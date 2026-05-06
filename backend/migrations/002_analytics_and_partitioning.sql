-- Analytics materialized views
CREATE MATERIALIZED VIEW IF NOT EXISTS detection_statistics AS
SELECT
  date_trunc('day', d.timestamp) AS day,
  COALESCE(d.class_name, 'unknown_aircraft') AS class_name,
  COUNT(*) AS detection_count,
  AVG(d.confidence) AS avg_confidence
FROM detections d
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_detection_statistics_day_class
  ON detection_statistics(day, class_name);

CREATE MATERIALIZED VIEW IF NOT EXISTS airport_activity_summary AS
SELECT
  a.id AS airport_id,
  a.name AS airport_name,
  a.icao_code,
  COUNT(d.id) AS detections_within_5km,
  MAX(d.timestamp) AS last_detection_at
FROM airports a
LEFT JOIN detections d
  ON d.centroid IS NOT NULL
 AND ST_DWithin(a.geom::geography, d.centroid::geography, 5000)
GROUP BY a.id, a.name, a.icao_code;

CREATE UNIQUE INDEX IF NOT EXISTS idx_airport_activity_summary_airport_id
  ON airport_activity_summary(airport_id);

-- Partitioned analytics table for high-volume detection history.
-- The canonical detections table remains the write-source for compatibility.
CREATE TABLE IF NOT EXISTS detections_partitioned (
  LIKE detections INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
) PARTITION BY RANGE (timestamp);

CREATE OR REPLACE FUNCTION ensure_detection_partition(ts timestamp)
RETURNS void AS $$
DECLARE
  part_start date := date_trunc('month', ts)::date;
  part_end date := (date_trunc('month', ts) + interval '1 month')::date;
  part_name text := format('detections_partitioned_%s', to_char(part_start, 'YYYYMM'));
BEGIN
  EXECUTE format(
    'CREATE TABLE IF NOT EXISTS %I PARTITION OF detections_partitioned FOR VALUES FROM (%L) TO (%L);',
    part_name, part_start, part_end
  );
END;
$$ LANGUAGE plpgsql;

SELECT ensure_detection_partition(NOW()::timestamp);
SELECT ensure_detection_partition((NOW() + interval '1 month')::timestamp);

CREATE OR REPLACE FUNCTION mirror_detection_into_partitioned()
RETURNS trigger AS $$
BEGIN
  PERFORM ensure_detection_partition(NEW.timestamp);
  INSERT INTO detections_partitioned VALUES (NEW.*);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mirror_detection_partitioned ON detections;
CREATE TRIGGER trg_mirror_detection_partitioned
AFTER INSERT ON detections
FOR EACH ROW
EXECUTE FUNCTION mirror_detection_into_partitioned();

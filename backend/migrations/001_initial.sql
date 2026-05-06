CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  api_token VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS satellite_images (
  id SERIAL PRIMARY KEY,
  filename VARCHAR(255),
  original_filename VARCHAR(255),
  file_path TEXT,
  image_type VARCHAR(32),
  source VARCHAR(64),
  provider VARCHAR(64) NOT NULL,
  acquisition_date TIMESTAMP NOT NULL,
  cloud_cover FLOAT DEFAULT 0,
  width INT,
  height INT,
  crs VARCHAR(128),
  resolution_m FLOAT DEFAULT 10,
  bounds GEOMETRY(POLYGON, 4326),
  bounds_json JSONB DEFAULT '{}'::jsonb,
  georeferenced BOOLEAN DEFAULT FALSE,
  asset_url TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aircraft_classes (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) UNIQUE NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS ai_models (
  id SERIAL PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  file_path TEXT,
  model_type VARCHAR(64) DEFAULT 'yolov8',
  classes JSONB DEFAULT '[]'::jsonb,
  checksum_sha256 VARCHAR(128) UNIQUE,
  uploader VARCHAR(100),
  input_size INT,
  stride INT,
  framework_version VARCHAR(64),
  version VARCHAR(64) NOT NULL,
  framework VARCHAR(64) DEFAULT 'pytorch',
  weights_path TEXT NOT NULL,
  metrics JSONB DEFAULT '{}'::jsonb,
  active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS detections (
  id SERIAL PRIMARY KEY,
  image_id INT REFERENCES satellite_images(id),
  model_id INT REFERENCES ai_models(id),
  class_id INT REFERENCES aircraft_classes(id),
  class_name VARCHAR(128),
  confidence FLOAT NOT NULL,
  pixel_bbox JSONB DEFAULT '{}'::jsonb,
  geo_polygon GEOMETRY(POLYGON, 4326),
  centroid GEOMETRY(POINT, 4326),
  georeferenced BOOLEAN DEFAULT TRUE,
  timestamp TIMESTAMP DEFAULT NOW(),
  source VARCHAR(64) DEFAULT 'yolov8',
  attributes JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS airports (
  id SERIAL PRIMARY KEY,
  ident VARCHAR(16) UNIQUE,
  icao_code VARCHAR(8) UNIQUE,
  iata_code VARCHAR(8),
  name VARCHAR(255) NOT NULL,
  municipality VARCHAR(128),
  country VARCHAR(64),
  type VARCHAR(64),
  geom GEOMETRY(POINT, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
  id SERIAL PRIMARY KEY,
  level VARCHAR(32) DEFAULT 'info',
  title VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  status VARCHAR(32) DEFAULT 'open',
  related_detection_id INT REFERENCES detections(id),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS geo_events (
  id SERIAL PRIMARY KEY,
  event_type VARCHAR(64) NOT NULL,
  geom GEOMETRY(GEOMETRY, 4326) NOT NULL,
  payload JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  username_snapshot VARCHAR(100),
  action VARCHAR(128) NOT NULL,
  endpoint VARCHAR(255) NOT NULL,
  status VARCHAR(32) NOT NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS detection_jobs (
  id SERIAL PRIMARY KEY,
  task_id VARCHAR(255) UNIQUE NOT NULL,
  image_id INT REFERENCES satellite_images(id),
  status VARCHAR(32) DEFAULT 'pending',
  progress FLOAT DEFAULT 0,
  message TEXT,
  result JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS change_detection_jobs (
  id SERIAL PRIMARY KEY,
  task_id VARCHAR(255) UNIQUE NOT NULL,
  before_image_id INT REFERENCES satellite_images(id),
  after_image_id INT REFERENCES satellite_images(id),
  status VARCHAR(32) DEFAULT 'pending',
  progress FLOAT DEFAULT 0,
  message TEXT,
  result JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  token VARCHAR(512) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  revoked BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_satellite_images_footprint_gist ON satellite_images USING GIST (bounds);
CREATE INDEX IF NOT EXISTS idx_detections_geo_polygon_gist ON detections USING GIST (geo_polygon);
CREATE INDEX IF NOT EXISTS idx_detections_centroid_gist ON detections USING GIST (centroid);
CREATE INDEX IF NOT EXISTS idx_airports_geom_gist ON airports USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_detections_image_id ON detections(image_id);
CREATE INDEX IF NOT EXISTS idx_ai_models_active ON ai_models(active);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);

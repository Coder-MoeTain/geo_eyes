CREATE EXTENSION IF NOT EXISTS postgis;
\i /docker-entrypoint-initdb.d/001_initial.sql

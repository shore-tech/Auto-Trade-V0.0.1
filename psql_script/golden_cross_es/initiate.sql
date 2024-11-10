-- create user
CREATE USER newuser WITH PASSWORD '1234';


-- create database
CREATE DATABASE demo_db OWNER newuser;

-- create schema
\c demo_db;
CREATE SCHEMA golden_cross_es;


-- grant permission
GRANT CREATE ON SCHEMA public TO newuser;
GRANT ALL PRIVILEGES ON DATABASE demo_db TO newuser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA golden_cross_es TO newuser;
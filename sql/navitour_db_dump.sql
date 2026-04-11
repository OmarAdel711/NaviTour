-- ==============================================================
-- NaviTour: Complete Database Dump
-- Generated : 2026-03-07
-- Run: psql -U postgres -f navitour_db_dump.sql
-- ==============================================================

-- Create database (run as postgres superuser)
-- If DB already exists, skip this line:
-- CREATE DATABASE egypt_transport;

\c egypt_transport

CREATE EXTENSION IF NOT EXISTS postgis;

-- ==============================================================
-- SCHEMA
-- ==============================================================

DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS restaurants;
DROP TABLE IF EXISTS stations;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name    TEXT
);

CREATE TABLE places (
    place_id  SERIAL PRIMARY KEY,
    name      TEXT,
    category  TEXT,
    geom      geography(Point, 4326)
);

CREATE TABLE restaurants (
    restaurant_id SERIAL PRIMARY KEY,
    name          TEXT,
    cuisine       TEXT,
    geom          geography(Point, 4326)
);

CREATE TABLE stations (
    station_id SERIAL PRIMARY KEY,
    name       TEXT,
    city       TEXT,
    type       TEXT,
    geometry   geography(Point, 4326)
);

CREATE TABLE ratings (
    rating_id  SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(user_id),
    place_type TEXT,
    place_id   INTEGER,
    rating     INTEGER CHECK (rating BETWEEN 1 AND 5),
    review     TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Spatial indexes for fast distance queries
CREATE INDEX idx_places_geom      ON places      USING GIST(geom);
CREATE INDEX idx_restaurants_geom ON restaurants  USING GIST(geom);
CREATE INDEX idx_stations_geom    ON stations     USING GIST(geometry);
CREATE INDEX idx_ratings_user     ON ratings(user_id);
CREATE INDEX idx_ratings_place    ON ratings(place_type, place_id);

-- ==============================================================
-- USERS (54 rows)
-- ==============================================================
INSERT INTO users (user_id, name) VALUES
(1, 'Omar'),
(2, 'Sara'),
(3, 'Ahmed'),
(4, 'Mona'),
(5, 'Mohamed'),
(6, 'Youssef'),
(7, 'Fatma'),
(8, 'Khaled'),
(9, 'Nadia'),
(10, 'Hassan'),
(11, 'Laila'),
(12, 'Tarek'),
(13, 'Reem'),
(14, 'Ibrahim'),
(15, 'Mariam'),
(16, 'Mostafa'),
(17, 'Dina'),
(18, 'Amr'),
(19, 'Heba'),
(20, 'Sami'),
(21, 'Aya'),
(22, 'Karim'),
(23, 'Salma'),
(24, 'Adel'),
(25, 'Nour'),
(26, 'Waleed'),
(27, 'Eman'),
(28, 'Ali'),
(29, 'Mai'),
(30, 'Ayman'),
(31, 'Hager'),
(32, 'Hazem'),
(33, 'Rania'),
(34, 'Mahmoud'),
(35, 'Basma'),
(36, 'Elsayed'),
(37, 'Abeer'),
(38, 'Zain'),
(39, 'Hadeer'),
(40, 'Hamdy'),
(41, 'Magdy'),
(42, 'Yaser'),
(43, 'Nansy'),
(44, 'Khloud'),
(45, 'Nawel'),
(46, 'Aisha'),
(47, 'Retal'),
(48, 'Samia'),
(49, 'Zainab'),
(50, 'Manar'),
(51, 'Sherif'),
(52, 'Doaa'),
(53, 'Samir'),
(54, 'Maha')
(55, 'Nada'),
(56, 'Kareem'),
(57, 'Hana'),
(58, 'Osama'),
(59, 'Lina'),
(60, 'Tamer');
SELECT setval('users_user_id_seq', 60);

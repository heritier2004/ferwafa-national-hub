-- NATIONAL FOOTBALL INTELLIGENCE SYSTEM (RWANDA - FERWAFA LEVEL)
-- PostgreSQL Database Schema

-- ROLES: SUPER_ADMIN, FERWAFA, CLUB, SCHOOL, ACADEMY, SCOUT

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS institutions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- club, school, academy
    code VARCHAR(50) UNIQUE NOT NULL, -- e.g., APR, RAYON, AMV
    location VARCHAR(255),
    logo_url TEXT
);

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    institution_id INTEGER REFERENCES institutions(id),
    player_code VARCHAR(50) UNIQUE NOT NULL, -- e.g., APR-001
    name VARCHAR(255) NOT NULL,
    position VARCHAR(50),
    height DECIMAL(5,2),
    weight DECIMAL(5,2),
    nationality VARCHAR(100) DEFAULT 'Rwandan',
    date_of_birth DATE,
    photo_url TEXT
);

CREATE TABLE IF NOT EXISTS matches (
    id SERIAL PRIMARY KEY,
    home_team_id INTEGER REFERENCES institutions(id),
    away_team_id INTEGER REFERENCES institutions(id),
    stadium VARCHAR(255),
    match_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'SCHEDULED', -- SCHEDULED, LIVE, COMPLETED
    round VARCHAR(50), -- First Round, Second Round
    score_home INTEGER DEFAULT 0,
    score_away INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS match_events (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    player_id INTEGER REFERENCES players(id),
    event_type VARCHAR(50) NOT NULL, -- goal, card_yellow, card_red, injury, pass, movement
    timestamp_match INTEGER, -- match minute
    x_pos DECIMAL(10,2), -- for tracking
    y_pos DECIMAL(10,2), -- for tracking
    value DECIMAL(10,2) -- intensity or value of event
);

CREATE TABLE IF NOT EXISTS player_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    speed DECIMAL(5,2) DEFAULT 0.0,
    distance DECIMAL(10,2) DEFAULT 0.0,
    rating DECIMAL(3,1) DEFAULT 0.0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_analysis (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    star_rating DECIMAL(2,1) CHECK (star_rating >= 3.5 AND star_rating <= 9.5),
    analysis_notes TEXT,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fixtures (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    status VARCHAR(50) DEFAULT 'PENDING', -- PENDING, APPROVED, OVERRIDDEN
    suggested_by_ai BOOLEAN DEFAULT TRUE,
    approved_by_ferwafa BOOLEAN DEFAULT FALSE,
    approved_by_id INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS live_sessions (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    live_link VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'INACTIVE', -- INACTIVE, ACTIVE, CLOSED
    websocket_endpoint VARCHAR(255)
);

-- INDEXES for performance
CREATE INDEX idx_players_institution ON players(institution_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_events_match ON match_events(match_id);
CREATE INDEX idx_stats_player ON player_stats(player_id);

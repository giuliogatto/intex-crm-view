-- User authentication tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- Admin user: giuliogatto@gmail.com / dsahj657!45
INSERT INTO users (username, password_hash, role) VALUES
(
    'giuliogatto@gmail.com',
    '460d565d18d6696f08c8d3ed494a8b7f$45f0ea76ea24fed97f8c0694c956dcbd5785aa7333ae74ac4b4aefc1e096fafd',
    'admin'
)
ON CONFLICT (username) DO NOTHING;

-- password (clear text version): dsahj657!45

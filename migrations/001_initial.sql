CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    language_code TEXT,
    referrer TEXT
);

CREATE TABLE usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT NOT NULL,
    source_id TEXT,
    duration_seconds INTEGER,
    success INTEGER NOT NULL,
    error TEXT,
    api_cost_cents INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_usage_user_time ON usage_log(user_id, created_at);

CREATE TABLE subscriptions (
    user_id INTEGER PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    payment_charge_id TEXT NOT NULL,
    stars_paid INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    payment_charge_id TEXT UNIQUE NOT NULL,
    invoice_payload TEXT NOT NULL,
    stars_amount INTEGER NOT NULL,
    refunded INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE summary_cache (
    cache_key TEXT PRIMARY KEY,
    summary_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hits INTEGER DEFAULT 1
);

-- SmartRecomenda: esquema inicial idempotente.
-- A aplicação também executa este contrato na inicialização para o modo demonstrativo.
CREATE TABLE IF NOT EXISTS contents (id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, type TEXT NOT NULL, genres TEXT NOT NULL, language TEXT NOT NULL, year INTEGER, cover TEXT NOT NULL, popularity REAL NOT NULL DEFAULT 0, is_demo INTEGER NOT NULL DEFAULT 1, featured INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT, history_enabled INTEGER NOT NULL DEFAULT 0, role TEXT NOT NULL DEFAULT 'user');
CREATE TABLE IF NOT EXISTS preferences (user_id TEXT PRIMARY KEY, types TEXT NOT NULL, genres TEXT NOT NULL, languages TEXT NOT NULL, blocked_ids TEXT NOT NULL, diversity TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ratings (user_id TEXT NOT NULL, content_id INTEGER NOT NULL, rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), updated_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, content_id));
CREATE TABLE IF NOT EXISTS favorites (user_id TEXT NOT NULL, content_id INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user_id, content_id));
CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, content_id INTEGER NOT NULL, kind TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS recommendation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, strategy TEXT NOT NULL, item_count INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);

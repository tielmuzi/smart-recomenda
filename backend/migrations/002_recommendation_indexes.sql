-- Indexes used by personalized scoring and administrative activity reports.
CREATE INDEX IF NOT EXISTS idx_ratings_user ON ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_user ON recommendation_events(user_id);

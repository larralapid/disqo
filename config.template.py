# Spotify user ID (used when creating private Ready playlists)
user_id = ''

# Username retained for compatibility/documentation; SpotifyOAuth uses account auth.
username = ''

# Discovery backlog / listening-list playlist ID.
beta_id = ''

# Consumable familiar-song pool. Tracks are MOVED out of this playlist into
# generated Ready playlists. When it reaches zero, refill it from Liked Songs.
liked_bucket_id = ''

# Legacy target queue playlist ID. No longer used by the Ready-batch workflow,
# but kept here so older scripts/configs do not break immediately.
pq_id = ''

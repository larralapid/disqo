# disqo — Spotify discovery queue builder

I use Spotify playlists as a consumable discovery system rather than permanent collections.

The two source pools are:

- **In Beta** — unfamiliar / not-yet-evaluated tracks.
- **Liked Bucket** — familiar tracks copied from Spotify Liked Songs. This is also consumable.

When a Ready playlist is created, tracks are randomly sampled **without replacement** from both pools, arranged according to a novelty/familiarity pattern, written to a new private playlist, and then removed from both source playlists. This gives the workflow true move semantics.

When Liked Bucket reaches zero, refill it by copying all current Spotify Liked Songs into that playlist.

## Default experiments

`main.py` currently creates five Ready playlists:

| Batch | Size | Pattern | Approx. beta share | Intent |
| --- | ---: | --- | ---: | --- |
| 1 | 50 | `BL` | 50% | strict unfamiliar/familiar alternation |
| 2 | 48 | `BBL` | 67% | two discoveries per familiar track |
| 3 | 30 | `BLL` | 33% | familiarity-heavy session |
| 4 | 45 | `BBBLL` | 60% | novelty bursts followed by recovery |
| 5 | 40 | `RANDOM50` | 50% | balanced but less predictable; avoids 3-song same-type streaks when possible |

`B` means In Beta and `L` means Liked Bucket.

Each generated playlist is named from its actual contents using the format:

```text
🤖{track_count}t{rough_duration_hours}h
```

Examples: `🤖50t3h`, `🤖30t2h`.

## Spotify components

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
- [Spotipy](https://spotipy.readthedocs.io/)
- Spotify developer application / OAuth credentials

Required OAuth scopes include private playlist read/write and library read access.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `config.template.py` to `config.py` and set:

```python
user_id = "..."
beta_id = "..."          # In Beta playlist
liked_bucket_id = "..."  # consumable familiar-song bucket
```

3. Export Spotify OAuth credentials:

```bash
export SPOTIPY_CLIENT_ID="your-client-id"
export SPOTIPY_CLIENT_SECRET="your-client-secret"
export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
```

The older `clientID`, `clientSecret`, and `redirectURI` environment-variable names are also accepted for compatibility.

4. Run:

```bash
python main.py
```

## Safety / behavior

The destination playlist is created and populated **before** source tracks are removed. If creation or adding tracks fails, the source pools are left untouched. Once the destination succeeds, the selected tracks are consumed from both In Beta and Liked Bucket.

Spotify's Web API does not expose playlist folders, so generated playlists will appear at the playlist-library level; move them into the Spotify `ready` folder manually if desired.

To manually restore Liked Bucket from Liked Songs in Python:

```python
from src.Spot import Spot

Spot().refill_liked_bucket(only_if_empty=True)
```

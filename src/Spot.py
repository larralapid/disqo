import os
import random
from dataclasses import dataclass
from typing import Iterable, List, Sequence

import spotipy
from spotipy.oauth2 import SpotifyOAuth

import config


@dataclass(frozen=True)
class BatchSpec:
    size: int
    pattern: str
    label: str = ""


class Spot:
    SCOPES = [
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-library-read",
    ]

    def __init__(self):
        self.in_beta_id = config.beta_id
        self.liked_bucket_id = config.liked_bucket_id
        self.user_id = config.user_id

        scope = " ".join(self.SCOPES)
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=os.getenv("SPOTIPY_CLIENT_ID") or os.getenv("clientID"),
                client_secret=os.getenv("SPOTIPY_CLIENT_SECRET") or os.getenv("clientSecret"),
                redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI") or os.getenv("redirectURI"),
                scope=scope,
                cache_path=os.getenv("SPOTIPY_CACHE_PATH", ".cache-disqo"),
                open_browser=True,
            )
        )

    # ---------- Spotify reads ----------

    def get_playlist_tracks(self, playlist_id: str) -> List[dict]:
        """Return all valid track objects from a playlist, preserving playlist order."""
        tracks = []
        offset = 0

        while True:
            page = self.sp.playlist_items(
                playlist_id,
                offset=offset,
                limit=100,
                additional_types=("track",),
            )
            for item in page.get("items", []):
                track = item.get("track") if item else None
                if track and track.get("id") and track.get("uri"):
                    tracks.append(track)

            if not page.get("next"):
                break
            offset += len(page.get("items", []))

        return tracks

    def get_saved_tracks(self) -> List[dict]:
        """Return all songs in Spotify Liked Songs."""
        tracks = []
        offset = 0

        while True:
            page = self.sp.current_user_saved_tracks(limit=50, offset=offset)
            for item in page.get("items", []):
                track = item.get("track") if item else None
                if track and track.get("id") and track.get("uri"):
                    tracks.append(track)

            if not page.get("next"):
                break
            offset += len(page.get("items", []))

        return tracks

    # ---------- Source-pool management ----------

    def refill_liked_bucket(self, only_if_empty: bool = True) -> int:
        """Copy all Liked Songs into Liked Bucket.

        This intentionally copies from Spotify's saved-track library only when the
        consumable bucket has reached zero, matching the manual reset step.
        """
        current = self.get_playlist_tracks(self.liked_bucket_id)
        if only_if_empty and current:
            return 0

        liked = self.get_saved_tracks()
        uris = [track["uri"] for track in liked]
        self._add_items(self.liked_bucket_id, uris)
        return len(uris)

    @staticmethod
    def _unique_by_id(tracks: Iterable[dict]) -> List[dict]:
        seen = set()
        result = []
        for track in tracks:
            track_id = track["id"]
            if track_id not in seen:
                seen.add(track_id)
                result.append(track)
        return result

    # ---------- Pattern generation ----------

    @staticmethod
    def _expand_pattern(pattern: str, size: int) -> List[str]:
        """Expand a B/L pattern to exactly size slots.

        B = In Beta, L = Liked Bucket.

        Special pattern: RANDOM50 creates a balanced random sequence with no run
        longer than two when possible.
        """
        normalized = pattern.upper().replace(" ", "")
        if normalized == "RANDOM50":
            beta_count = (size + 1) // 2
            liked_count = size - beta_count
            slots = ["B"] * beta_count + ["L"] * liked_count

            for _ in range(1000):
                random.shuffle(slots)
                if all(
                    not (slots[i] == slots[i + 1] == slots[i + 2])
                    for i in range(max(0, len(slots) - 2))
                ):
                    return slots
            return slots

        if not normalized or any(ch not in {"B", "L"} for ch in normalized):
            raise ValueError(f"Invalid pattern: {pattern!r}. Use B/L characters or RANDOM50.")

        return [normalized[i % len(normalized)] for i in range(size)]

    @staticmethod
    def _interleave_selected(slots: Sequence[str], beta: List[dict], liked: List[dict]) -> List[dict]:
        beta_iter = iter(beta)
        liked_iter = iter(liked)
        return [next(beta_iter) if slot == "B" else next(liked_iter) for slot in slots]

    # ---------- Playlist writes ----------

    def _add_items(self, playlist_id: str, uris: Sequence[str]) -> None:
        for i in range(0, len(uris), 100):
            self.sp.playlist_add_items(playlist_id, list(uris[i : i + 100]))

    def _remove_track_ids(self, playlist_id: str, track_ids: Sequence[str]) -> None:
        """Remove consumed tracks from a source playlist in API-sized chunks."""
        for i in range(0, len(track_ids), 100):
            self.sp.playlist_remove_all_occurrences_of_items(
                playlist_id,
                list(track_ids[i : i + 100]),
            )

    @staticmethod
    def _duration_title(tracks: Sequence[dict], prefix: str = "🤖") -> str:
        total_ms = sum(track.get("duration_ms", 0) or 0 for track in tracks)
        hours = total_ms / 3_600_000
        rough_hours = max(1, int(hours + 0.5))
        return f"{prefix}{len(tracks)}t{rough_hours}h"

    def create_ready_batch(self, spec: BatchSpec, title_prefix: str = "🤖") -> dict:
        beta_pool = self._unique_by_id(self.get_playlist_tracks(self.in_beta_id))
        liked_pool = self._unique_by_id(self.get_playlist_tracks(self.liked_bucket_id))

        slots = self._expand_pattern(spec.pattern, spec.size)
        beta_needed = slots.count("B")
        liked_needed = slots.count("L")

        if len(beta_pool) < beta_needed:
            raise RuntimeError(
                f"In Beta has {len(beta_pool)} unique tracks but this batch needs {beta_needed}."
            )
        if len(liked_pool) < liked_needed:
            raise RuntimeError(
                f"Liked Bucket has {len(liked_pool)} unique tracks but this batch needs {liked_needed}. "
                "Refill it from Liked Songs, then rerun."
            )

        # Sample without replacement from both consumable pools.
        selected_beta = random.sample(beta_pool, beta_needed)
        selected_liked = random.sample(liked_pool, liked_needed)
        ordered = self._interleave_selected(slots, selected_beta, selected_liked)

        title = self._duration_title(ordered, prefix=title_prefix)
        description = (
            f"disqo ready batch | pattern={spec.pattern} | "
            f"beta={beta_needed} | liked={liked_needed}"
        )
        if spec.label:
            description += f" | {spec.label}"

        created = self.sp.user_playlist_create(
            user=self.user_id,
            name=title,
            public=False,
            description=description,
        )
        playlist_id = created["id"]

        # Destination is populated before either source is mutated. If creation/add
        # fails, no tracks have been consumed from the source buckets.
        self._add_items(playlist_id, [track["uri"] for track in ordered])

        # Move semantics: after successful destination creation, consume from BOTH.
        self._remove_track_ids(self.in_beta_id, [track["id"] for track in selected_beta])
        self._remove_track_ids(self.liked_bucket_id, [track["id"] for track in selected_liked])

        return {
            "id": playlist_id,
            "url": created.get("external_urls", {}).get("spotify"),
            "name": title,
            "size": len(ordered),
            "pattern": spec.pattern,
            "beta": beta_needed,
            "liked": liked_needed,
            "duration_ms": sum(track.get("duration_ms", 0) or 0 for track in ordered),
        }

    def create_ready_playlists(
        self,
        specs: Sequence[BatchSpec],
        title_prefix: str = "🤖",
    ) -> List[dict]:
        """Create multiple disposable Ready playlists sequentially.

        Each batch rereads In Beta and Liked Bucket after the prior batch consumes
        its tracks, which prevents any track from being selected twice in the run.
        """
        results = []
        for index, spec in enumerate(specs, start=1):
            print(f"Creating batch {index}/{len(specs)}: size={spec.size}, pattern={spec.pattern}")
            result = self.create_ready_batch(spec, title_prefix=title_prefix)
            results.append(result)
            print(
                f"  {result['name']}: {result['beta']} beta + "
                f"{result['liked']} liked -> {result['url']}"
            )
        return results

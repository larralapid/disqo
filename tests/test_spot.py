import random
import sys
import types
import unittest
from copy import deepcopy

# src/Spot.py imports a local config module. Supply a test-only stand-in so the
# production config.py never needs to exist in CI.
config = types.ModuleType("config")
config.beta_id = "beta"
config.liked_bucket_id = "liked"
config.user_id = "user"
sys.modules["config"] = config

from src.Spot import BatchSpec, Spot


def track(i, duration_ms=180_000, source="x"):
    return {
        "id": f"{source}{i}",
        "uri": f"spotify:track:{source}{i}",
        "duration_ms": duration_ms,
    }


class FakeSpotify:
    def __init__(self, beta_count=200, liked_count=200, saved_count=20, fail_add=False):
        self.playlists = {
            "beta": [track(i, source="b") for i in range(beta_count)],
            "liked": [track(i, source="l") for i in range(liked_count)],
        }
        self.saved = [track(i, source="s") for i in range(saved_count)]
        self.created = []
        self.removals = []
        self.fail_add = fail_add
        self._created_counter = 0

    def user_playlist_create(self, user, name, public=False, description=""):
        self._created_counter += 1
        pid = f"ready-{self._created_counter}"
        self.playlists[pid] = []
        obj = {
            "id": pid,
            "name": name,
            "description": description,
            "external_urls": {"spotify": f"https://open.spotify.com/playlist/{pid}"},
        }
        self.created.append(obj)
        return obj

    def playlist_add_items(self, playlist_id, uris):
        if self.fail_add:
            raise RuntimeError("simulated destination add failure")
        by_uri = {
            t["uri"]: t
            for items in self.playlists.values()
            for t in items
        }
        by_uri.update({t["uri"]: t for t in self.saved})
        self.playlists[playlist_id].extend(deepcopy(by_uri[u]) for u in uris)

    def playlist_remove_all_occurrences_of_items(self, playlist_id, ids):
        ids = set(ids)
        self.removals.append((playlist_id, set(ids)))
        self.playlists[playlist_id] = [t for t in self.playlists[playlist_id] if t["id"] not in ids]
        return {"snapshot_id": "snapshot"}


class HarnessSpot(Spot):
    def __init__(self, fake):
        self.in_beta_id = "beta"
        self.liked_bucket_id = "liked"
        self.user_id = "user"
        self.sp = fake

    def get_playlist_tracks(self, playlist_id):
        return deepcopy(self.sp.playlists[playlist_id])

    def get_saved_tracks(self):
        return deepcopy(self.sp.saved)


class PatternTests(unittest.TestCase):
    def test_fixed_patterns_expand_exactly(self):
        self.assertEqual(Spot._expand_pattern("BL", 7), list("BLBLBLB"))
        self.assertEqual(Spot._expand_pattern("BBL", 8), list("BBLBBLBB"))
        self.assertEqual(Spot._expand_pattern("BLL", 8), list("BLLBLLBL"))
        self.assertEqual(Spot._expand_pattern("BBBLL", 10), list("BBBLLBBBLL"))

    def test_random50_is_balanced_and_avoids_three_song_streaks(self):
        random.seed(7)
        slots = Spot._expand_pattern("RANDOM50", 41)
        self.assertEqual(len(slots), 41)
        self.assertEqual(slots.count("B"), 21)
        self.assertEqual(slots.count("L"), 20)
        self.assertTrue(all(not (slots[i] == slots[i+1] == slots[i+2]) for i in range(len(slots)-2)))

    def test_invalid_pattern_is_rejected(self):
        with self.assertRaises(ValueError):
            Spot._expand_pattern("BX", 10)


class BatchTests(unittest.TestCase):
    def test_single_batch_moves_from_both_sources_and_preserves_pattern(self):
        random.seed(1)
        fake = FakeSpotify(beta_count=50, liked_count=50)
        spot = HarnessSpot(fake)
        before_beta = {t["id"] for t in fake.playlists["beta"]}
        before_liked = {t["id"] for t in fake.playlists["liked"]}

        result = spot.create_ready_batch(BatchSpec(size=12, pattern="BL"))
        ready = fake.playlists[result["id"]]

        self.assertEqual(result["size"], 12)
        self.assertEqual(result["beta"], 6)
        self.assertEqual(result["liked"], 6)
        self.assertEqual([t["id"][0] for t in ready], list("blblblblblbl"))

        after_beta = {t["id"] for t in fake.playlists["beta"]}
        after_liked = {t["id"] for t in fake.playlists["liked"]}
        moved_beta = before_beta - after_beta
        moved_liked = before_liked - after_liked
        self.assertEqual(moved_beta, {t["id"] for t in ready if t["id"].startswith("b")})
        self.assertEqual(moved_liked, {t["id"] for t in ready if t["id"].startswith("l")})

    def test_five_batches_do_not_reuse_tracks(self):
        random.seed(42)
        fake = FakeSpotify(beta_count=250, liked_count=250)
        spot = HarnessSpot(fake)
        specs = [
            BatchSpec(50, "BL"),
            BatchSpec(48, "BBL"),
            BatchSpec(30, "BLL"),
            BatchSpec(45, "BBBLL"),
            BatchSpec(40, "RANDOM50"),
        ]

        results = spot.create_ready_playlists(specs)
        all_ids = []
        for result in results:
            ids = [t["id"] for t in fake.playlists[result["id"]]]
            self.assertEqual(len(ids), result["size"])
            all_ids.extend(ids)

        self.assertEqual(len(all_ids), sum(s.size for s in specs))
        self.assertEqual(len(all_ids), len(set(all_ids)), "a source track was reused across Ready playlists")

    def test_source_playlists_are_not_mutated_if_destination_add_fails(self):
        random.seed(3)
        fake = FakeSpotify(beta_count=20, liked_count=20, fail_add=True)
        spot = HarnessSpot(fake)
        beta_before = deepcopy(fake.playlists["beta"])
        liked_before = deepcopy(fake.playlists["liked"])

        with self.assertRaises(RuntimeError):
            spot.create_ready_batch(BatchSpec(10, "BL"))

        self.assertEqual(fake.playlists["beta"], beta_before)
        self.assertEqual(fake.playlists["liked"], liked_before)
        self.assertEqual(fake.removals, [])

    def test_insufficient_source_pool_fails_before_writes(self):
        fake = FakeSpotify(beta_count=2, liked_count=50)
        spot = HarnessSpot(fake)
        with self.assertRaisesRegex(RuntimeError, "In Beta"):
            spot.create_ready_batch(BatchSpec(10, "BL"))
        self.assertEqual(fake.created, [])

    def test_duration_title_uses_actual_duration(self):
        tracks = [track(i, duration_ms=240_000) for i in range(30)]  # exactly 2h
        self.assertEqual(Spot._duration_title(tracks), "🤖30t2h")

    def test_refill_liked_bucket_only_when_empty(self):
        fake = FakeSpotify(beta_count=10, liked_count=0, saved_count=13)
        spot = HarnessSpot(fake)
        self.assertEqual(spot.refill_liked_bucket(), 13)
        self.assertEqual(len(fake.playlists["liked"]), 13)
        self.assertEqual(spot.refill_liked_bucket(), 0)
        self.assertEqual(len(fake.playlists["liked"]), 13)


if __name__ == "__main__":
    unittest.main()

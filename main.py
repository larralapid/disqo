from src.Spot import BatchSpec, Spot


# Five experiments over both novelty ratio and ordering rhythm.
# B = In Beta (new/unfamiliar), L = Liked Bucket (familiar).
READY_BATCHES = [
    BatchSpec(size=50, pattern="BL", label="50% beta, strict palate-cleanser alternation"),
    BatchSpec(size=48, pattern="BBL", label="67% beta, two discoveries per familiar track"),
    BatchSpec(size=30, pattern="BLL", label="33% beta, familiarity-heavy"),
    BatchSpec(size=45, pattern="BBBLL", label="60% beta, novelty bursts with recovery"),
    BatchSpec(size=40, pattern="RANDOM50", label="50% beta, randomized with max-two streak guardrail"),
]


def main():
    spot = Spot()
    results = spot.create_ready_playlists(READY_BATCHES, title_prefix="🤖")

    print("\nCreated Ready playlists:")
    for result in results:
        print(
            f"- {result['name']} | {result['beta']} beta / {result['liked']} liked | "
            f"{result['url']}"
        )


if __name__ == "__main__":
    main()

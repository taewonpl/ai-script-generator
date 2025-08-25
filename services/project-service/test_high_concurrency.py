"""
High concurrency stress test for atomic episode creation
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import sessionmaker

from src.project_service.database.engine import engine
from src.project_service.services.episode_service import EpisodeService


def create_episode_worker(project_id: str, worker_id: int, num_episodes: int):
    """Worker function to create episodes concurrently"""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        service = EpisodeService(db)
        created_episodes = []

        for i in range(num_episodes):
            try:
                episode = service.create_episode(
                    project_id=project_id,
                    title=f"Stress Test Episode W{worker_id}-{i+1}",
                    description=f"Stress test from worker {worker_id}",
                )
                created_episodes.append(episode["number"])

            except Exception as e:
                print(f"Worker {worker_id}: Failed episode {i+1}: {e}")

        return worker_id, created_episodes

    finally:
        db.close()


def test_high_concurrency():
    """Stress test with high concurrency"""
    # High concurrency parameters
    num_workers = 20
    episodes_per_worker = 5
    total_expected = num_workers * episodes_per_worker

    print("🚀 HIGH CONCURRENCY STRESS TEST")
    print(f"Workers: {num_workers}, Episodes per worker: {episodes_per_worker}")
    print(f"Total expected episodes: {total_expected}")

    # Use existing test project
    project_id = "test_concurrent_proj"

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                create_episode_worker, project_id, worker_id, episodes_per_worker
            )
            for worker_id in range(1, num_workers + 1)
        ]

        results = []
        total_created = 0

        for future in as_completed(futures):
            try:
                worker_id, episodes = future.result()
                results.append((worker_id, episodes))
                total_created += len(episodes)
                if len(episodes) == episodes_per_worker:
                    print(f"✅ Worker {worker_id}: {len(episodes)} episodes")
                else:
                    print(
                        f"⚠️ Worker {worker_id}: {len(episodes)}/{episodes_per_worker} episodes"
                    )
            except Exception as e:
                print(f"❌ Worker failed: {e}")

    end_time = time.time()

    print(f"\\n⏱️ Stress test completed in {end_time - start_time:.2f} seconds")
    print(f"Episodes created: {total_created}/{total_expected}")

    # Verify results
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        from src.project_service.repositories.episode import EpisodeRepository

        repo = EpisodeRepository(db)

        all_episodes = repo.get_by_project(project_id)
        episode_numbers = [ep.number for ep in all_episodes]
        episode_numbers.sort()

        # Check for duplicates
        unique_numbers = set(episode_numbers)
        if len(unique_numbers) == len(episode_numbers):
            print("✅ NO DUPLICATE EPISODE NUMBERS")
        else:
            print(
                f"❌ DUPLICATES FOUND: {len(episode_numbers) - len(unique_numbers)} duplicates"
            )

        # Check for gaps
        if len(episode_numbers) > 0:
            expected_range = list(range(1, len(episode_numbers) + 1))
            if episode_numbers == expected_range:
                print("✅ NO GAPS IN NUMBERING")
            else:
                print("❌ GAPS FOUND IN NUMBERING")

        print("\\n📊 Final Results:")
        print(f"Total episodes in DB: {len(all_episodes)}")
        print(
            f"Number range: {min(episode_numbers) if episode_numbers else 'N/A'} - {max(episode_numbers) if episode_numbers else 'N/A'}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    test_high_concurrency()

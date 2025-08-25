"""
Test atomic episode creation with concurrency scenarios
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import sessionmaker

from src.project_service.database.engine import engine
from src.project_service.models.project import ProjectStatus, ProjectType
from src.project_service.repositories.project import ProjectRepository
from src.project_service.services.episode_service import EpisodeService


def setup_test_project():
    """Create a test project for episode creation"""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Create test project
        project_id = "test_concurrent_proj"
        project_data = {
            "id": project_id,
            "name": "Concurrent Test Project",
            "type": ProjectType.DRAMA,
            "status": ProjectStatus.PLANNING,
            "description": "Test project for concurrency testing",
            "progress_percentage": 0,
            "next_episode_number": 1,
        }

        project_repo = ProjectRepository(db)
        # Delete if exists
        existing = project_repo.get(project_id)
        if existing:
            project_repo.delete(project_id)
            db.commit()

        project = project_repo.create(project_data)
        db.commit()
        print(f"✅ Created test project: {project.name}")
        return project_id

    finally:
        db.close()


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
                    title=f"Episode from Worker {worker_id}-{i+1}",
                    description=f"Created by worker {worker_id}",
                )
                created_episodes.append(episode)
                print(f"Worker {worker_id}: Created episode #{episode['number']}")

            except Exception as e:
                print(f"Worker {worker_id}: Failed to create episode {i+1}: {e}")

        return worker_id, created_episodes

    finally:
        db.close()


def test_concurrent_episode_creation():
    """Test concurrent episode creation for race conditions"""
    print("🔄 Setting up test project...")
    project_id = setup_test_project()

    # Test parameters
    num_workers = 5
    episodes_per_worker = 3
    total_expected = num_workers * episodes_per_worker

    print(
        f"🚀 Starting concurrent test: {num_workers} workers, {episodes_per_worker} episodes each"
    )
    print(f"Expected total episodes: {total_expected}")

    # Run concurrent episode creation
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                create_episode_worker, project_id, worker_id, episodes_per_worker
            )
            for worker_id in range(1, num_workers + 1)
        ]

        results = []
        for future in as_completed(futures):
            try:
                worker_id, episodes = future.result()
                results.append((worker_id, episodes))
                print(f"✅ Worker {worker_id} completed")
            except Exception as e:
                print(f"❌ Worker failed: {e}")

    end_time = time.time()
    print(f"⏱️ Test completed in {end_time - start_time:.2f} seconds")

    # Analyze results
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        from src.project_service.repositories.episode import EpisodeRepository

        repo = EpisodeRepository(db)

        # Get all episodes for the project
        episodes = repo.get_by_project(project_id)
        episode_numbers = [ep.number for ep in episodes]
        episode_numbers.sort()

        print("\\n📊 Results Analysis:")
        print(f"Episodes created: {len(episodes)}")
        print(f"Episode numbers: {episode_numbers}")

        # Check for duplicates
        unique_numbers = set(episode_numbers)
        if len(unique_numbers) == len(episode_numbers):
            print("✅ No duplicate episode numbers detected")
        else:
            print("❌ Duplicate episode numbers found!")
            duplicates = [
                num for num in episode_numbers if episode_numbers.count(num) > 1
            ]
            print(f"Duplicates: {set(duplicates)}")

        # Check for gaps
        expected_numbers = list(range(1, len(episodes) + 1))
        if episode_numbers == expected_numbers:
            print("✅ No gaps in episode numbering")
        else:
            print("❌ Gaps found in episode numbering")
            print(f"Expected: {expected_numbers}")
            print(f"Actual: {episode_numbers}")

        # Check project counter
        project_repo = ProjectRepository(db)
        project = project_repo.get(project_id)
        print(f"\\n🎯 Project next_episode_number: {project.next_episode_number}")
        print(f"Expected next number: {len(episodes) + 1}")

        if project.next_episode_number == len(episodes) + 1:
            print("✅ Project counter is correct")
        else:
            print("❌ Project counter is incorrect")

    finally:
        db.close()


if __name__ == "__main__":
    test_concurrent_episode_creation()

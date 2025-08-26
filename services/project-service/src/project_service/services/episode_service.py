"""
Episode Business Logic Service
"""

import uuid
from typing import Any

# Use fallback DTOs - Core integration disabled for type stability
from pydantic import BaseModel
from sqlalchemy.orm import Session


class EpisodeDTO(BaseModel):
    id: str
    title: str
    project_id: str
    order: int
    status: str | None = None
    description: str | None = None


class EpisodeCreateDTO(BaseModel):
    title: str
    description: str | None = None


class EpisodeUpdateDTO(BaseModel):
    title: str | None = None
    description: str | None = None


class BaseServiceException(Exception): ...


from ..database.transaction import ConcurrencyError, atomic_transaction
from ..monitoring.episode_alerting import get_alert_manager
from ..monitoring.episode_metrics import (
    get_integrity_checker,
    get_performance_tracker,
)
from ..repositories.episode import EpisodeRepository
from ..repositories.project import ProjectRepository

# Setup logging
try:
    from ai_script_core import get_service_logger

    logger = get_service_logger("project-service.episode-service")
except ImportError:
    import logging

    logger = logging.getLogger(__name__)  # type: ignore[assignment]


class NotFoundError(BaseServiceException):
    def __init__(
        self,
        entity: str = "Resource",
        resource_id: str | None = None,
        message: str | None = None,
    ):
        self.message = message or (
            f"{entity} not found" + (f": {resource_id}" if resource_id else "")
        )
        super().__init__(self.message)


class ValidationError(BaseServiceException):
    def __init__(self, field: str | None = None, message: str = "Validation error"):
        self.message = f"{field}: {message}" if field else message
        super().__init__(self.message)


# Temporary utility function
def generate_id(prefix: str | None = None) -> str:
    base_id = str(uuid.uuid4())
    return f"{prefix}_{base_id}" if prefix else base_id


class EpisodeService:
    """에피소드 비즈니스 로직 서비스"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = EpisodeRepository(db)
        self.project_repository = ProjectRepository(db)

    def create_episode(
        self, project_id: str, title: str, description: str | None = None
    ) -> dict[str, Any]:
        """에피소드 생성 - 원자적 카운터 방식으로 번호 자동 할당"""
        # 프로젝트 존재 확인
        if not self.project_repository.exists(project_id):
            raise NotFoundError("Project", project_id)

        # 에피소드 ID 생성
        episode_id = generate_id("ep")

        # 성능 추적 시작
        performance_tracker = get_performance_tracker()
        operation_id = f"create_episode_{project_id}_{episode_id}"
        performance_tracker.start_operation(operation_id)

        retry_count = 0
        had_conflict = False
        success = False

        # 원자적 트랜잭션으로 에피소드 생성 (동시성 안전)
        try:
            with atomic_transaction(self.db, max_retries=3) as tx_db:
                # 원자적으로 에피소드 번호 할당
                next_number = self.repository.get_next_episode_number_atomic(project_id)
                next_order = self.repository.get_next_order(project_id)

                # 데이터베이스 객체 생성
                db_data = {
                    "id": episode_id,
                    "title": title,
                    "project_id": project_id,
                    "number": next_number,  # 원자적으로 할당된 에피소드 번호
                    "order": next_order,  # 표시 순서
                    "description": description,
                }

                episode = self.repository.create(db_data)
                success = True

                # 성능 메트릭 기록
                duration = performance_tracker.end_operation(
                    operation_id=operation_id,
                    db=self.db,
                    project_id=project_id,
                    episode_id=episode_id,
                    success=success,
                    retry_count=retry_count,
                    had_conflict=had_conflict,
                )

                # 생성 후 무결성 검사 (주기적으로)
                import random

                if random.random() < 0.1:  # 10% 확률로 무결성 검사
                    try:
                        integrity_checker = get_integrity_checker(self.db)
                        alert_manager = get_alert_manager(self.db)

                        # 비동기적으로 무결성 검사 실행
                        import threading

                        def check_integrity() -> None:
                            try:
                                integrity_result = (
                                    integrity_checker.check_project_integrity(
                                        project_id
                                    )
                                )
                                if not integrity_result.is_healthy:
                                    alert_manager.run_all_checks(project_id)
                            except Exception as e:
                                logger.warning(
                                    f"Post-creation integrity check failed: {e}"
                                )

                        threading.Thread(target=check_integrity, daemon=True).start()

                    except Exception as e:
                        logger.debug(f"Could not start integrity check: {e}")

                return episode.to_dict()

        except ConcurrencyError as e:
            had_conflict = True
            success = False

            # 성능 메트릭 기록 (실패)
            performance_tracker.end_operation(
                operation_id=operation_id,
                db=self.db,
                project_id=project_id,
                episode_id=episode_id,
                success=success,
                retry_count=retry_count,
                had_conflict=had_conflict,
            )

            # 충돌율 체크 및 알림
            try:
                alert_manager = get_alert_manager(self.db)
                alert_manager.check_conflict_rate(project_id)
            except Exception:
                pass  # 알림 실패는 에피소드 생성에 영향 주지 않음

            raise ValidationError(
                message=f"Episode creation failed due to concurrency: {e!s}"
            )

        except Exception as e:
            success = False

            # 성능 메트릭 기록 (실패)
            performance_tracker.end_operation(
                operation_id=operation_id,
                db=self.db,
                project_id=project_id,
                episode_id=episode_id,
                success=success,
                retry_count=retry_count,
                had_conflict=had_conflict,
            )

            # 실패율 체크 및 알림
            try:
                alert_manager = get_alert_manager(self.db)
                alert_manager.check_failure_rate(project_id)
            except Exception:
                pass  # 알림 실패는 에피소드 생성에 영향 주지 않음

            raise ValidationError(message=f"Failed to create episode: {e!s}")

    def get_episode(self, episode_id: str) -> dict[str, Any]:
        """에피소드 조회"""
        episode = self.repository.get(episode_id)
        if not episode:
            raise NotFoundError("Episode", episode_id)

        return episode.to_dict()

    def get_episodes_by_project(
        self, project_id: str, published_only: bool = False
    ) -> list[dict[str, Any]]:
        """프로젝트별 에피소드 목록 조회"""
        if published_only:
            episodes = self.repository.get_published_episodes(project_id)
        else:
            episodes = self.repository.get_by_project(project_id)

        return [episode.to_dict() for episode in episodes]

    def update_episode(
        self, episode_id: str, update_data: dict[str, Any]
    ) -> dict[str, Any]:
        """에피소드 수정"""
        # 에피소드 존재 확인
        if not self.repository.exists(episode_id):
            raise NotFoundError("Episode", episode_id)

        # None이 아닌 값만 필터링
        filtered_data = {k: v for k, v in update_data.items() if v is not None}

        episode = self.repository.update(episode_id, filtered_data)
        if not episode:
            raise NotFoundError("Episode", episode_id)

        return episode.to_dict()

    def delete_episode(self, episode_id: str) -> bool:
        """에피소드 삭제"""
        if not self.repository.exists(episode_id):
            raise NotFoundError("Episode", episode_id)

        return self.repository.delete(episode_id)

    def publish_episode(self, episode_id: str) -> dict[str, Any]:
        """에피소드 공개"""
        episode = self.repository.publish_episode(episode_id)
        if not episode:
            raise NotFoundError("Episode", episode_id)

        return episode.to_dict()

    def unpublish_episode(self, episode_id: str) -> dict[str, Any]:
        """에피소드 비공개"""
        episode = self.repository.unpublish_episode(episode_id)
        if not episode:
            raise NotFoundError("Episode", episode_id)

        return episode.to_dict()

    def reorder_episodes(
        self, project_id: str, episode_orders: list[dict[str, Any]]
    ) -> bool:
        """에피소드 순서 재정렬"""
        # 프로젝트 존재 확인
        if not self.project_repository.exists(project_id):
            raise NotFoundError("Project", project_id)

        return self.repository.reorder_episodes(project_id, episode_orders)

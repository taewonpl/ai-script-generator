"""
Transaction management utilities for atomic operations
"""

import random
import time
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session


class ConcurrencyError(Exception):
    """Raised when a concurrency conflict occurs"""

    pass


@contextmanager
def atomic_transaction(
    db: Session,
    isolation_level: str = "SERIALIZABLE",
    max_retries: int = 3,
    base_delay: float = 0.1,
) -> Generator[Session, None, None]:
    """
    Context manager for atomic transactions with retry logic and SERIALIZABLE isolation

    Args:
        db: SQLAlchemy session
        isolation_level: Transaction isolation level (SERIALIZABLE recommended)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff (seconds)
    """

    for attempt in range(max_retries + 1):
        try:
            # Set SERIALIZABLE isolation level for maximum consistency
            db.execute(text("PRAGMA read_uncommitted = false"))

            # Begin immediate transaction to acquire exclusive lock
            db.execute(text("BEGIN IMMEDIATE"))

            try:
                yield db
                db.commit()
                return  # Success - exit retry loop

            except (IntegrityError, OperationalError) as e:
                db.rollback()

                # Check if this is a concurrency-related error
                error_msg = str(e).lower()
                if any(
                    keyword in error_msg
                    for keyword in [
                        "database is locked",
                        "unique constraint",
                        "serialization failure",
                        "deadlock",
                    ]
                ):
                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        delay = base_delay * (2**attempt) + random.uniform(0, 0.1)
                        time.sleep(delay)
                        continue
                    else:
                        raise ConcurrencyError(f"Max retries exceeded: {e}")
                else:
                    # Non-concurrency error - don't retry
                    raise

        except Exception:
            # Ensure rollback on any error
            try:
                db.rollback()
            except:
                pass

            if attempt == max_retries:
                raise

    raise ConcurrencyError(f"Transaction failed after {max_retries} retries")

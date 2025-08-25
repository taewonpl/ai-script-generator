"""
Advanced Helper Utilities for AI Script Generator v3.0

UUID 생성, 날짜 포맷팅, 텍스트 정제, 서비스 상태 확인 등 공통 헬퍼 함수를 제공합니다.
"""

import asyncio
import hashlib
import json
import re
import secrets
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
import requests

# =============================================================================
# UUID 생성 유틸리티
# =============================================================================


def generate_uuid() -> str:
    """
    표준 UUID4 생성

    Returns:
        생성된 UUID 문자열 (하이픈 포함)
    """
    return str(uuid.uuid4())


def generate_uuid_hex() -> str:
    """
    하이픈 없는 UUID4 생성

    Returns:
        생성된 UUID 문자열 (하이픈 없음)
    """
    return uuid.uuid4().hex


def generate_prefixed_id(prefix: str) -> str:
    """
    접두사가 있는 ID 생성

    Args:
        prefix: ID 접두사

    Returns:
        접두사_UUID 형태의 ID
    """
    return f"{prefix}_{generate_uuid()}"


def generate_short_id(length: int = 8) -> str:
    """
    URL-safe한 짧은 ID 생성

    Args:
        length: 생성할 ID의 길이

    Returns:
        URL-safe 짧은 ID
    """
    return secrets.token_urlsafe(length)[:length]


def generate_numeric_id(length: int = 8) -> str:
    """
    숫자로만 구성된 ID 생성

    Args:
        length: 생성할 ID의 길이

    Returns:
        숫자로만 구성된 ID
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


# =============================================================================
# 날짜/시간 포맷팅 유틸리티
# =============================================================================


def format_datetime(
    dt: datetime | None = None, format_type: str = "iso", timezone_aware: bool = True
) -> str:
    """
    날짜/시간을 다양한 형식으로 포맷

    Args:
        dt: 포맷할 datetime 객체 (None이면 현재 시간 사용)
        format_type: 포맷 타입 ('iso', 'standard', 'compact', 'human')
        timezone_aware: 시간대 정보 포함 여부

    Returns:
        포맷된 날짜/시간 문자열
    """
    if dt is None:
        dt = datetime.now(timezone.utc if timezone_aware else None)

    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "standard":
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif format_type == "compact":
        return dt.strftime("%Y%m%d_%H%M%S")
    elif format_type == "human":
        return dt.strftime("%Y년 %m월 %d일 %H:%M:%S")
    elif format_type == "date_only":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time_only":
        return dt.strftime("%H:%M:%S")
    else:
        return dt.strftime(format_type)  # 사용자 정의 포맷


def parse_datetime(
    date_string: str, formats: list[str] | None = None
) -> datetime | None:
    """
    문자열을 datetime으로 파싱 (여러 포맷 시도)

    Args:
        date_string: 파싱할 날짜 문자열
        formats: 시도할 포맷 목록

    Returns:
        파싱된 datetime 객체 또는 None
    """
    if formats is None:
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
        ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    return None


def utc_now() -> datetime:
    """현재 UTC 시간 반환"""
    return datetime.now(timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """datetime을 UTC로 변환"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def calculate_age(
    from_date: datetime, to_date: datetime | None = None
) -> dict[str, int]:
    """
    두 날짜 사이의 시간 차이 계산

    Args:
        from_date: 시작 날짜
        to_date: 종료 날짜 (None이면 현재 시간)

    Returns:
        시간 차이 정보 (days, hours, minutes, seconds)
    """
    if to_date is None:
        to_date = utc_now()

    delta = to_date - from_date

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "days": days,
        "hours": hours,
        "minutes": minutes,
        "seconds": seconds,
        "total_seconds": int(delta.total_seconds()),
    }


# =============================================================================
# 텍스트 정제 유틸리티
# =============================================================================


def sanitize_text(
    text: str,
    remove_html: bool = True,
    normalize_whitespace: bool = True,
    remove_special_chars: bool = False,
    max_length: int | None = None,
) -> str:
    """
    텍스트 정제

    Args:
        text: 정제할 텍스트
        remove_html: HTML 태그 제거 여부
        normalize_whitespace: 공백 정규화 여부
        remove_special_chars: 특수 문자 제거 여부
        max_length: 최대 길이 제한

    Returns:
        정제된 텍스트
    """
    if not text:
        return ""

    result = str(text)

    # HTML 태그 제거
    if remove_html:
        result = re.sub(r"<[^>]+>", "", result)
        # HTML 엔티티 디코딩
        import html

        result = html.unescape(result)

    # 공백 정규화
    if normalize_whitespace:
        result = re.sub(r"\s+", " ", result).strip()

    # 특수 문자 제거 (알파벳, 숫자, 기본 구두점만 유지)
    if remove_special_chars:
        result = re.sub(r"[^\w\s\.,!?;:()-]", "", result)

    # 길이 제한
    if max_length and len(result) > max_length:
        result = result[:max_length].rsplit(" ", 1)[0] + "..."

    return result


def clean_filename(filename: str, max_length: int = 255) -> str:
    """
    파일명 정제 (안전한 파일명으로 변환)

    Args:
        filename: 정제할 파일명
        max_length: 최대 파일명 길이

    Returns:
        정제된 파일명
    """
    # 위험한 문자 제거
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

    # 연속된 점이나 공백 제거
    cleaned = re.sub(r"[.\s]+", "_", cleaned)

    # 앞뒤 공백 및 점 제거
    cleaned = cleaned.strip(". ")

    # 길이 제한
    if len(cleaned) > max_length:
        name, ext = Path(cleaned).stem, Path(cleaned).suffix
        max_name_length = max_length - len(ext)
        cleaned = name[:max_name_length] + ext

    # 빈 문자열 처리
    if not cleaned:
        cleaned = f"unnamed_{generate_short_id(6)}"

    return cleaned


def extract_emails(text: str) -> list[str]:
    """텍스트에서 이메일 주소 추출"""
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return re.findall(email_pattern, text)


def extract_urls(text: str) -> list[str]:
    """텍스트에서 URL 추출"""
    url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
    return re.findall(url_pattern, text)


def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
    """민감한 데이터 마스킹"""
    # 이메일 마스킹
    text = re.sub(
        r"(\w+)@(\w+\.\w+)",
        lambda m: f"{m.group(1)[:2]}{mask_char * 3}@{m.group(2)}",
        text,
    )

    # 전화번호 마스킹
    text = re.sub(
        r"(\d{3})-?(\d{3,4})-?(\d{4})",
        lambda m: f"{m.group(1)}-{mask_char * len(m.group(2))}-{m.group(3)}",
        text,
    )

    return text


# =============================================================================
# 서비스 상태 확인 유틸리티
# =============================================================================


def validate_service_health(
    service_url: str,
    timeout: int = 5,
    expected_status: int = 200,
    health_endpoint: str = "/health",
) -> dict[str, Any]:
    """
    서비스 상태 확인 (동기)

    Args:
        service_url: 서비스 URL
        timeout: 타임아웃(초)
        expected_status: 예상 상태 코드
        health_endpoint: 헬스 체크 엔드포인트

    Returns:
        상태 확인 결과
    """
    result = {
        "service_url": service_url,
        "is_healthy": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
        "timestamp": utc_now().isoformat(),
    }

    try:
        # URL 파싱 및 검증
        parsed_url = urlparse(service_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")

        # 헬스 체크 URL 구성
        health_url = service_url.rstrip("/") + health_endpoint

        # 요청 시작 시간
        start_time = datetime.now()

        # HTTP 요청
        response = requests.get(
            health_url,
            timeout=timeout,
            headers={"User-Agent": "AI-Script-Generator-HealthChecker/3.0"},
        )

        # 응답 시간 계산
        response_time = (datetime.now() - start_time).total_seconds() * 1000

        result.update(
            {
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "is_healthy": response.status_code == expected_status,
            }
        )

        # 응답 본문에서 추가 정보 추출 (JSON인 경우)
        try:
            response_data = response.json()
            if isinstance(response_data, dict):
                result["service_info"] = {
                    "version": response_data.get("version"),
                    "status": response_data.get("status"),
                    "database": response_data.get("database_status"),
                    "dependencies": response_data.get("dependencies"),
                }
        except json.JSONDecodeError:
            pass

    except requests.exceptions.Timeout:
        result["error"] = "Request timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection error"
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request error: {e!s}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e!s}"

    return result


async def validate_service_health_async(
    service_url: str,
    timeout: int = 5,
    expected_status: int = 200,
    health_endpoint: str = "/health",
) -> dict[str, Any]:
    """
    서비스 상태 확인 (비동기)

    Args:
        service_url: 서비스 URL
        timeout: 타임아웃(초)
        expected_status: 예상 상태 코드
        health_endpoint: 헬스 체크 엔드포인트

    Returns:
        상태 확인 결과
    """
    result = {
        "service_url": service_url,
        "is_healthy": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
        "timestamp": utc_now().isoformat(),
    }

    try:
        # URL 파싱 및 검증
        parsed_url = urlparse(service_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError("Invalid URL format")

        # 헬스 체크 URL 구성
        health_url = service_url.rstrip("/") + health_endpoint

        # 요청 시작 시간
        start_time = datetime.now()

        # 비동기 HTTP 요청
        async with aiohttp.ClientSession() as session:
            async with session.get(
                health_url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": "AI-Script-Generator-HealthChecker/3.0"},
            ) as response:
                # 응답 시간 계산
                response_time = (datetime.now() - start_time).total_seconds() * 1000

                result.update(
                    {
                        "status_code": response.status,
                        "response_time_ms": round(response_time, 2),
                        "is_healthy": response.status == expected_status,
                    }
                )

                # 응답 본문에서 추가 정보 추출 (JSON인 경우)
                try:
                    response_data = await response.json()
                    if isinstance(response_data, dict):
                        result["service_info"] = {
                            "version": response_data.get("version"),
                            "status": response_data.get("status"),
                            "database": response_data.get("database_status"),
                            "dependencies": response_data.get("dependencies"),
                        }
                except:
                    pass

    except asyncio.TimeoutError:
        result["error"] = "Request timeout"
    except aiohttp.ClientConnectorError:
        result["error"] = "Connection error"
    except Exception as e:
        result["error"] = f"Unexpected error: {e!s}"

    return result


def check_multiple_services(
    services: list[str], timeout: int = 5, max_workers: int = 10
) -> dict[str, dict[str, Any]]:
    """
    여러 서비스 상태를 동시에 확인

    Args:
        services: 서비스 URL 목록
        timeout: 각 요청의 타임아웃
        max_workers: 최대 동시 실행 수

    Returns:
        서비스별 상태 확인 결과
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 서비스에 대한 future 생성
        future_to_service = {
            executor.submit(validate_service_health, service, timeout): service
            for service in services
        }

        # 결과 수집
        for future in as_completed(future_to_service):
            service = future_to_service[future]
            try:
                results[service] = future.result()
            except Exception as e:
                results[service] = {
                    "service_url": service,
                    "is_healthy": False,
                    "error": f"Health check failed: {e!s}",
                    "timestamp": utc_now().isoformat(),
                }

    return results


# =============================================================================
# 기타 유틸리티 함수
# =============================================================================


def calculate_hash(data: str | bytes, algorithm: str = "sha256") -> str:
    """
    데이터의 해시값 계산

    Args:
        data: 해시할 데이터
        algorithm: 해시 알고리즘

    Returns:
        해시값 (hex 문자열)
    """
    if isinstance(data, str):
        data = data.encode("utf-8")

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data)
    return hash_obj.hexdigest()


def safe_json_loads(data: str, default: Any = None) -> Any:
    """안전한 JSON 파싱"""
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default


def safe_json_dumps(obj: Any, default: Any = None, **kwargs: Any) -> str:
    """안전한 JSON 직렬화"""
    try:
        return json.dumps(obj, ensure_ascii=False, default=str, **kwargs)
    except (TypeError, ValueError):
        return default or "{}"


def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    """딕셔너리 깊은 병합"""
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def get_env_var(key: str, default: Any = None, var_type: type = str) -> Any:
    """환경 변수 값 가져오기 (타입 변환 포함)"""
    import os

    value = os.getenv(key, default)

    if value is None or value == "":
        return default

    if var_type == bool:
        return str(value).lower() in ("true", "1", "yes", "on")
    elif var_type == int:
        try:
            return int(value)
        except ValueError:
            return default
    elif var_type == float:
        try:
            return float(value)
        except ValueError:
            return default
    elif var_type == list:
        try:
            return [item.strip() for item in str(value).split(",") if item.strip()]
        except:
            return default or []
    else:
        return var_type(value)


def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[..., Any]:
    """
    지수 백오프를 사용한 재시도 데코레이터

    Args:
        func: 재시도할 함수
        max_retries: 최대 재시도 횟수
        base_delay: 기본 지연 시간
        max_delay: 최대 지연 시간
        backoff_factor: 백오프 배수
        exceptions: 재시도할 예외 타입들
    """
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delay = base_delay
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e

                if attempt == max_retries:
                    raise e

                time.sleep(min(delay, max_delay))
                delay *= backoff_factor

        if last_exception:
            raise last_exception
        else:
            raise Exception("All retry attempts failed")

    return wrapper

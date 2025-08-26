"""
Logging filters for sensitive data masking and security
"""

import logging
import re
from collections.abc import Mapping
from typing import Any


class APIKeyMaskingFilter(logging.Filter):
    """Filter to mask API keys and sensitive data in log messages"""

    def __init__(self) -> None:
        super().__init__()

        # Common API key patterns
        self.api_key_patterns = [
            # OpenAI API keys
            re.compile(r"\bsk-[A-Za-z0-9]{20,}\b", re.IGNORECASE),
            # Anthropic API keys
            re.compile(r"\bant-api-[A-Za-z0-9]{20,}\b", re.IGNORECASE),
            # Generic bearer tokens
            re.compile(r"\bBearer\s+[A-Za-z0-9+/=]{20,}\b", re.IGNORECASE),
            # Generic API keys (various formats)
            re.compile(
                r'\b(?:api[_-]?key|token|secret)["\']?\s*[:=]\s*["\']?([A-Za-z0-9+/=]{20,})["\']?\b',
                re.IGNORECASE,
            ),
            # AWS access keys
            re.compile(r"\bAKIA[0-9A-Z]{16}\b", re.IGNORECASE),
            # Database URLs with passwords
            re.compile(r"(postgresql|mysql|mongodb)://[^:]+:([^@]+)@", re.IGNORECASE),
            # Redis URLs with passwords
            re.compile(r"redis://[^:]*:([^@]+)@", re.IGNORECASE),
            # JWT tokens
            re.compile(
                r"\beyJ[A-Za-z0-9+/=]{20,}\.[A-Za-z0-9+/=]{20,}\.[A-Za-z0-9+/=]{20,}\b",
                re.IGNORECASE,
            ),
        ]

        # Sensitive field names to mask completely
        self.sensitive_fields = {
            "password",
            "passwd",
            "pwd",
            "secret",
            "token",
            "key",
            "api_key",
            "apikey",
            "access_token",
            "refresh_token",
            "private_key",
            "secret_key",
            "openai_api_key",
            "anthropic_api_key",
            "azure_openai_key",
            "cohere_api_key",
        }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and mask sensitive data in log record"""
        try:
            # Mask message content
            if hasattr(record, "msg") and record.msg:
                record.msg = self._mask_sensitive_data(str(record.msg))

            # Mask arguments if present
            if hasattr(record, "args") and record.args:
                record.args = self._mask_args(record.args)

            # Mask extra fields
            if hasattr(record, "__dict__"):
                for key, value in record.__dict__.items():
                    if key.lower() in self.sensitive_fields and isinstance(value, str):
                        setattr(record, key, self._mask_value(value))

            return True

        except Exception as e:
            # Don't fail logging if masking fails
            print(f"Warning: Failed to mask sensitive data in log: {e}")
            return True

    def _mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data in text using patterns"""
        if not text:
            return text

        masked_text = text

        # Apply all patterns
        for pattern in self.api_key_patterns:
            masked_text = pattern.sub(self._replace_with_mask, masked_text)

        return masked_text

    def _replace_with_mask(self, match: re.Match[str]) -> str:
        """Replace matched sensitive data with masked version"""
        matched_text = match.group(0)

        # For database URLs, preserve structure but mask password
        if "://" in matched_text and "@" in matched_text:
            parts = matched_text.split("://")
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if ":" in rest and "@" in rest:
                    user_pass, host_part = rest.split("@", 1)
                    if ":" in user_pass:
                        user, password = user_pass.split(":", 1)
                        masked_password = self._mask_value(password)
                        return f"{scheme}://{user}:{masked_password}@{host_part}"

        # For other patterns, mask the sensitive part
        return self._mask_value(matched_text)

    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value while preserving some context"""
        if not value or len(value) < 8:
            return "***"

        # Show first 4 and last 4 characters
        return f"{value[:4]}...{value[-4:]}"

    def _mask_args(self, args: tuple[Any, ...] | Mapping[str, Any]) -> tuple[Any, ...]:
        """Mask sensitive data in log arguments"""
        if not args:
            return ()

        # Handle Mapping case (keyword arguments)
        if isinstance(args, Mapping):
            # Convert mapping to tuple of values for compatibility
            return tuple(args.values())

        # Handle tuple case
        masked_args: list[Any] = []
        for arg in args:
            if isinstance(arg, str):
                masked_args.append(self._mask_sensitive_data(arg))
            elif isinstance(arg, dict):
                masked_args.append(self._mask_dict(arg))
            elif isinstance(arg, (list, tuple)):
                masked_args.append(self._mask_collection(arg))
            else:
                masked_args.append(arg)

        return tuple(masked_args)

    def _mask_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive data in dictionary"""
        if not isinstance(data, dict):
            return data

        masked_dict = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                masked_dict[key] = self._mask_value(str(value)) if value else value
            elif isinstance(value, str):
                masked_dict[key] = self._mask_sensitive_data(value)
            elif isinstance(value, dict):
                masked_dict[key] = self._mask_dict(value)
            elif isinstance(value, (list, tuple)):
                masked_dict[key] = self._mask_collection(value)
            else:
                masked_dict[key] = value

        return masked_dict

    def _mask_collection(
        self, data: list[Any] | tuple[Any, ...]
    ) -> list[Any] | tuple[Any, ...]:
        """Mask sensitive data in list/tuple"""
        if not isinstance(data, (list, tuple)):
            return data

        masked_items: list[Any] = []
        for item in data:
            if isinstance(item, str):
                masked_items.append(self._mask_sensitive_data(item))
            elif isinstance(item, dict):
                masked_items.append(self._mask_dict(item))
            elif isinstance(item, (list, tuple)):
                masked_items.append(self._mask_collection(item))
            else:
                masked_items.append(item)

        # Type-safe reconstruction
        if isinstance(data, list):
            return masked_items
        else:
            return tuple(masked_items)


class StructuredLoggingFilter(logging.Filter):
    """Filter to add structured logging context"""

    def __init__(self, service_name: str = "generation-service") -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:
        """Add structured context to log record"""
        try:
            # Add service context
            record.service = self.service_name

            # Add request context if available
            if not hasattr(record, "request_id"):
                record.request_id = getattr(record, "request_id", None)

            # Add user context if available
            if not hasattr(record, "user_id"):
                record.user_id = getattr(record, "user_id", None)

            # Add correlation ID if available
            if not hasattr(record, "correlation_id"):
                record.correlation_id = getattr(record, "correlation_id", None)

            return True

        except Exception as e:
            print(f"Warning: Failed to add structured context: {e}")
            return True


class PerformanceLoggingFilter(logging.Filter):
    """Filter to add performance metrics to logs"""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add performance context to log record"""
        try:
            # Add timing information if available
            if hasattr(record, "duration_ms"):
                record.performance = True

            # Mark slow operations
            if hasattr(record, "duration_ms") and record.duration_ms > 1000:
                record.slow_operation = True

            return True

        except Exception as e:
            print(f"Warning: Failed to add performance context: {e}")
            return True


def setup_logging_filters(
    logger: logging.Logger, service_name: str = "generation-service"
) -> None:
    """Setup all logging filters for a logger"""

    # Add API key masking filter
    api_key_filter = APIKeyMaskingFilter()
    logger.addFilter(api_key_filter)

    # Add structured logging filter
    structured_filter = StructuredLoggingFilter(service_name)
    logger.addFilter(structured_filter)

    # Add performance logging filter
    performance_filter = PerformanceLoggingFilter()
    logger.addFilter(performance_filter)

    return logger


def get_filtered_logger(
    name: str, service_name: str = "generation-service"
) -> logging.Logger:
    """Get a logger with all security filters applied"""
    logger = logging.getLogger(name)
    return setup_logging_filters(logger, service_name)

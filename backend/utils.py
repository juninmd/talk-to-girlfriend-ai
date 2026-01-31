import re
import datetime
import asyncio
from enum import Enum
from typing import Optional, Union, Any, Dict
from functools import wraps
from backend.logging_setup import logger


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class ErrorCategory(str, Enum):
    CHAT = "CHAT"
    MSG = "MSG"
    CONTACT = "CONTACT"
    GROUP = "GROUP"
    MEDIA = "MEDIA"
    PROFILE = "PROFILE"
    AUTH = "AUTH"
    ADMIN = "ADMIN"


def json_serializer(obj):
    """Helper function to convert non-serializable objects for JSON serialization."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def log_and_format_error(
    function_name: str,
    error: Exception,
    prefix: Optional[Union[ErrorCategory, str]] = None,
    user_message: str = None,
    **kwargs,
) -> str:
    """
    Centralized error handling function.
    """
    if isinstance(prefix, str) and prefix == "VALIDATION-001":
        error_code = prefix
    else:
        if prefix is None:
            for category in ErrorCategory:
                if category.name.lower() in function_name.lower():
                    prefix = category
                    break
        prefix_str = prefix.value if isinstance(prefix, ErrorCategory) else (prefix or "GEN")
        error_code = f"{prefix_str}-ERR-{abs(hash(function_name)) % 1000:03d}"

    context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(f"Error in {function_name} ({context}) - Code: {error_code}", exc_info=True)

    if user_message:
        return user_message

    return f"An error occurred (code: {error_code}). Check mcp_errors.log for details."


def validate_id(*param_names_to_validate):
    """
    Decorator to validate chat_id and user_id parameters.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for param_name in param_names_to_validate:
                if param_name not in kwargs or kwargs[param_name] is None:
                    continue

                param_value = kwargs[param_name]

                def validate_single_id(value, p_name):
                    if isinstance(value, int):
                        if not (-(2**63) <= value <= 2**63 - 1):
                            return (
                                None,
                                f"Invalid {p_name}: {value}. ID is out of range.",
                            )
                        return value, None
                    if isinstance(value, str):
                        try:
                            int_value = int(value)
                            if not (-(2**63) <= int_value <= 2**63 - 1):
                                return (
                                    None,
                                    f"Invalid {p_name}: {value}. ID is out of range.",
                                )
                            return int_value, None
                        except ValueError:
                            if re.match(r"^@?[a-zA-Z0-9_]{5,}$", value):
                                return value, None
                            else:
                                return (
                                    None,
                                    f"Invalid {p_name}: '{value}'. Must be integer or username.",
                                )
                    return (
                        None,
                        f"Invalid {p_name}: {value}. Type must be int or str.",
                    )

                if isinstance(param_value, list):
                    validated_list = []
                    for item in param_value:
                        validated_item, error_msg = validate_single_id(item, param_name)
                        if error_msg:
                            return log_and_format_error(
                                func.__name__,
                                ValidationError(error_msg),
                                prefix="VALIDATION-001",
                                user_message=error_msg,
                                **{param_name: param_value},
                            )
                        validated_list.append(validated_item)
                    kwargs[param_name] = validated_list
                else:
                    validated_value, error_msg = validate_single_id(param_value, param_name)
                    if error_msg:
                        return log_and_format_error(
                            func.__name__,
                            ValidationError(error_msg),
                            prefix="VALIDATION-001",
                            user_message=error_msg,
                            **{param_name: param_value},
                        )
                    kwargs[param_name] = validated_value

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def format_entity(entity) -> Dict[str, Any]:
    from telethon.tl.types import Chat

    result = {"id": entity.id}
    if hasattr(entity, "title"):
        result["name"] = entity.title
        result["type"] = "group" if isinstance(entity, Chat) else "channel"
    elif hasattr(entity, "first_name"):
        name_parts = []
        if entity.first_name:
            name_parts.append(entity.first_name)
        if hasattr(entity, "last_name") and entity.last_name:
            name_parts.append(entity.last_name)
        result["name"] = " ".join(name_parts)
        result["type"] = "user"
        if hasattr(entity, "username") and entity.username:
            result["username"] = entity.username
        if hasattr(entity, "phone") and entity.phone:
            result["phone"] = entity.phone
    return result


def get_sender_name(message) -> str:
    if not message.sender:
        return "Unknown"
    if hasattr(message.sender, "title") and message.sender.title:
        return message.sender.title
    elif hasattr(message.sender, "first_name"):
        first_name = getattr(message.sender, "first_name", "") or ""
        last_name = getattr(message.sender, "last_name", "") or ""
        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else "Unknown"
    else:
        return "Unknown"


def async_retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry async functions with exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. Error: {e}"
                        )
                        raise e

                    logger.warning(
                        f"Function {func.__name__} failed (Attempt {attempts}/{max_attempts}). "
                        f"Retrying in {current_delay}s... Error: {e}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff

        return wrapper

    return decorator

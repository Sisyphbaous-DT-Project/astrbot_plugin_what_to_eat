"""频率限制器模块，防止多Bot循环触发。"""

from __future__ import annotations

import time
from typing import Any

from astrbot.api import logger


class RateLimiter:
    """
    频率限制器，按群组记录响应次数，防止多Bot循环触发。
    
    在指定时间窗口内，超过最大响应次数后，会强制推荐食物（而非复读）。
    """

    def __init__(self, max_responses: int = 3, window_seconds: int = 60) -> None:
        """
        Initialize the rate limiter.

        Args:
            max_responses: Maximum number of responses in the time window
            window_seconds: Time window in seconds
        """
        self.max_responses = max(1, max_responses)
        self.window_seconds = window_seconds
        # 存储格式: {group_id: [timestamp1, timestamp2, ...]}
        self._response_history: dict[str, list[float]] = {}
        logger.info(f"RateLimiter initialized: max={self.max_responses}, window={self.window_seconds}s")

    def can_respond(self, group_id: str) -> tuple[bool, bool]:
        """
        Check if the plugin can respond and whether to force recommendation.

        Args:
            group_id: Group ID or sender ID for private chats

        Returns:
            Tuple of (can_respond: bool, force_recommend: bool)
            - can_respond: Whether to allow this response
            - force_recommend: Whether to force food recommendation (exceeded limit)
        """
        if not group_id:
            # No group ID, allow response but don't force recommend
            return True, False

        # Clean up old records first
        self._cleanup_old_records(group_id)

        # Get current response count
        history = self._response_history.get(group_id, [])
        current_count = len(history)

        if current_count < self.max_responses:
            # Within limit, normal behavior
            return True, False
        else:
            # Exceeded limit, force recommend food
            logger.debug(f"Rate limit exceeded for {group_id}: {current_count} >= {self.max_responses}")
            return True, True

    def record_response(self, group_id: str) -> None:
        """
        Record a response for the given group.

        Args:
            group_id: Group ID or sender ID
        """
        if not group_id:
            return

        if group_id not in self._response_history:
            self._response_history[group_id] = []

        self._response_history[group_id].append(time.time())

    def _cleanup_old_records(self, group_id: str) -> None:
        """
        Remove records outside the time window.

        Args:
            group_id: Group ID to clean up
        """
        if group_id not in self._response_history:
            return

        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        # Keep only records within the time window
        self._response_history[group_id] = [
            ts for ts in self._response_history[group_id] if ts > cutoff_time
        ]

        # Remove empty entries to save memory
        if not self._response_history[group_id]:
            del self._response_history[group_id]

    def clear_all(self) -> None:
        """Clear all rate limit history. Useful for testing."""
        self._response_history.clear()
        logger.info("RateLimiter history cleared")

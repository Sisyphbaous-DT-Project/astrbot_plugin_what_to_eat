"""频率限制器模块，防止多Bot循环触发。"""

from __future__ import annotations

import time
from typing import Any

from astrbot.api import logger


class RateLimiter:
    """
    频率限制器，按群组记录响应次数，防止多Bot循环触发。
    
    在指定时间窗口内，超过最大响应次数后，会强制推荐食物（而非复读）。
    同时支持复读冷却功能，复读后的一段时间内强制推荐食物。
    """

    def __init__(
        self,
        max_responses: int = 3,
        window_seconds: int = 60,
        echo_cooldown_enabled: bool = True,
        echo_cooldown_seconds: int = 15,
    ) -> None:
        """
        初始化频率限制器。

        Args:
            max_responses: 时间窗口内最大响应次数
            window_seconds: 时间窗口（秒）
            echo_cooldown_enabled: 是否启用复读冷却
            echo_cooldown_seconds: 复读后的冷却时间（秒）
        """
        self.max_responses = max(1, max_responses)
        self.window_seconds = window_seconds
        self.echo_cooldown_enabled = echo_cooldown_enabled
        # 将冷却时间限制在合理范围（0到1小时）
        self.echo_cooldown_seconds = max(0, min(3600, echo_cooldown_seconds))
        # 存储格式: {group_id: [timestamp1, timestamp2, ...]}
        self._response_history: dict[str, list[float]] = {}
        # 存储格式: {group_id: last_echo_timestamp}
        self._echo_cooldown_map: dict[str, float] = {}
        logger.info(
            f"频率限制器初始化: max={self.max_responses}, window={self.window_seconds}s, "
            f"echo_cooldown={self.echo_cooldown_enabled}, cooldown_seconds={self.echo_cooldown_seconds}s"
        )

    def can_respond(self, group_id: str) -> tuple[bool, bool]:
        """
        检查插件是否可以响应以及是否强制推荐。

        Args:
            group_id: 群组 ID 或私聊的发送者 ID

        Returns:
            (can_respond: bool, force_recommend: bool) 元组
            - can_respond: 始终为 True（此插件始终响应）
            - force_recommend: 是否强制推荐食物（超出限制）
        
        注意:
            此方法仅决定是否强制推荐食物，而不是是否阻止响应。
        """
        if not group_id:
            # 无群组 ID，允许响应但不强制推荐
            return True, False

        # 先清理旧记录
        self._cleanup_old_records(group_id)

        # 获取当前响应次数
        history = self._response_history.get(group_id, [])
        current_count = len(history)

        if current_count < self.max_responses:
            # 在限制内，正常行为
            return True, False
        else:
            # 超出限制，强制推荐食物
            logger.debug(f"群组 {group_id} 超出频率限制: {current_count} >= {self.max_responses}")
            return True, True

    def record_response(self, group_id: str) -> None:
        """
        记录指定群组的响应。

        Args:
            group_id: 群组 ID 或发送者 ID
        """
        if not group_id:
            return

        if group_id not in self._response_history:
            self._response_history[group_id] = []

        self._response_history[group_id].append(time.time())

    def _cleanup_old_records(self, group_id: str) -> None:
        """
        移除时间窗口外的旧记录。

        Args:
            group_id: 要清理的群组 ID
        """
        if group_id not in self._response_history:
            return

        current_time = time.time()
        cutoff_time = current_time - self.window_seconds

        # 只保留时间窗口内的记录
        self._response_history[group_id] = [
            ts for ts in self._response_history[group_id] if ts > cutoff_time
        ]

        # 移除空条目以节省内存
        if not self._response_history[group_id]:
            del self._response_history[group_id]

    def is_in_echo_cooldown(self, group_id: str) -> bool:
        """
        检查群组是否处于复读冷却期。

        Args:
            group_id: 群组 ID 或私聊发送者 ID

        Returns:
            如果在冷却期内返回 True，否则返回 False
        """
        if not self.echo_cooldown_enabled or not group_id:
            return False

        # 定期清理过期的冷却记录
        self._cleanup_echo_cooldown()

        last_echo = self._echo_cooldown_map.get(group_id)
        if last_echo is None:
            return False

        return time.time() - last_echo < self.echo_cooldown_seconds

    def record_echo(self, group_id: str) -> None:
        """
        记录复读响应用于冷却追踪。

        Args:
            group_id: 群组 ID 或发送者 ID
        """
        if group_id and self.echo_cooldown_enabled:
            self._echo_cooldown_map[group_id] = time.time()
            logger.debug(f"复读已记录: {group_id}, cooldown={self.echo_cooldown_seconds}s")

    def _cleanup_echo_cooldown(self) -> None:
        """
        移除过期的复读冷却记录以防止内存泄漏。
        超过 2 倍冷却期的记录被视为过期。
        """
        if not self._echo_cooldown_map:
            return

        current_time = time.time()
        # 使用 2 倍冷却期作为清理的安全边距
        cutoff_time = current_time - (self.echo_cooldown_seconds * 2)

        expired_groups = [
            gid for gid, ts in self._echo_cooldown_map.items()
            if ts < cutoff_time
        ]
        for gid in expired_groups:
            del self._echo_cooldown_map[gid]

        if expired_groups:
            logger.debug(f"清理了 {len(expired_groups)} 条过期的复读冷却记录")

    def clear_all(self) -> None:
        """清除所有频率限制历史记录。测试时有用。"""
        self._response_history.clear()
        self._echo_cooldown_map.clear()
        logger.info("频率限制器历史记录已清除")

    def check_and_record(self, group_id: str) -> tuple[bool, bool]:
        """
        原子性地检查频率限制并记录响应。
        
        此方法结合 can_respond() 和 record_response() 以避免
        多线程/多协程环境中的竞态条件。

        Args:
            group_id: 群组 ID 或私聊发送者 ID

        Returns:
            (can_respond: bool, force_recommend: bool) 元组
        """
        can_respond, force_recommend = self.can_respond(group_id)
        if can_respond:
            self.record_response(group_id)
        return can_respond, force_recommend

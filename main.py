"""吃什么推荐插件主文件。"""

from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .food_data import FoodDataManager
from .rate_limiter import RateLimiter
from .responder import Responder


class WhatToEatPlugin(Star):
    """
    吃什么推荐插件。

    识别消息中的"吃什么"关键词，根据配置概率：
    - 推荐大学生常吃的美食
    - 或复读"是啊，吃什么"

    新增：频率限制功能，防止多Bot循环触发
    """

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        """
        Initialize the plugin.

        Args:
            context: AstrBot context
            config: Plugin configuration
        """
        super().__init__(context)
        self.config = config

        # Read configuration with defaults
        probability = config.get("recommend_probability", 0.3)

        # Initialize rate limiter
        rate_limit_enabled = config.get("rate_limit_enabled", True)
        rate_limit_max = config.get("rate_limit_max", 3)
        rate_limit_window = config.get("rate_limit_window_seconds", 60)
        echo_cooldown_enabled = config.get("echo_cooldown_enabled", True)
        echo_cooldown_seconds = config.get("echo_cooldown_seconds", 15)
        if rate_limit_enabled:
            self.rate_limiter = RateLimiter(
                max_responses=rate_limit_max,
                window_seconds=rate_limit_window,
                echo_cooldown_enabled=echo_cooldown_enabled,
                echo_cooldown_seconds=echo_cooldown_seconds,
            )
        else:
            self.rate_limiter = None

        # Initialize components
        self.food_manager = FoodDataManager(config)
        self.responder = Responder(probability)

        logger.info("吃什么插件初始化成功")

    @filter.regex(r"吃什么")
    async def on_what_to_eat(self, event: AstrMessageEvent, *args, **kwargs):
        """
        处理包含"吃什么"的消息。

        Args:
            event: 消息事件
            **kwargs: AstrBot 框架传入的额外参数
        """
        try:
            # 立即阻止默认 LLM 请求
            # 注意：在 AstrBot 中，调用前会检查 'if not event.call_llm'
            # 所以设置 call_llm=True 实际上是阻止默认 LLM 被调用
            event.should_call_llm(True)

            # 获取群组 ID 用于频率限制
            group_id = event.get_group_id()
            if not group_id:
                # 私聊，使用发送者 ID
                group_id = event.get_sender_id()

            # 检查频率限制和复读冷却（原子操作）
            force_recommend = False
            echo_cooldown_active = False
            if self.rate_limiter:
                # 使用原子操作检查并记录，避免竞态条件
                _, force_recommend = self.rate_limiter.check_and_record(group_id)
                echo_cooldown_active = self.rate_limiter.is_in_echo_cooldown(group_id)

            # 决定是否推荐食物
            should_recommend = force_recommend or echo_cooldown_active or self.responder.should_recommend()
            
            if should_recommend:
                # 推荐食物（强制或按概率）
                if self.food_manager.has_foods():
                    food = self.food_manager.get_random_food()
                    response = self.responder.get_food_response(food)
                else:
                    response = self.responder.get_fallback_response()
            else:
                # 复读回复
                response = self.responder.get_echo_response()
                # 记录复读时间用于冷却追踪
                if self.rate_limiter:
                    self.rate_limiter.record_echo(group_id)

            # 发送响应并停止事件传播
            yield event.plain_result(response)
            event.stop_event()

        except Exception as e:
            logger.exception("吃什么插件发生错误")
            try:
                yield event.plain_result("哎呀，出错了...")
                event.stop_event()
            except Exception as inner_e:
                # 区分原始异常和发送失败异常
                logger.error(f"发送错误消息失败: {inner_e}")
                # 检测可能的系统性错误（事件系统故障等）
                error_msg = str(inner_e).lower()
                if any(kw in error_msg for kw in ["event", "yield", "generator", "async"]):
                    logger.critical(f"检测到事件系统错误: {inner_e}")

    async def terminate(self) -> None:
        """插件卸载时调用。"""
        logger.info("吃什么插件已终止")

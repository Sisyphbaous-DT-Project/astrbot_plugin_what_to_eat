"""吃什么推荐插件主文件。"""

from __future__ import annotations

import os
import re

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from .food_data import FoodDataManager


from .image_manager import ImageManager
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

        # Read trigger keywords configuration
        trigger_keywords = config.get("trigger_keywords", ["吃什么"])
        if not trigger_keywords or not isinstance(trigger_keywords, list):
            trigger_keywords = ["吃什么"]
        # Filter out empty strings
        self.trigger_keywords = [k for k in trigger_keywords if isinstance(k, str) and k.strip()]
        if not self.trigger_keywords:
            self.trigger_keywords = ["吃什么"]
        # Build regex pattern from keywords
        escaped_keywords = [re.escape(k) for k in self.trigger_keywords]
        self.keyword_pattern = re.compile("|".join(escaped_keywords))
        logger.info(f"关键词配置: {self.trigger_keywords}")

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

        # Initialize image manager
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_manager = ImageManager(config, plugin_dir)

        logger.info("吃什么插件初始化成功")

        logger.info("吃什么插件初始化成功")

        logger.info("吃什么插件初始化成功")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_what_to_eat(self, event: AstrMessageEvent, *args, **kwargs):
        """
        处理消息，检查是否包含配置的关键词。

        Args:
            event: 消息事件
            **kwargs: AstrBot 框架传入的额外参数
        """
        # 获取消息文本内容
        message_text = event.message_str
        if not message_text:
            return

        # 检查是否匹配关键词
        if not self.keyword_pattern.search(message_text):
            return

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
                    response_text = self.responder.get_food_response(food)

                    # 尝试获取食物图片
                    image_path = self.image_manager.get_random_image(food)

                    if image_path:
                        # 发送图文消息
                        yield event.make_result().message(response_text).file_image(image_path)
                    else:
                        # 无图片，只发送文字
                        yield event.plain_result(response_text)
                else:
                    response_text = self.responder.get_fallback_response()
                    yield event.plain_result(response_text)
            else:
                # 复读回复（不发送图片，保持简洁）
                response_text = self.responder.get_echo_response()
                yield event.plain_result(response_text)
                # 记录复读时间用于冷却追踪
                if self.rate_limiter:
                    self.rate_limiter.record_echo(group_id)

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

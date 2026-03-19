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
        if rate_limit_enabled:
            self.rate_limiter = RateLimiter(max_responses=rate_limit_max, window_seconds=60)
        else:
            self.rate_limiter = None

        # Initialize components
        self.food_manager = FoodDataManager(config)
        self.responder = Responder(probability)

        logger.info("WhatToEatPlugin initialized successfully")

    @filter.regex(r"吃什么")
    async def on_what_to_eat(self, event: AstrMessageEvent, *args, **kwargs):
        """
        Handle messages containing "吃什么".

        Args:
            event: The message event
            **kwargs: Additional arguments passed by AstrBot framework
        """
        try:
            # Block default LLM request immediately
            # Note: In AstrBot, the check is 'if not event.call_llm' before calling LLM.
            # So setting call_llm=True actually PREVENTS the default LLM from being called.
            event.should_call_llm(True)

            # Get group ID for rate limiting
            group_id = event.get_group_id()
            if not group_id:
                # Private chat, use sender ID
                group_id = event.get_sender_id()

            # Check rate limit
            force_recommend = False
            if self.rate_limiter:
                can_respond, force_recommend = self.rate_limiter.can_respond(group_id)
                if not can_respond:
                    event.stop_event()
                    return

            # Decide whether to recommend food
            if force_recommend:
                # Rate limit exceeded, always recommend food
                if self.food_manager.has_foods():
                    food = self.food_manager.get_random_food()
                    response = self.responder.get_food_response(food)
                else:
                    response = self.responder.get_fallback_response()
            elif self.responder.should_recommend():
                # Normal probability, recommend food
                if self.food_manager.has_foods():
                    food = self.food_manager.get_random_food()
                    response = self.responder.get_food_response(food)
                else:
                    response = self.responder.get_fallback_response()
            else:
                # Echo response
                response = self.responder.get_echo_response()

            # Record this response for rate limiting
            if self.rate_limiter:
                self.rate_limiter.record_response(group_id)

            # Send response and stop event propagation
            yield event.plain_result(response)
            event.stop_event()

        except Exception:
            logger.exception("WhatToEatPlugin error occurred")
            yield event.plain_result("哎呀，出错了...")
            event.stop_event()

    async def terminate(self) -> None:
        """Called when plugin is unloaded."""
        logger.info("WhatToEatPlugin terminated")

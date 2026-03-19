"""吃什么推荐插件主文件。"""

from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

from .food_data import FoodDataManager
from .responder import Responder


class WhatToEatPlugin(Star):
    """
    吃什么推荐插件。

    识别消息中的"吃什么"关键词，根据配置概率：
    - 推荐大学生常吃的美食
    - 或复读"是啊，吃什么"
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

        # Initialize components
        self.food_manager = FoodDataManager(config)
        self.responder = Responder(probability)

        logger.info("WhatToEatPlugin initialized successfully")

    @filter.regex(r"吃什么")
    async def on_what_to_eat(self, event: AstrMessageEvent):
        """
        Handle messages containing "吃什么".

        Decide whether to recommend food or echo based on probability.
        Also blocks default LLM request to avoid duplicate responses.
        """
        try:
            # Block default LLM request immediately
            # Note: should_call_llm(True) actually BLOCKS LLM
            # because the check in AstrBot is 'not event.call_llm'
            event.should_call_llm(True)

            # Decide whether to recommend food
            if self.responder.should_recommend():
                # Recommend food
                if self.food_manager.has_foods():
                    food = self.food_manager.get_random_food()
                    response = self.responder.get_food_response(food)
                else:
                    # No foods available, fallback
                    response = self.responder.get_fallback_response()
            else:
                # Echo response
                response = self.responder.get_echo_response()

            # Send response and stop event propagation
            yield event.plain_result(response)
            event.stop_event()

        except Exception:
            # Log exception with traceback for better observability
            logger.exception("WhatToEatPlugin error occurred")
            yield event.plain_result("哎呀，出错了...")
            # Also stop event on error to prevent duplicate responses
            event.stop_event()

    async def terminate(self) -> None:
        """Called when plugin is unloaded."""
        logger.info("WhatToEatPlugin terminated")

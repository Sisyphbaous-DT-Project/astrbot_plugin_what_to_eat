"""回复逻辑模块。"""

from __future__ import annotations

import random
from typing import Any

from astrbot.api import logger


class Responder:
    """Handle message response logic."""

    # Fixed echo response (复读回复固定内容)
    ECHO_RESPONSE = "是啊，吃什么"

    # Food recommendation templates
    RECOMMEND_TEMPLATES = [
        "要不吃{food}？",
        "试试{food}吧！",
        "{food}怎么样？",
        "推荐你吃{food}~",
        "今天吃{food}吧！",
        "{food}了解一下？",
    ]

    def __init__(self, probability: Any = 0.3) -> None:
        """
        Initialize the responder.

        Args:
            probability: Probability of recommending food (0.0-1.0)
                         Can be float, int, or string representation
        """
        # Type-safe conversion
        probability = self._safe_float(probability, 0.3)
        self.probability = max(0.0, min(1.0, probability))
        logger.info(f"Responder initialized with probability={self.probability}")

    def _safe_float(self, value: Any, default: float) -> float:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value
        """
        if value is None:
            return default
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                logger.warning(f"Could not convert '{value}' to float, using default {default}")
                return default
        
        logger.warning(f"Unexpected type {type(value).__name__} for probability, using default {default}")
        return default

    def should_recommend(self) -> bool:
        """
        Decide whether to recommend food based on probability.

        Returns:
            True to recommend food, False to echo
        """
        return random.random() < self.probability

    def get_echo_response(self) -> str:
        """
        Get an echo response.

        Returns:
            Fixed echo message: "是啊，吃什么"
        """
        return self.ECHO_RESPONSE

    def get_food_response(self, food: str) -> str:
        """
        Generate a food recommendation response.

        Args:
            food: Food name

        Returns:
            Recommendation message
        """
        template = random.choice(self.RECOMMEND_TEMPLATES)
        return template.format(food=food)

    def get_fallback_response(self) -> str:
        """
        Get fallback response when no foods available.

        Returns:
            Fallback message
        """
        return "我想不到推荐什么...你自己决定吧！"

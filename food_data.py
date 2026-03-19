"""食物数据管理模块。"""

from __future__ import annotations

import random

from astrbot.api import logger


class FoodDataManager:
    """管理食物数据，包括内置列表和用户自定义列表。"""

    def __init__(self, config: dict) -> None:
        """
        Initialize the food data manager.

        Args:
            config: Plugin configuration dictionary
        """
        self.config = config
        # Read builtin foods from config (now editable in WebUI)
        self.builtin_foods = config.get("builtin_foods", [])
        self.custom_foods = config.get("custom_foods", [])
        logger.info(
            f"FoodDataManager initialized: builtin={len(self.builtin_foods)}, "
            f"custom={len(self.custom_foods)}"
        )

    def get_all_foods(self) -> list[str]:
        """
        Get all available food items.

        Returns:
            Merged list of built-in and custom foods
        """
        foods = []
        foods.extend(self.builtin_foods)
        foods.extend(self.custom_foods)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_foods: list[str] = []
        for food in foods:
            stripped_food = food.strip() if isinstance(food, str) else ""
            if stripped_food and stripped_food not in seen:
                seen.add(stripped_food)
                unique_foods.append(stripped_food)

        return unique_foods

    def get_random_food(self) -> str | None:
        """
        Get a random food item.

        Returns:
            Food name, or None if no foods available
        """
        foods = self.get_all_foods()
        if not foods:
            return None
        return random.choice(foods)

    def has_foods(self) -> bool:
        """Check if any foods are available."""
        return len(self.get_all_foods()) > 0

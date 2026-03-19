"""食物数据管理模块。"""

from __future__ import annotations

import random
from typing import Any

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
        
        # Validate and sanitize builtin_foods
        builtin_foods_raw = config.get("builtin_foods", [])
        self.builtin_foods = self._sanitize_food_list(builtin_foods_raw, "builtin_foods")
        
        # Validate and sanitize custom_foods
        custom_foods_raw = config.get("custom_foods", [])
        self.custom_foods = self._sanitize_food_list(custom_foods_raw, "custom_foods")
        
        # Cache the merged list
        self._cached_foods: list[str] | None = None
        
        logger.info(
            f"FoodDataManager initialized: builtin={len(self.builtin_foods)}, "
            f"custom={len(self.custom_foods)}"
        )

    def _sanitize_food_list(self, raw_value: Any, field_name: str) -> list[str]:
        """
        Sanitize food list from config.
        
        Args:
            raw_value: Raw config value
            field_name: Field name for logging
            
        Returns:
            Sanitized list of strings
        """
        if raw_value is None:
            return []
        
        if isinstance(raw_value, str):
            # Handle case where config might be a string instead of list
            logger.warning(f"{field_name} is a string, converting to list")
            return [raw_value] if raw_value.strip() else []
        
        if not isinstance(raw_value, list):
            logger.warning(f"{field_name} has unexpected type {type(raw_value).__name__}, using empty list")
            return []
        
        # Filter out non-string items and empty strings
        result = []
        for item in raw_value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            else:
                logger.debug(f"Skipping invalid item in {field_name}: {item}")
        
        return result

    def get_all_foods(self) -> list[str]:
        """
        Get all available food items.

        Returns:
            Merged list of built-in and custom foods
        """
        # Return cached list if available
        if self._cached_foods is not None:
            return self._cached_foods
        
        foods = []
        foods.extend(self.builtin_foods)
        foods.extend(self.custom_foods)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_foods: list[str] = []
        for food in foods:
            if food not in seen:
                seen.add(food)
                unique_foods.append(food)
        
        # Cache the result
        self._cached_foods = unique_foods
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
        # Use cached list to avoid recomputation
        return len(self.get_all_foods()) > 0

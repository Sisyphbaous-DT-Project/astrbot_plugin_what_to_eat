"""食物数据管理模块。"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

if TYPE_CHECKING:
    from astrbot.api import AstrBotConfig


class FoodDataManager:
    """管理食物数据，包括内置列表和用户自定义列表。"""

    def __init__(self, config: AstrBotConfig) -> None:
        """
        初始化食物数据管理器。

        Args:
            config: 插件配置 (AstrBotConfig)
        """
        self.config = config
        
        # 验证并清理内置食物列表
        builtin_foods_raw = config.get("builtin_foods", [])
        self.builtin_foods = self._sanitize_food_list(builtin_foods_raw, "builtin_foods")
        
        # 验证并清理自定义食物列表
        custom_foods_raw = config.get("custom_foods", [])
        self.custom_foods = self._sanitize_food_list(custom_foods_raw, "custom_foods")
        
        # 缓存合并后的列表
        self._cached_foods: list[str] | None = None
        
        logger.info(
            f"食物数据管理器初始化完成: builtin={len(self.builtin_foods)}, "
            f"custom={len(self.custom_foods)}"
        )

    def _sanitize_food_list(self, raw_value: Any, field_name: str) -> list[str]:
        """
        清理配置文件中的食物列表。
        
        Args:
            raw_value: 原始配置值
            field_name: 用于日志记录的字段名
            
        Returns:
            清理后的字符串列表
        """
        if raw_value is None:
            return []
        
        if isinstance(raw_value, str):
            # 处理配置可能是字符串而非列表的情况
            logger.warning(f"{field_name} 是字符串，正在转换为列表")
            return [raw_value] if raw_value.strip() else []
        
        if not isinstance(raw_value, list):
            logger.warning(f"{field_name} 类型异常 {type(raw_value).__name__}，使用空列表")
            return []
        
        # 过滤掉非字符串项和空字符串
        result = []
        for item in raw_value:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            else:
                logger.warning(f"跳过 {field_name} 中的无效项: {item!r}")
        
        return result

    def clear_cache(self) -> None:
        """清除缓存的食物列表。配置热重载时调用。"""
        self._cached_foods = None
        logger.debug("食物缓存已清除")

    def get_all_foods(self) -> list[str]:
        """
        获取所有可用的食物项。

        Returns:
            内置和自定义食物合并后的列表
        """
        # 如果缓存可用，直接返回
        if self._cached_foods is not None:
            return self._cached_foods
        
        # 使用 dict.fromkeys() 去重同时保持顺序（Python 3.7+）
        # 比手动 set + list 方式更简洁
        all_foods = self.builtin_foods + self.custom_foods
        self._cached_foods = list(dict.fromkeys(all_foods))
        
        return self._cached_foods

    def get_random_food(self) -> str | None:
        """
        获取随机食物项。

        Returns:
            食物名称，如果没有可用食物则返回 None
        """
        foods = self.get_all_foods()
        if not foods:
            return None
        return random.choice(foods)

    def has_foods(self) -> bool:
        """检查是否有可用的食物。"""
        # 使用缓存列表避免重复计算
        return len(self.get_all_foods()) > 0

"""图片管理模块。"""

from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

if TYPE_CHECKING:
    from astrbot.api import AstrBotConfig


class ImageManager:
    """管理食物图片，支持多图片随机选择。"""

    def __init__(self, config: AstrBotConfig, plugin_dir: str) -> None:
        """
        初始化图片管理器。

        Args:
            config: 插件配置
            plugin_dir: 插件根目录路径
        """
        self.config = config
        self.plugin_dir = plugin_dir

        # 读取食物图片配置
        raw_food_images = config.get("food_images", {})
        self.food_images = self._sanitize_food_images(raw_food_images)

        logger.info(f"图片管理器初始化完成: {len(self.food_images)} 个食物有图片配置")

    def _sanitize_food_images(self, raw_value: Any) -> dict[str, list[str]]:
        """
        清理食物图片配置。

        Args:
            raw_value: 原始配置值

        Returns:
            清理后的食物名到图片路径列表的映射
        """
        if not raw_value or not isinstance(raw_value, dict):
            return {}

        result = {}
        for food_name, image_paths in raw_value.items():
            if not isinstance(food_name, str) or not food_name.strip():
                logger.warning(f"跳过无效的食物名: {food_name!r}")
                continue

            # 规范化食物名（去除首尾空格）
            food_name = food_name.strip()

            # 处理图片路径
            if isinstance(image_paths, str):
                # 单个图片路径转为列表
                image_paths = [image_paths]
            elif not isinstance(image_paths, list):
                logger.warning(f"食物 '{food_name}' 的图片配置格式无效，跳过")
                continue

            # 过滤有效路径
            valid_paths = []
            for path in image_paths:
                if isinstance(path, str) and path.strip():
                    valid_paths.append(path.strip())

            if valid_paths:
                result[food_name] = valid_paths

        return result

    def _get_full_path(self, relative_path: str) -> str:
        """
        将相对路径转换为绝对路径。

        Args:
            relative_path: 相对于插件目录的路径

        Returns:
            绝对路径
        """
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(relative_path):
            return relative_path

        # 相对于插件目录
        return os.path.join(self.plugin_dir, relative_path)

    def has_images(self, food_name: str) -> bool:
        """
        检查食物是否有图片配置。

        Args:
            food_name: 食物名称

        Returns:
            是否有图片配置（不检查文件是否存在）
        """
        if not food_name:
            return False

        # 精确匹配
        if food_name in self.food_images:
            return len(self.food_images[food_name]) > 0

        # 尝试去除首尾空格后的匹配
        food_name_stripped = food_name.strip()
        if food_name_stripped in self.food_images:
            return len(self.food_images[food_name_stripped]) > 0

        return False

    def get_random_image(self, food_name: str) -> str | None:
        """
        获取食物的随机图片路径。

        Args:
            food_name: 食物名称

        Returns:
            图片的绝对路径，如果没有配置或文件不存在则返回 None
        """
        if not food_name:
            return None

        # 获取图片路径列表
        image_paths = self.food_images.get(food_name)

        # 尝试去除首尾空格后的匹配
        if image_paths is None:
            food_name_stripped = food_name.strip()
            image_paths = self.food_images.get(food_name_stripped)

        if not image_paths:
            return None

        # 随机选择一张图片，并检查文件是否存在
        # 为了避免重复检查不存在的文件，先过滤出存在的图片
        existing_paths = []
        for path in image_paths:
            full_path = self._get_full_path(path)
            if os.path.isfile(full_path):
                existing_paths.append(full_path)

        if not existing_paths:
            logger.debug(f"食物 '{food_name}' 的图片配置存在但文件不存在")
            return None

        return random.choice(existing_paths)

    def get_all_foods_with_images(self) -> list[str]:
        """
        获取所有有图片配置的食物名称列表。

        Returns:
            食物名称列表
        """
        return list(self.food_images.keys())

    def reload_config(self, config: AstrBotConfig) -> None:
        """
        重新加载配置（用于配置热重载）。

        Args:
            config: 新的插件配置
        """
        raw_food_images = config.get("food_images", {})
        self.food_images = self._sanitize_food_images(raw_food_images)
        logger.info(f"图片配置已重载: {len(self.food_images)} 个食物有图片")

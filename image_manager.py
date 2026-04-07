"""图片管理模块。"""

from __future__ import annotations

import os
import random
import re
from typing import TYPE_CHECKING

from astrbot.api import logger

if TYPE_CHECKING:
    from astrbot.api import AstrBotConfig


class ImageManager:
    """管理食物图片，支持从文件夹自动扫描和配置两种方式。"""

    def __init__(self, config: AstrBotConfig, plugin_dir: str) -> None:
        """
        初始化图片管理器。

        Args:
            config: 插件配置
            plugin_dir: 插件根目录路径
        """
        self.config = config
        self.plugin_dir = plugin_dir
        self.images_dir = os.path.join(plugin_dir, "images")

        # 从文件夹扫描图片
        self.scanned_images = self._scan_images_folder()

        logger.info(f"图片管理器初始化完成: {len(self.scanned_images)} 个食物有图片")

    def _scan_images_folder(self) -> dict[str, list[str]]:
        """
        扫描 images 文件夹，根据文件名匹配食物。

        文件名格式：
        - 黄焖鸡米饭.jpg
        - 黄焖鸡米饭_1.jpg
        - 黄焖鸡米饭-1.jpg

        Returns:
            食物名到图片路径列表的映射
        """
        result: dict[str, list[str]] = {}

        if not os.path.isdir(self.images_dir):
            logger.debug(f"图片目录不存在: {self.images_dir}")
            return result

        # 支持的图片格式
        image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

        try:
            for filename in os.listdir(self.images_dir):
                filepath = os.path.join(self.images_dir, filename)

                # 跳过目录
                if not os.path.isfile(filepath):
                    continue

                # 检查扩展名
                ext = os.path.splitext(filename)[1].lower()
                if ext not in image_extensions:
                    continue

                # 从文件名提取食物名
                # 支持格式：食物名.jpg、食物名_1.jpg、食物名-1.jpg
                food_name = self._extract_food_name(filename)

                if food_name:
                    if food_name not in result:
                        result[food_name] = []
                    result[food_name].append(filepath)

        except OSError as e:
            logger.warning(f"扫描图片目录失败: {e}")

        # 对每个食物的图片列表排序，保持顺序一致
        for food_name in result:
            result[food_name].sort()

        return result

    def _extract_food_name(self, filename: str) -> str | None:
        """
        从文件名提取食物名称。

        Args:
            filename: 文件名（不含路径）

        Returns:
            食物名称，如果无法提取则返回 None
        """
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]

        # 移除序号后缀（_1、_2、-1、-2 等）
        # 匹配末尾的 _数字 或 -数字
        cleaned_name = re.sub(r"[_-]\d+$", "", name_without_ext)

        if cleaned_name.strip():
            return cleaned_name.strip()

        return None

    def has_images(self, food_name: str) -> bool:
        """
        检查食物是否有图片。

        Args:
            food_name: 食物名称

        Returns:
            是否有图片（扫描到的或配置的）
        """
        if not food_name:
            return False

        food_name_stripped = food_name.strip()

        # 检查扫描到的图片
        if food_name_stripped in self.scanned_images:
            return len(self.scanned_images[food_name_stripped]) > 0

        return False

    def get_random_image(self, food_name: str) -> str | None:
        """
        获取食物的随机图片路径。

        Args:
            food_name: 食物名称

        Returns:
            图片的绝对路径，如果没有则返回 None
        """
        if not food_name:
            return None

        food_name_stripped = food_name.strip()

        # 优先使用扫描到的图片
        image_paths = self.scanned_images.get(food_name_stripped)

        if image_paths:
            # 过滤掉不存在的文件（可能被删除了）
            existing_paths = [p for p in image_paths if os.path.isfile(p)]
            if existing_paths:
                return random.choice(existing_paths)

        return None

    def get_all_foods_with_images(self) -> list[str]:
        """
        获取所有有图片配置的食物名称列表。

        Returns:
            食物名称列表
        """
        return list(self.scanned_images.keys())

    def reload(self) -> None:
        """重新扫描图片文件夹（用于热重载）。"""
        self.scanned_images = self._scan_images_folder()
        logger.info(f"图片配置已重载: {len(self.scanned_images)} 个食物有图片")

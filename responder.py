"""回复逻辑模块。"""

from __future__ import annotations

import random

from astrbot.api import logger


class Responder:
    """处理消息回复逻辑。"""

    # 复读回复固定内容
    ECHO_RESPONSE = "是啊，吃什么"

    # 食物推荐模板
    RECOMMEND_TEMPLATES = [
        "要不吃{food}？",
        "试试{food}吧！",
        "{food}怎么样？",
        "推荐你吃{food}！",
        "今天吃{food}吧！",
        "{food}了解一下？",
    ]

    def __init__(self, probability: float = 0.3) -> None:
        """
        初始化回复器。

        Args:
            probability: 推荐食物的概率 (0.0-1.0)
                        默认为 0.3（30% 推荐，70% 复读）
        """
        self.probability = max(0.0, min(1.0, float(probability)))
        logger.info(f"回复器初始化完成: probability={self.probability}")

    def should_recommend(self) -> bool:
        """
        根据概率决定是否推荐食物。

        Returns:
            推荐食物返回 True，复读返回 False
        
        说明:
            - probability=0.0: 从不推荐（始终复读）
            - probability=1.0: 总是推荐（从不复读）
        """
        return random.random() < self.probability

    def get_echo_response(self) -> str:
        """
        获取复读回复。

        Returns:
            固定复读消息: "是啊，吃什么"
        """
        return self.ECHO_RESPONSE

    def get_food_response(self, food: str | None) -> str:
        """
        生成食物推荐回复。

        Args:
            food: 食物名称，如果没有可用食物则为 None

        Returns:
            推荐消息，如果 food 为 None 则返回兜底消息
        """
        if food is None:
            return self.get_fallback_response()
        template = random.choice(self.RECOMMEND_TEMPLATES)
        return template.format(food=food)

    def get_fallback_response(self) -> str:
        """
        获取兜底回复（当没有可用食物时）。

        Returns:
            兜底消息
        """
        return "我想不到推荐什么...你自己决定吧！"

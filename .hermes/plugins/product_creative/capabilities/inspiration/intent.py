from ..intent_helpers import contains_any, phrases
from ..models import IntentRule


def _confirm_library(message: str) -> bool:
    positive = ("确认沉淀灵感", "沉淀到灵感库", "写入灵感库", "加入灵感库", "保存灵感库")
    negative = ("不要沉淀", "不沉淀", "不要写入灵感库", "不写入灵感库", "先不要沉淀", "暂不沉淀")
    return contains_any(message, positive) and not contains_any(message, negative)


INTENT_RULES = (
    IntentRule("confirm_inspiration_library_entry", 250, _confirm_library),
    phrases("create_llm_inspiration_pack", 260, "llm深度总结", "llm 灵感", "深度总结灵感", "深度灵感总结", "模型总结灵感", "用deepseek总结灵感", "deepseek总结灵感"),
    phrases("create_inspiration_candidates", 270, "灵感候选", "提炼灵感", "挖掘灵感", "分析灵感"),
    phrases("create_inspiration_pack", 280, "灵感包", "整理灵感", "打包灵感"),
    phrases("collect_external_source_snapshot", 290, "外部素材", "外部灵感", "抓取灵感", "抓取小红书", "抓取抖音", "搜索小红书", "搜索抖音", "爆款文案", "热点", "热门话题", "热门题材", "竞品灵感"),
)

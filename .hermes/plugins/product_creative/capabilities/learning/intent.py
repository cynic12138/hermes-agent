from ..intent_helpers import contains_any, phrases
from ..models import IntentRule


def _apply_proposal(message: str) -> bool:
    return contains_any(message, ("确认", "同意", "应用", "apply", "confirm", "yes")) and contains_any(message, ("proposal", "提案", "应用"))


INTENT_RULES = (
    IntentRule("apply_evolution_proposal", 10, _apply_proposal),
    phrases("create_evolution_proposal", 40, "生成提案", "学习提案", "创建提案"),
    phrases("record_image_result_feedback", 380, "反馈图片", "评价图片", "选择图片", "选中图片", "这张图不错", "这张图片"),
    phrases("record_channel_feedback", 440, "喜欢", "选择", "选第", "反馈", "不喜欢", "广告感"),
)

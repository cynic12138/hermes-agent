from ..intent_helpers import contains_any, phrases
from ..models import IntentRule


def _video_result_feedback(message: str) -> bool:
    direct = ("反馈视频结果", "评价视频结果", "这个视频满意", "这个视频不错", "选择这个视频")
    return contains_any(message, direct) or (
        contains_any(message, ("通过", "不通过"))
        and contains_any(message, ("视频", "主图", "剧情", "动效", "故事"))
    )


INTENT_RULES = (
    phrases("review_video_brief", 100, "审阅视频brief", "视频brief审阅", "审阅视频方案", "视频方案审阅"),
    phrases("revise_video_brief", 110, "确认视频brief", "确认视频方案", "修改视频brief", "修订视频brief", "调整视频方案", "确认分镜", "修改分镜"),
    phrases("build_video_provider_payload", 120, "视频payload", "视频provider", "视频生成请求", "构建视频请求", "准备视频生成"),
    phrases("check_video_reference_readiness", 130, "视频引用检查", "视频参考图检查", "检查视频参考图", "检查视频url", "视频url检查"),
    phrases("check_video_live_readiness", 140, "检查视频live", "检查视频可生成", "视频可生成检查", "视频就绪检查", "视频readiness"),
    phrases("create_video_execution_policy", 150, "确认视频执行策略", "视频执行策略", "允许真实生成视频", "批准视频生成", "批准视频调用"),
    phrases("submit_video_generation_task", 160, "提交视频任务", "调用视频模型", "真实生成视频", "开始生成视频"),
    phrases("check_video_task_status", 170, "查询视频任务", "检查视频任务", "视频任务状态", "查询生成状态"),
    phrases("import_video_result", 180, "导入视频结果", "导入生成视频", "视频结果url", "视频链接导入"),
    IntentRule("record_video_result_feedback", 190, _video_result_feedback),
    phrases("compose_exact_main_video", 200, "固定主图", "主图固定", "主图不能变", "主图不变", "不改主图", "主图完整", "不重绘主图", "动漫故事推广", "卡通动漫故事"),
    phrases("record_video_brief_feedback", 210, "反馈视频brief", "视频brief反馈", "反馈视频方案", "评价视频brief", "评价分镜", "反馈分镜", "记住这个分镜", "这个分镜"),
    phrases("create_video_brief", 410, "生成视频brief", "创建视频brief", "视频brief", "视频方案", "视频分镜说明书"),
    phrases("resolve_video_intent", 420, "图生视频", "以这张图", "用这张图", "以这张主图", "用这张主图", "用这个主图", "主图做视频", "已有素材", "素材库", "本地素材", "根据素材", "今日视频", "今天视频"),
)

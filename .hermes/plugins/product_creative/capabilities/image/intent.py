from ..intent_helpers import phrases

INTENT_RULES = (
    phrases("review_image_brief", 300, "审阅图片brief", "图片brief审阅", "审阅图片方案", "图片方案审阅", "审阅主图方案"),
    phrases("revise_image_brief", 310, "确认图片brief", "确认图片方案", "修改图片brief", "修订图片brief", "调整图片方案", "确认主图方案"),
    phrases("create_batch_generation_policy", 320, "批量生图", "批量生成图片", "批量主图", "批量图片策略", "生成策略", "batch policy"),
    phrases("build_image_provider_payload", 330, "图片payload", "图片provider", "图片生成请求", "构建图片请求", "准备图片生成"),
    phrases("check_image_live_readiness", 340, "检查图片live", "检查图片可生成", "图片就绪检查", "图片readiness"),
    phrases("submit_image_generation_job", 345, "调用图片模型", "真实生成图片", "开始生图", "提交图片生成", "生成候选图"),
    phrases("resolve_image_intent", 400, "生成图片", "生成主图", "生图", "产品图", "封面图", "电商主图", "小红书封面"),
)

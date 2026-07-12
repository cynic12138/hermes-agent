from ..intent_helpers import phrases

INTENT_RULES = (
    phrases("review_generated_result", 350, "审阅生成结果", "结果审阅", "审阅真实结果", "审阅图片结果", "审阅视频结果", "看看生成结果"),
    phrases("evaluate_generated_result", 360, "评估生成结果", "结果评估", "从结果学习", "总结结果学习", "沉淀结果经验", "根据结果生成学习建议"),
    phrases("create_task_overview_package", 370, "任务总览", "完整审阅包", "总览包", "本次链路", "中间产物总览"),
)

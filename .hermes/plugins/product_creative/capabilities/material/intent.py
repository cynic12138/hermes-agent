from ..intent_helpers import phrases

INTENT_RULES = (
    phrases("register_material_asset", 50, "注册主图", "上传主图", "添加主图", "登记主图", "注册素材", "上传素材", "添加素材", "登记素材", "登记这张", "这张主图素材", "作为当前主图"),
    phrases("analyze_material_image", 60, "分析主图", "理解主图", "识别主图", "分析素材", "理解素材", "识别素材", "图片理解", "视觉理解"),
    phrases("align_visual_analysis", 70, "对齐主图", "确认主图理解", "主图对齐", "视觉对齐", "确认视觉参考", "作为视觉参考"),
    phrases("rebuild_material_cards", 80, "素材卡片", "重建卡片", "刷新卡片", "material card"),
    phrases("prepare_task_material_pack", 90, "素材包", "任务素材包", "准备素材", "选择素材", "material pack"),
    phrases("record_material_feedback", 230, "素材反馈", "这张素材", "这个素材", "素材选择"),
    phrases("resolve_material_execution_input", 240, "素材执行输入", "素材解析", "provider输入", "模型输入", "materialresolver", "material resolver"),
    phrases("register_selected_image_asset", 390, "登记生成图", "保存生成图", "生成图入库", "加入素材库", "作为候选素材"),
)

from ..intent_helpers import phrases

INTENT_RULES = (
    phrases("create_product", 20, "创建产品", "新建产品", "初始化产品"),
    phrases("ingest_product_source", 30, "输入资料", "补充资料", "导入资料", "录入资料"),
)

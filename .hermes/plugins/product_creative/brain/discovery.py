"""Task-scoped Product Brain readiness without canonical writeback."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, Iterable, List

from ..common import ensure_product, now_iso, slug, timestamp, write_json
from ..contracts.models import (
    CreativeTaskRequest,
    DiscoveryQuestion,
    ProductKnowledgeField,
    ProductReadinessReport,
)
from ..ports.runtime_repositories import artifact_documents, materials, product_brains, proposals


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _first_text(values: Iterable[Any]) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _material_for_current_packaging(product_id: str) -> Dict[str, Any]:
    active = [item for item in materials().list(product_id) if item.get("status", "active") == "active"]
    for role in ("current_main_image", "video_first_frame", "product_photo"):
        for item in reversed(active):
            if item.get("role") == role:
                return item
    return {}


def _claim_boundaries(state: Dict[str, Any]) -> Dict[str, Any]:
    compliance = state.get("compliance") if isinstance(state.get("compliance"), dict) else {}
    allowed = _list(compliance.get("allowed_claims")) or _list(state.get("allowed_claims"))
    forbidden = _list(compliance.get("forbidden_claims")) or _list(state.get("forbidden_claims"))
    return {"allowed": allowed, "forbidden": forbidden} if allowed or forbidden else {}


def _question(field: ProductKnowledgeField, priority: int, prompt: str) -> DiscoveryQuestion:
    return DiscoveryQuestion(
        question_id=f"question-{field.key}",
        field_key=field.key,
        prompt=prompt,
        priority=priority,
        blocking=field.blocking,
    )


def assess_product_readiness(
    product_id: str,
    request: CreativeTaskRequest,
    *,
    task_id: str = "",
) -> ProductReadinessReport:
    """Derive and persist task readiness without changing Canonical Product Brain."""

    base = ensure_product(product_id)
    current_brain = product_brains().current(base.name)
    state = current_brain.get("state") if isinstance(current_brain.get("state"), dict) else {}
    material = _material_for_current_packaging(base.name)
    basic = state.get("basic") if isinstance(state.get("basic"), dict) else {}
    product_name = _first_text((state.get("name"), basic.get("name")))
    sku = _first_text((basic.get("sku"), basic.get("sku_name"), basic.get("specification"), state.get("sku")))
    claims = _claim_boundaries(state)
    needs_product_visual = any(item in request.deliverables for item in ("image", "video"))
    understanding_only = request.goal_kind == "understanding"

    fields = [
        ProductKnowledgeField(
            key="product_identity",
            label="产品身份",
            status="CONFIRMED" if product_name else "UNKNOWN",
            value=product_name or None,
            blocking=not bool(product_name),
            impact="无法确定本次任务对应的产品。",
        ),
        ProductKnowledgeField(
            key="claim_boundaries",
            label="可用与禁用表述",
            status="CONFIRMED" if claims else "UNKNOWN",
            value=claims or None,
            blocking=True,
            impact="无法判断生成内容是否包含未经确认的产品表述。",
        ),
        ProductKnowledgeField(
            key="product_sku",
            label="产品 SKU/规格",
            status="CONFIRMED" if sku else "UNKNOWN",
            value=sku or None,
            blocking=True,
            impact="无法确认生成内容对应的具体商品版本。",
        ),
        ProductKnowledgeField(
            key="current_packaging",
            label="当前包装/商品主体素材",
            status="CONFIRMED" if material else "UNKNOWN",
            value=material.get("material_id") if material else None,
            source_ids=[str(material.get("source_id"))] if material.get("source_id") else [],
            blocking=needs_product_visual and not bool(material),
            impact="缺少当前包装素材，不能承诺商品主体和包装保真。",
        ),
        ProductKnowledgeField(
            key="delivery_spec",
            label="交付类型",
            status="CONFIRMED" if request.deliverables or understanding_only else "UNKNOWN",
            value=list(request.deliverables) or (["understanding"] if understanding_only else None),
            blocking=not bool(request.deliverables) and not understanding_only,
            impact="无法判断用户需要文案、图片、视频或组合交付。",
        ),
    ]

    prompts = {
        "claim_boundaries": "本次内容允许使用哪些产品卖点或表述，又有哪些表述必须禁止？",
        "product_sku": "这次任务对应哪个具体 SKU、规格或包装版本？",
        "current_packaging": "请提供或确认当前包装/商品主图；哪张素材是本次商品主体？",
        "product_identity": "请确认这次要创作的具体产品名称。",
        "delivery_spec": "本次最终需要文案、图片、视频，还是组合交付？",
    }
    priority = {
        "claim_boundaries": 0,
        "product_identity": 1,
        "product_sku": 2,
        "current_packaging": 3,
        "delivery_spec": 4,
    }
    unresolved = [field for field in fields if field.blocking and field.status in {"UNKNOWN", "CONFLICTED"}]
    unresolved.sort(key=lambda field: (priority[field.key], field.key))
    questions = [_question(field, priority[field.key], prompts[field.key]) for field in unresolved[:3]]
    blockers = [field.impact for field in unresolved]
    clean_task_id = slug(task_id or f"task-{timestamp()}")
    readiness_id = f"readiness-{clean_task_id}"
    path = base / "artifacts" / "product_readiness" / f"{readiness_id}.json"
    report = ProductReadinessReport(
        readiness_id=readiness_id,
        task_id=clean_task_id,
        product_id=base.name,
        created_at=now_iso(),
        deliverables=list(request.deliverables),
        ready=not unresolved,
        fields=fields,
        blockers=blockers,
        questions=questions,
        artifact_path=str(path),
    )
    write_json(path, report.model_dump(mode="json"))
    return report


def _claim_lists(message: str) -> tuple[List[str], List[str]]:
    allowed_match = re.search(r"允许(?:使用)?(.+?)(?=，|,|；|;|。|禁止|$)", message)
    forbidden_match = re.search(r"禁止(.+)$", message)

    def split(value: str) -> List[str]:
        result: List[str] = []
        for raw in re.split(r"(?:、|，|,|；|;)", value):
            item = raw.strip(" 。；;，,")
            if not item:
                continue
            # A conjunction can be part of one claim (for example
            # ``温和不刺激``). Split only when both sides are independently
            # shaped compliance terms such as ``医疗功效和治疗表述``.
            paired = re.fullmatch(
                r"(.+(?:功效|效果|承诺|适用))和(.+(?:表述|功效|效果|承诺|适用))",
                item,
            )
            if paired:
                result.extend([paired.group(1).strip(), paired.group(2).strip()])
            else:
                result.append(item)
        return result

    return (
        split(allowed_match.group(1)) if allowed_match else [],
        split(forbidden_match.group(1)) if forbidden_match else [],
    )


def create_field_confirmation_proposal(
    product_id: str,
    task_id: str,
    field_key: str,
    message: str,
) -> Dict[str, Any]:
    """Store a user answer as evidence and a reviewable field proposal."""

    base = ensure_product(product_id)
    evidence_id = f"evidence-{uuid.uuid4().hex}"
    evidence_path = artifact_documents(base).save(
        "evidence_inbox",
        evidence_id,
        {
            "schema_version": "product_creative.evidence.v1",
            "evidence_id": evidence_id,
            "product_id": base.name,
            "task_id": task_id,
            "kind": "user_message",
            "content": message,
            "created_at": now_iso(),
            "status": "EVIDENCE_ONLY",
        },
    )
    updates: List[Dict[str, Any]] = []
    if field_key == "claim_boundaries":
        allowed, forbidden = _claim_lists(message)
        if allowed:
            updates.append({"path": "compliance.allowed_claims", "value": allowed})
        if forbidden:
            updates.append({"path": "compliance.forbidden_claims", "value": forbidden})
    elif field_key == "product_sku":
        updates.append({"path": "basic.sku", "value": message.strip()})
    elif field_key == "product_identity":
        updates.append({"path": "name", "value": message.strip()})
    if not updates:
        raise ValueError(f"field '{field_key}' needs structured evidence before it can be confirmed")
    proposal_id = f"proposal-{timestamp()}-{uuid.uuid4().hex[:6]}"
    for update in updates:
        update.update(
            {
                "update_type": "discovery_field_confirmation",
                "source_ids": [evidence_id],
                "target_page": "product/Product.md",
            }
        )
    proposal = {
        "proposal_id": proposal_id,
        "product_id": base.name,
        "task_id": task_id,
        "field_key": field_key,
        "status": "proposed",
        "risk_level": "high",
        "requires_human_review": True,
        "source_ids": [evidence_id],
        "evidence_path": evidence_path,
        "updates": updates,
        "created_at": now_iso(),
    }
    proposal["storage_uri"] = proposals().save(proposal)
    proposal_path = base / "structured" / "evolution_proposals" / f"{proposal_id}.json"
    write_json(proposal_path, proposal)
    return proposal

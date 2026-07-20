"""External inspiration collection service."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from ...common import append_jsonl, ensure_product, now_iso, product_state_path, read_json, read_product_state, timestamp, update_index_and_log, write_json

from .shared import _list, _rel, _safe_limit, _sanitize_string, _text

EXTERNAL_SOURCE_SNAPSHOT_SCHEMA_VERSION = "product_creative.external_source_snapshot.v6.3"

DEFAULT_XHS_SIDECAR = "http://127.0.0.1:8787/api"

DEFAULT_DOUYIN_SIDECAR = "http://127.0.0.1:8000"
DOUYIN_FIRST5_TIMEOUT_SECONDS = 900

def _post_json(url: str, body: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {raw[:500]}") from exc
    return payload if isinstance(payload, dict) else {"data": payload}

def _get_json(url: str, timeout: int = 30) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {raw[:500]}") from exc
    return payload if isinstance(payload, dict) else {"items": payload}

def _fetch_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "product-creative/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch URL: {exc}") from exc

def _read_import(path: str) -> Any:
    clean = _text(path)
    if not clean:
        return {}
    payload_path = Path(clean)
    if not payload_path.exists():
        raise FileNotFoundError(f"import path does not exist: {path}")
    if payload_path.suffix.lower() in {".txt", ".md"}:
        return {"text": payload_path.read_text(encoding="utf-8-sig")}
    return json.loads(payload_path.read_text(encoding="utf-8-sig"))

def _xhs_item(note: Dict[str, Any]) -> Dict[str, Any]:
    stats = {
        "liked": note.get("likedCount") or note.get("liked") or note.get("likes") or 0,
        "collected": note.get("collectedCount") or note.get("collected") or note.get("collects") or 0,
        "comments": note.get("commentCount") or note.get("comments") or 0,
        "shares": note.get("shareCount") or note.get("shares") or 0,
    }
    return {
        "source_item_id": _text(note.get("id") or note.get("noteId")),
        "title": _sanitize_string(note.get("title"), 160),
        "text": _sanitize_string(note.get("desc") or note.get("content") or note.get("text"), 1000),
        "author": "anonymous",
        "url": _text(note.get("webUrl") or note.get("noteUrl") or note.get("url")),
        "media": {
            "image_count": len(_list(note.get("imageUrls"))),
            "has_video": bool(note.get("videoUrl")),
        },
        "stats": stats,
        "hot_score": note.get("hotScore") or sum(int(v or 0) for v in stats.values()),
        "not_product_fact": True,
    }

def _douyin_item(item: Dict[str, Any]) -> Dict[str, Any]:
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    copy_analysis = item.get("copy_analysis") if isinstance(item.get("copy_analysis"), dict) else {}
    return {
        "source_item_id": _text(item.get("aweme_id") or item.get("id") or item.get("video_id")),
        "title": _sanitize_string(item.get("title") or item.get("desc"), 200),
        "text": _sanitize_string(item.get("text") or item.get("transcript") or item.get("transcript_text"), 1600),
        "url": _text(item.get("share_url") or item.get("url")),
        "stats": stats,
        "hot_value": item.get("hot_value") or item.get("score") or 0,
        "copy_analysis": copy_analysis,
        "not_product_fact": True,
    }

def _normalize_import_items(provider: str, payload: Any, limit: int) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("notes"), list):
            source = payload.get("notes")
        elif isinstance(payload.get("items"), list):
            source = payload.get("items")
        elif isinstance(payload.get("data"), list):
            source = payload.get("data")
        elif isinstance(payload.get("text"), str) and not any(
            payload.get(key) for key in ("title", "name", "url", "source_url")
        ):
            source = [{"title": "manual import", "text": payload.get("text")}]
        else:
            source = [payload]
    elif isinstance(payload, list):
        source = payload
    else:
        source = [{"title": "manual import", "text": str(payload)}]

    items: List[Dict[str, Any]] = []
    for raw in source[:limit]:
        if not isinstance(raw, dict):
            raw = {"text": str(raw)}
        if provider.startswith("xiaohongshu") or provider.startswith("xhs"):
            items.append(_xhs_item(raw))
        elif provider.startswith("douyin"):
            items.append(_douyin_item(raw))
        else:
            items.append(
                {
                    "source_item_id": _text(raw.get("id")) or f"manual-{len(items) + 1}",
                    "title": _sanitize_string(raw.get("title") or raw.get("name") or "manual source", 200),
                    "text": _sanitize_string(raw.get("text") or raw.get("content") or raw.get("desc") or raw.get("summary"), 1600),
                    "url": _text(raw.get("url") or raw.get("source_url")),
                    "stats": raw.get("stats") if isinstance(raw.get("stats"), dict) else {},
                    "not_product_fact": True,
                }
            )
    return items

def _xhs_live(sidecar_url: str, query: str, limit: int, wait_seconds: int, auto_browser_cookie: bool) -> Dict[str, Any]:
    base_url = sidecar_url.rstrip("/")
    health = _get_json(f"{base_url}/health", timeout=10)
    auth = {}
    if auto_browser_cookie:
        try:
            auth = _post_json(f"{base_url}/auth/browser", {}, timeout=90)
        except Exception as exc:
            auth = {"connected": False, "error": str(exc)}
    job = _post_json(
        f"{base_url}/search-jobs",
        {"keywords": [query], "sort": "popular", "noteType": "all", "pages": 1, "commentPages": 1, "concurrency": 1},
        timeout=30,
    )
    job_id = _text(job.get("id") or job.get("jobId"))
    deadline = time.time() + max(5, int(wait_seconds or 60))
    latest = job
    while job_id and time.time() < deadline:
        time.sleep(2)
        latest = _get_json(f"{base_url}/search-jobs/{urllib.parse.quote(job_id)}", timeout=15)
        status = _text(latest.get("status")).lower()
        if status in {"completed", "done", "failed", "stopped", "error"}:
            break
    notes_payload = {}
    analytics = {}
    if job_id:
        query_string = urllib.parse.urlencode({"jobId": job_id, "page": 1, "pageSize": limit})
        try:
            notes_payload = _get_json(f"{base_url}/notes?{query_string}", timeout=20)
        except Exception as exc:
            notes_payload = {"error": str(exc)}
        try:
            analytics = _get_json(f"{base_url}/analytics/{urllib.parse.quote(job_id)}", timeout=20)
        except Exception as exc:
            analytics = {"error": str(exc)}
    raw_notes = notes_payload.get("items") or notes_payload.get("data") or notes_payload.get("notes") or []
    return {
        "health": health,
        "auth_status": {"attempted_browser_cookie": bool(auto_browser_cookie), "connected": bool(auth.get("connected")), "error": _text(auth.get("error"))},
        "job": latest,
        "analytics": analytics,
        "items": [_xhs_item(item) for item in raw_notes[:limit] if isinstance(item, dict)],
    }

def _douyin_live(
    sidecar_url: str,
    query: str,
    limit: int,
    transcribe_limit: int,
    analyze_first5_limit: int,
    source_url: str = "",
) -> Dict[str, Any]:
    base_url = sidecar_url.rstrip("/")
    health = _get_json(f"{base_url}/api/health", timeout=10)
    direct_url = _text(source_url)
    if direct_url:
        parsed = urllib.parse.urlparse(direct_url)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme not in {"http", "https"}
            or not (
                hostname == "douyin.com"
                or hostname.endswith(".douyin.com")
            )
        ):
            raise ValueError("Douyin direct URL must use an http(s) douyin.com host")
        match = re.search(r"/video/(\d+)", parsed.path)
        source_item_id = match.group(1) if match else parsed.path.rstrip("/").rsplit("/", 1)[-1]
        search = {
            "items": [
                {
                    "aweme_id": source_item_id,
                    "title": query or "用户指定抖音视频",
                    "share_url": direct_url,
                    "stats": {},
                }
            ],
            "count": 1,
            "source": "direct_url",
        }
    else:
        search = _post_json(
            f"{base_url}/api/search",
            {
                "keyword": query,
                "max_items": limit,
                "only_commerce": False,
                "sort_mode": "hot",
                "duration": "all",
                "content_type": "video",
                "min_hot_value": 0,
            },
            timeout=120,
        )
    items = [_douyin_item(item) for item in _list(search.get("items"))[:limit] if isinstance(item, dict)]
    transcribed = 0
    transcript_attempts = 0
    transcript_errors = []
    for item in items:
        if transcript_attempts >= max(0, int(transcribe_limit or 0)):
            break
        url = _text(item.get("url"))
        if not url:
            continue
        transcript_attempts += 1
        try:
            result = _post_json(
                f"{base_url}/api/video/transcribe-online",
                {"url": url, "api_key": "", "deepseek_api_key": ""},
                timeout=240,
            )
            item["text"] = _sanitize_string(result.get("text"), 2000)
            item["copy_analysis"] = result.get("copy_analysis") if isinstance(result.get("copy_analysis"), dict) else {}
            item["transcript_status"] = "completed"
            transcribed += 1
        except Exception as exc:
            item["transcript_status"] = "failed"
            transcript_errors.append({"url": url, "error": str(exc)[:300]})
    first5_analyzed = 0
    first5_attempts = 0
    first5_errors = []
    for item in items:
        if first5_attempts >= max(0, int(analyze_first5_limit or 0)):
            break
        url = _text(item.get("url"))
        if not url:
            continue
        first5_attempts += 1
        try:
            result = _post_json(
                f"{base_url}/api/video/analyze-first5",
                {"url": url, "api_key": "", "siliconflow_api_key": ""},
                # The sidecar permits up to 180 seconds for Ark file upload
                # and 600 seconds for the Responses analysis. Keep this
                # client boundary longer than the sidecar's own bounded work
                # so a valid slow result is not discarded at 360 seconds.
                timeout=DOUYIN_FIRST5_TIMEOUT_SECONDS,
            )
            item["first5_analysis"] = {
                "model": _text(result.get("model")),
                "input_mode": _text(result.get("input_mode")),
                "analyzed_seconds": result.get("analyzed_seconds"),
                "analysis": result.get("analysis") if isinstance(result.get("analysis"), dict) else {},
            }
            item["first5_analysis_status"] = "completed"
            first5_analyzed += 1
        except Exception as exc:
            item["first5_analysis_status"] = "failed"
            first5_errors.append({"url": url, "error": str(exc)[:300]})
    return {
        "health": health,
        "search": search,
        "items": items,
        "transcribed_count": transcribed,
        "transcript_attempt_count": transcript_attempts,
        "transcript_errors": transcript_errors,
        "first5_analyzed_count": first5_analyzed,
        "first5_attempt_count": first5_attempts,
        "first5_analysis_errors": first5_errors,
    }

def _snapshot_markdown(snapshot: Dict[str, Any]) -> str:
    lines = [
        f"# {snapshot['snapshot_id']}",
        "",
        f"Provider: {snapshot['provider']}",
        f"Channel: {snapshot['channel']}",
        f"Query: {snapshot['query']}",
        f"Status: {snapshot['status']}",
        f"Items: {len(snapshot.get('items') or [])}",
        "",
        "## Summary",
        "",
        snapshot.get("summary", ""),
        "",
        "## Items",
        "",
    ]
    for item in snapshot.get("items") or []:
        title = item.get("title") or item.get("source_item_id") or "item"
        lines.append(f"- {title} ({item.get('url', '')})")
    lines.extend(["", "## Risk Flags", ""])
    lines.extend([f"- {item}" for item in snapshot.get("risk_flags", [])] or ["- None"])
    lines.append("")
    return "\n".join(lines)

def collect_external_source_snapshot(
    product_id: str,
    provider: str = "manual",
    query: str = "",
    channel: str = "",
    mode: str = "dry_run",
    limit: int = 5,
    import_path: str = "",
    text: str = "",
    url: str = "",
    sidecar_url: str = "",
    wait_seconds: int = 90,
    transcribe_limit: int = 1,
    auto_browser_cookie: bool = False,
    analyze_first5_limit: int = 1,
) -> Dict[str, Any]:
    base = ensure_product(product_id)
    clean_provider = _text(provider) or "manual"
    clean_mode = _text(mode) or "dry_run"
    clean_query = _text(query) or _text(text)[:80] or _text(url)
    clean_limit = _safe_limit(limit, 5, 20)
    risk_flags: List[str] = []
    raw_ref: Dict[str, Any] = {}
    items: List[Dict[str, Any]] = []
    status = "completed"
    external_collection_performed = False
    external_provider_requested = (
        clean_provider not in {"manual", "manual-import"}
        and (clean_mode == "live" or (clean_provider in {"generic-web", "web"} and bool(url)))
    )

    try:
        if external_provider_requested and os.environ.get("PRODUCT_CREATIVE_ENABLE_EXTERNAL_PROVIDER") != "1":
            status = "blocked"
            risk_flags.append("Real external provider collection is disabled; use manual/import mode.")
        elif clean_mode == "import" and import_path:
            imported = _read_import(import_path)
            items = _normalize_import_items(clean_provider, imported, clean_limit)
            raw_ref = {"import_path": str(Path(import_path).resolve())}
        elif clean_provider in {"manual", "manual-import"}:
            imported = _read_import(import_path) if import_path else {"text": text or clean_query}
            items = _normalize_import_items(clean_provider, imported, clean_limit)
        elif clean_provider in {"generic-web", "web"}:
            if url:
                fetched = _fetch_text(url)
                items = _normalize_import_items("generic-web", {"title": url, "url": url, "text": fetched[:4000]}, clean_limit)
                external_collection_performed = True
            else:
                status = "needs_hermes_web_search"
                risk_flags.append("No URL was provided. Use Hermes web_search/web_extract, then import the result as manual source text.")
        elif clean_provider in {"xiaohongshu-sidecar", "xhs-sidecar", "xiaohongshu"}:
            if clean_mode != "live":
                status = "needs_live_or_import"
                risk_flags.append("XHS sidecar requires mode=live or an import_path for dry validation.")
            else:
                live = _xhs_live(sidecar_url or DEFAULT_XHS_SIDECAR, clean_query, clean_limit, wait_seconds, auto_browser_cookie)
                items = _list(live.get("items"))
                raw_ref = {
                    "sidecar_url": sidecar_url or DEFAULT_XHS_SIDECAR,
                    "job": live.get("job", {}),
                    "analytics": live.get("analytics", {}),
                    "auth_status": live.get("auth_status", {}),
                }
                external_collection_performed = True
                job_status = _text((live.get("job") or {}).get("status")).lower()
                breaker_reason = _text((live.get("job") or {}).get("breakerReason"))
                auth_status = live.get("auth_status") if isinstance(live.get("auth_status"), dict) else {}
                auth_error = _text(auth_status.get("error"))
                if job_status in {"failed", "error", "stopped"} and items:
                    status = "completed_partial"
                    risk_flags.append(breaker_reason or f"XHS sidecar job ended with status={job_status} after returning usable notes.")
                elif job_status in {"failed", "error", "stopped"}:
                    status = "blocked"
                    risk_flags.append(breaker_reason or f"XHS sidecar job ended with status={job_status}.")
                elif auth_status.get("attempted_browser_cookie") and not auth_status.get("connected") and auth_error and items:
                    status = "completed_partial"
                    risk_flags.append(f"XHS browser-cookie refresh failed after returning usable notes: {auth_error[:420]}")
                elif auth_status.get("attempted_browser_cookie") and not auth_status.get("connected") and auth_error:
                    status = "blocked"
                    risk_flags.append(auth_error[:500])
                elif not items:
                    status = "completed_empty"
                    risk_flags.append("XHS sidecar returned no sanitized notes.")
        elif clean_provider in {"douyin-sidecar", "douyin"}:
            if clean_mode != "live":
                status = "needs_live_or_import"
                risk_flags.append("Douyin sidecar requires mode=live or an import_path for dry validation.")
            else:
                live = _douyin_live(
                    sidecar_url or DEFAULT_DOUYIN_SIDECAR,
                    clean_query,
                    clean_limit,
                    transcribe_limit,
                    analyze_first5_limit,
                    source_url=url,
                )
                items = _list(live.get("items"))
                raw_ref = {
                    "sidecar_url": sidecar_url or DEFAULT_DOUYIN_SIDECAR,
                    "search_count": (live.get("search") or {}).get("count"),
                    "transcribed_count": live.get("transcribed_count", 0),
                    "transcript_attempt_count": live.get("transcript_attempt_count", 0),
                    "transcript_errors": live.get("transcript_errors", []),
                    "first5_analyzed_count": live.get("first5_analyzed_count", 0),
                    "first5_attempt_count": live.get("first5_attempt_count", 0),
                    "first5_analysis_errors": live.get("first5_analysis_errors", []),
                }
                external_collection_performed = True
                if not items:
                    status = "completed_empty"
                    risk_flags.append("Douyin sidecar returned no sanitized videos.")
        else:
            status = "unsupported_provider"
            risk_flags.append(f"Unsupported external source provider: {clean_provider}")
    except Exception as exc:
        status = "blocked"
        risk_flags.append(str(exc)[:500])

    snapshot_id = f"source-snapshot-{timestamp()}"
    channel_name = _text(channel) or ("xiaohongshu" if "xhs" in clean_provider or "xiaohongshu" in clean_provider else "douyin" if "douyin" in clean_provider else "web")
    summary = f"{clean_provider} snapshot for '{clean_query}' with {len(items)} sanitized item(s)."
    snapshot = {
        "schema_version": EXTERNAL_SOURCE_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "product_id": base.name,
        "created_at": now_iso(),
        "status": status,
        "provider": clean_provider,
        "mode": clean_mode,
        "query": clean_query,
        "channel": channel_name,
        "items": items,
        "items_count": len(items),
        "summary": summary,
        "source_urls": [item.get("url") for item in items if item.get("url")],
        "raw_ref": raw_ref,
        "credential_ref": "local-sidecar-session" if clean_provider in {"xiaohongshu-sidecar", "xhs-sidecar", "xiaohongshu", "douyin-sidecar", "douyin"} else "",
        "sanitization": {
            "cookie_saved": False,
            "api_key_saved": False,
            "raw_private_fields_removed": True,
            "author_anonymized": True,
        },
        "risk_flags": risk_flags,
        "not_product_fact": True,
        "external_collection_performed": external_collection_performed,
        "mutates_product_brain": False,
    }
    out_dir = base / "artifacts" / "external_source_snapshots"
    json_path = out_dir / f"{snapshot_id}.json"
    md_path = out_dir / f"{snapshot_id}.md"
    write_json(json_path, snapshot)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_snapshot_markdown(snapshot), encoding="utf-8")
    append_jsonl(
        base / "structured" / "external_source_snapshot_index.jsonl",
        {
            "snapshot_id": snapshot_id,
            "created_at": snapshot["created_at"],
            "provider": clean_provider,
            "channel": channel_name,
            "query": clean_query,
            "status": status,
            "items_count": len(items),
            "path": _rel(base, json_path),
        },
    )
    update_index_and_log(base, "external-source-snapshot", snapshot_id, [f"Provider: {clean_provider}", f"Status: {status}", f"Items: {len(items)}"])
    return {
        "success": status not in {"blocked", "unsupported_provider"},
        "schema_version": EXTERNAL_SOURCE_SNAPSHOT_SCHEMA_VERSION,
        "product_id": base.name,
        "snapshot_id": snapshot_id,
        "status": status,
        "items_count": len(items),
        "external_collection_performed": external_collection_performed,
        "risk_flags": risk_flags,
        "files": {"json": str(json_path), "markdown": str(md_path)},
        "snapshot": snapshot,
    }

def _resolve_snapshot(base: Path, value: str) -> Dict[str, Any]:
    if not value:
        raise ValueError("snapshot id or path is required")
    candidate = Path(value)
    if candidate.exists():
        resolved = candidate.resolve()
        root = base.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError("snapshot path must stay inside the product workspace")
        return read_json(resolved, {})
    path = base / "artifacts" / "external_source_snapshots" / f"{value}.json"
    if path.exists():
        return read_json(path, {})
    raise FileNotFoundError(f"source snapshot '{value}' does not exist")

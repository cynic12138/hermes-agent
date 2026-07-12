[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..\..")).Path
$python = @'
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / ".hermes" / "plugins"))
os.environ["PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER"] = "0"
os.environ["PRODUCT_CREATIVE_ENABLE_EXTERNAL_PROVIDER"] = "0"

from product_creative.provider_http import get_json, post_json
from product_creative.provider_io import download_image_asset, download_video_asset
from product_creative.application.policy import PolicyEngine
from product_creative.capabilities.registry import action_descriptors
from product_creative.contracts.durable import CommandEnvelope

attempts = []
def forbidden(*args, **kwargs):
    attempts.append(str(args[0]) if args else "network")
    raise AssertionError("network transport was reached")

blocked = []
with tempfile.TemporaryDirectory(prefix="provider-safety-") as temp, patch("urllib.request.urlopen", forbidden):
    calls = [
        lambda: post_json("https://invalid.example/provider", {}, "secret"),
        lambda: get_json("https://invalid.example/provider", "secret"),
        lambda: download_image_asset("https://invalid.example/image.png", Path(temp), "image"),
        lambda: download_video_asset("https://invalid.example/video.mp4", Path(temp), "video"),
    ]
    for call in calls:
        try:
            call()
        except PermissionError:
            blocked.append(True)
        except Exception:
            blocked.append(False)

report = {
    "success": False,
    "schema_version": "product_creative.provider_safety_check.v1",
    "blocked_entrypoints": len([item for item in blocked if item]),
    "network_call_count": len(attempts),
}
descriptor = action_descriptors()["submit_image_generation_job"]
policy = PolicyEngine()
disabled = policy.authorize(
    descriptor,
    CommandEnvelope(command=descriptor.name, product_id="safety", confirmed=True, payload={"provider": "volcengine-ark-image", "mode": "live"}),
)
os.environ["PRODUCT_CREATIVE_ENABLE_REAL_PROVIDER"] = "1"
unconfirmed = policy.authorize(
    descriptor,
    CommandEnvelope(command=descriptor.name, product_id="safety", confirmed=False, payload={"provider": "volcengine-ark-image", "mode": "live"}),
)
confirmed = policy.authorize(
    descriptor,
    CommandEnvelope(command=descriptor.name, product_id="safety", confirmed=True, payload={"provider": "volcengine-ark-image", "mode": "live"}),
)
report.update({
    "disabled_status": disabled.status,
    "unconfirmed_status": unconfirmed.status,
    "confirmed_status": confirmed.status,
})
report["success"] = (
    len(blocked) == 4 and all(blocked) and not attempts
    and not disabled.allowed and disabled.status == "blocked"
    and not unconfirmed.allowed and unconfirmed.status == "confirmation_required"
    and confirmed.allowed and confirmed.status == "allowed"
)
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["success"] else 1)
'@

$python | python - $repoRoot
exit $LASTEXITCODE

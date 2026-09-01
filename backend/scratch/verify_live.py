import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import urllib.request
from app.services.automation.playwright_service import run_browser_audit

print("=== 1. TESTING LIVE PLAYWRIGHT AUDIT PIPELINE ===")
test_site = {"platform": "Flipkart", "url": "https://www.flipkart.com", "headless": True}
audit_res = run_browser_audit(test_site)

print("Status:", audit_res["status"])
print("Platform:", audit_res["platform"])
print("Final URL:", audit_res["final_url"])
print("Audit Time:", audit_res["audit_time"])
print("Screenshot Path:", audit_res["screenshot"])
print("DOM Path:", audit_res["dom"])
print("Extracted Data Path:", audit_res["extracted_data"])
print("Evidence ID:", audit_res["evidence"]["evidence_id"])
print("Evidence Artifacts:", audit_res["evidence"]["artifacts"])
print("Evidence Items Count:", len(audit_res["evidence"]["evidence_items"]))
print("Detections Count:", len(audit_res["detection_results"]))

for det in audit_res["detection_results"]:
    print(f"  - Pattern: {det['pattern']} | Detected: {det['detected']} | Confidence: {det['confidence']}%")
    print(f"    Reason: {det['reason']}")

print("\n=== 2. TESTING STATIC ARTIFACT SERVING VIA HTTP ===")
artifacts = [
    audit_res["screenshot"],
    audit_res["dom"],
    audit_res["extracted_data"],
    audit_res["evidence"]["artifacts"]["evidence_json"]
]

for art in artifacts:
    url = f"http://127.0.0.1:8000/{art}"
    try:
        req = urllib.request.urlopen(url)
        print(f"HTTP GET {url} -> Status: {req.status} OK ({len(req.read())} bytes)")
    except Exception as e:
        print(f"HTTP GET {url} -> ERROR: {e}")

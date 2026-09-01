import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def post(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def main():
    print("1. Fetching configured websites...")
    status, websites = get("/api/v1/websites")
    print(f"Status: {status} | Found {len(websites)} websites.")

    if not websites:
        print("No websites found to audit.")
        return

    target = websites[0]
    site_id = target.get("id") or target.get("_id")
    platform = target.get("platform")
    print(f"\n2. Starting audit for site '{platform}' (ID: {site_id})...")

    audit_status, audit_data = post(f"/api/v1/automation/start/{site_id}")
    print(f"Audit Response Status: {audit_status}")

    audit_id = audit_data.get("audit_id")
    print(f"Audit ID: {audit_id}")
    print(f"Platform: {audit_data.get('platform')}")
    print(f"Pages Crawled: {audit_data.get('pages_crawled')}")
    print(f"Total Evidence Items: {audit_data.get('total_evidence_items')}")
    print(f"Total Dark Pattern Findings: {audit_data.get('total_dark_pattern_findings')}")

    print("\n3. Final Four Dark Pattern Summary:")
    summary = audit_data.get("dark_pattern_summary", [])
    for s in summary:
        print(f"  - Pattern: {s.get('pattern')} | Status: {s.get('status')} | Detected: {s.get('detected')} | Confidence: {s.get('confidence')}%")
        print(f"    Reason: {s.get('reason')}")

    print("\n4. Fetching from MongoDB via API...")
    mongo_status, mongo_data = get(f"/api/v1/automation/audit/{audit_id}")
    print(f"MongoDB Retrieval Status: {mongo_status}")
    print(f"MongoDB Pages Count: {len(mongo_data.get('pages', []))}")
    print(f"MongoDB Summary Patterns: {[p.get('pattern') for p in mongo_data.get('dark_pattern_summary', [])]}")

if __name__ == "__main__":
    main()

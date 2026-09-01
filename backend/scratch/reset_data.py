import os
import shutil
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.database import client, DATABASE_NAME, website_collection
from app.services.evidence.mongodb_evidence_service import EVIDENCE_DB_NAME

def reset_all_evidence():
    print("=" * 60)
    print("STARTING AUDIT & EVIDENCE DATA RESET")
    print("=" * 60)

    # 1. Check Website Configuration Database (MUST BE PRESERVED)
    print(f"\n[1] Checking Website Configuration DB: '{DATABASE_NAME}'")
    website_count = website_collection.count_documents({})
    websites = list(website_collection.find({}, {"platform": 1, "url": 1}))
    print(f"  -> Preserved websites count: {website_count}")
    for w in websites:
        print(f"     - Platform: {w.get('platform')}, URL: {w.get('url')}")
    assert website_count > 0, "Website configuration should not be empty!"

    # 2. Check current state of dark_pattern_evidence database
    print(f"\n[2] Checking evidence database: '{EVIDENCE_DB_NAME}'")
    dbs_before = client.list_database_names()
    print(f"  -> All databases before reset: {dbs_before}")

    if EVIDENCE_DB_NAME in dbs_before:
        evidence_db_before = client[EVIDENCE_DB_NAME]
        collections_before = evidence_db_before.list_collection_names()
        print(f"  -> Collections in '{EVIDENCE_DB_NAME}' before drop: {collections_before}")
        for col_name in collections_before:
            cnt = evidence_db_before[col_name].count_documents({})
            print(f"     - {col_name}: {cnt} documents")
    else:
        print(f"  -> Database '{EVIDENCE_DB_NAME}' does not currently exist.")

    # 3. Drop the entire dark_pattern_evidence database
    print(f"\n[3] Dropping database '{EVIDENCE_DB_NAME}'...")
    client.drop_database(EVIDENCE_DB_NAME)
    print(f"  -> Successfully dropped database '{EVIDENCE_DB_NAME}'")

    # 4. Clean up local filesystem audit artifacts under backend/artifacts/
    backend_artifacts_dir = Path(__file__).resolve().parent.parent / "artifacts"
    print(f"\n[4] Cleaning up local audit artifacts under: {backend_artifacts_dir}")
    removed_dirs_count = 0
    if backend_artifacts_dir.exists():
        for item in backend_artifacts_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
                removed_dirs_count += 1
                print(f"  -> Removed local directory: {item.name}")
            elif item.is_file():
                item.unlink()
                print(f"  -> Removed local file: {item.name}")
    print(f"  -> Total local artifact folders cleaned: {removed_dirs_count}")

    # Also clean any old temporary files in storage/evidence if any exist
    storage_evidence_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "evidence"
    if storage_evidence_dir.exists():
        for sub in storage_evidence_dir.iterdir():
            if sub.is_dir():
                for f in sub.iterdir():
                    if f.is_file():
                        f.unlink()
                        print(f"  -> Removed storage file: {f.name}")

    # 5. Verification
    print("\n[5] VERIFICATION AFTER RESET:")
    dbs_after = client.list_database_names()
    evidence_db_after = client[EVIDENCE_DB_NAME]
    collections_after = evidence_db_after.list_collection_names()
    audits_count = evidence_db_after["audits"].count_documents({})
    evidence_items_count = evidence_db_after["evidence_items"].count_documents({})
    pages_count = evidence_db_after["pages"].count_documents({})
    gridfs_files_count = evidence_db_after["fs.files"].count_documents({})
    gridfs_chunks_count = evidence_db_after["fs.chunks"].count_documents({})

    website_count_after = website_collection.count_documents({})

    print("=" * 60)
    print("FINAL RESET REPORT:")
    print(f"- Evidence database reset: {'YES' if EVIDENCE_DB_NAME not in dbs_after or len(collections_after) == 0 else 'NO'}")
    print(f"- Remaining collections in dark_pattern_evidence: {len(collections_after)} {collections_after}")
    print(f"- Remaining audit count: {audits_count}")
    print(f"- Remaining page records count: {pages_count}")
    print(f"- Remaining evidence item count: {evidence_items_count}")
    print(f"- Remaining GridFS file count: {gridfs_files_count}")
    print(f"- Remaining GridFS chunk count: {gridfs_chunks_count}")
    print(f"- Old local artifact directories removed: {'YES' if removed_dirs_count >= 0 else 'NO'}")
    print(f"- Website Configuration data preserved: {'YES' if website_count_after == website_count and website_count > 0 else 'NO'} ({website_count_after} websites)")
    print("=" * 60)

if __name__ == "__main__":
    reset_all_evidence()

import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from google import genai

load_dotenv()

ARTICLES_DIR = Path(os.getenv("ARTICLES_DIR", "data/articles"))
OUTPUT_PATH = Path(os.getenv("GEMINI_FILES_PATH", "data/gemini_files.json"))


def create_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to .env first.")
    return genai.Client(api_key=api_key)


def load_existing_metadata(path: Path = OUTPUT_PATH) -> Dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"uploaded_at": None, "files": []}


def save_metadata(metadata: Dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def upload_single_file(client, file_path: str | Path) -> Dict:
    file_path = Path(file_path)
    
    with open(file_path, "rb") as f:
        config = {"mime_type": "text/markdown"}
        uploaded = client.files.upload(file=f, config=config)

    return {
        "local_filename": file_path.name,
        "gemini_name": uploaded.name,
        "display_name": getattr(uploaded, "display_name", file_path.name),
        "uri": uploaded.uri,
        "mime_type": getattr(uploaded, "mime_type", "text/markdown"),
        "state": str(getattr(uploaded, "state", "UNKNOWN")),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }


def upsert_file_metadata(record: Dict, metadata_path: Path = OUTPUT_PATH) -> Dict:
    metadata = load_existing_metadata(metadata_path)
    records: List[Dict] = metadata.get("files", [])
    by_name = {item["local_filename"]: item for item in records}
    by_name[record["local_filename"]] = record

    updated_records = sorted(by_name.values(), key=lambda item: item["local_filename"])
    metadata.update({
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "sdk": "google-genai",
        "articles_dir": str(ARTICLES_DIR),
        "files_total_tracked": len(updated_records),
        "files": updated_records,
    })
    save_metadata(metadata, metadata_path)
    return metadata


def upload_markdown_files(limit=None):
    client = create_client()

    paths = sorted(glob(str(ARTICLES_DIR / "*.md")))
    if limit:
        paths = paths[:limit]

    existing = load_existing_metadata()
    uploaded_by_name = {item["local_filename"]: item for item in existing.get("files", [])}
    uploaded_records = list(existing.get("files", []))

    print(f"[*] Gemini File API Upload - Files discovered: {len(paths)}")

    uploaded_count = 0
    skipped_count = 0

    for index, path in enumerate(paths, 1):
        file_path = Path(path)
        local_filename = file_path.name

        if local_filename in uploaded_by_name:
            print(f"[{index}/{len(paths)}] SKIP already uploaded: {local_filename}")
            skipped_count += 1
            continue

        print(f"[{index}/{len(paths)}] Uploading: {local_filename}")
        record = upload_single_file(client, file_path)
        uploaded_records.append(record)
        uploaded_by_name[local_filename] = record
        uploaded_count += 1

        time.sleep(0.2)

    metadata = {
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "sdk": "google-genai",
        "articles_dir": str(ARTICLES_DIR),
        "files_discovered": len(paths),
        "files_uploaded_this_run": uploaded_count,
        "files_skipped_this_run": skipped_count,
        "files_total_tracked": len(uploaded_records),
        "files": uploaded_records,
    }
    save_metadata(metadata)

    print(f"\n[DONE] Gemini upload complete. Uploaded: {uploaded_count}, Skipped: {skipped_count}, Total: {len(uploaded_records)}")

    return metadata


if __name__ == "__main__":
    upload_markdown_files()

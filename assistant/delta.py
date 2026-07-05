import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_manifest(path: str | Path) -> Dict:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {"articles": {}}

    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(path: str | Path, manifest: Dict) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()

    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def detect_delta(article_records: List[Dict], manifest: Dict) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    existing = manifest.get("articles", {})
    new_articles = []
    updated_articles = []
    unchanged_articles = []

    for record in article_records:
        article_id = str(record["article_id"])
        previous = existing.get(article_id)

        if not previous:
            record["delta_reason"] = "new"
            new_articles.append(record)
            continue

        if previous.get("updated_at") != record.get("updated_at"):
            record["delta_reason"] = "updated_at_changed"
            updated_articles.append(record)
            continue

        if previous.get("content_hash") != record.get("content_hash"):
            record["delta_reason"] = "content_hash_changed"
            updated_articles.append(record)
            continue

        record["delta_reason"] = "unchanged"
        unchanged_articles.append(record)

    return new_articles, updated_articles, unchanged_articles


def upsert_manifest_record(manifest: Dict, record: Dict) -> None:
    article_id = str(record["article_id"])
    previous = manifest.setdefault("articles", {}).get(article_id, {})
    providers = previous.get("providers", {})

    if record.get("provider"):
        provider_payload = {
            "last_uploaded_at": record.get("last_uploaded_at"),
        }

        if record["provider"] == "gemini":
            provider_payload.update({
                "file_name": record.get("gemini_name"),
                "uri": record.get("gemini_uri"),
            })
        elif record["provider"] == "openai":
            provider_payload.update({
                "vector_store_id": record.get("openai_vector_store_id"),
                "file_batch_id": record.get("openai_file_batch_id"),
            })

        providers[record["provider"]] = provider_payload

    manifest["articles"][article_id] = {
        "article_id": article_id,
        "title": record.get("title"),
        "url": record.get("url"),
        "filename": record.get("filename"),
        "updated_at": record.get("updated_at"),
        "content_hash": record.get("content_hash"),
        "last_uploaded_at": record.get("last_uploaded_at") or previous.get("last_uploaded_at"),
        "gemini_name": record.get("gemini_name") or previous.get("gemini_name"),
        "gemini_uri": record.get("gemini_uri") or previous.get("gemini_uri"),
        "providers": providers,
    }


def write_run_log(path: str | Path, summary: Dict) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()

    with log_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

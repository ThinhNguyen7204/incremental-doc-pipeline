import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from assistant.gemini.build_index import build_index
from assistant.delta import (
    compute_sha256,
    detect_delta,
    load_manifest,
    save_manifest,
    upsert_manifest_record,
    write_run_log,
)
from assistant.gemini.gemini_upload_files import (
    create_client as create_gemini_client,
    upload_single_file as upload_gemini_file,
    upsert_file_metadata as upsert_gemini_file_metadata,
)
from assistant.openai.upload_to_vectorstore import VectorStoreManager
from scraper.fetch_articles import ZendeskScraper
from scraper.html_to_markdown import MarkdownConverter

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
ARTICLE_LIMIT = int(os.getenv("ARTICLE_LIMIT", "100"))
ARTICLES_DIR = Path(os.getenv("ARTICLES_DIR", "data/articles"))
MANIFEST_PATH = Path(os.getenv("ARTICLE_MANIFEST_PATH", "data/article_manifest.json"))
RUN_LOG_PATH = Path(os.getenv("DAILY_JOB_LOG_PATH", "logs/daily_job_last_run.json"))
VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID", "").strip()


def prepare_article_records(articles):
    converter = MarkdownConverter()
    records = []

    for article in articles:
        converted = converter.convert_article(article)
        filename = f"{converted['slug']}.md"
        markdown = converted["markdown"]

        records.append({
            "article_id": str(article["id"]),
            "title": article["title"],
            "url": article["url"],
            "updated_at": article.get("updated_at"),
            "filename": filename,
            "markdown": markdown,
            "content_hash": compute_sha256(markdown),
        })

    return records


def write_markdown_file(record):
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTICLES_DIR / record["filename"]
    path.write_text(record["markdown"], encoding="utf-8")
    return path


def upload_gemini_deltas(changed_articles, manifest):
    uploaded_delta = []
    client = create_gemini_client() if changed_articles else None

    for index, record in enumerate(changed_articles, 1):
        print(f"[{index}/{len(changed_articles)}] Gemini delta {record['delta_reason']}: {record['filename']}")
        file_path = write_markdown_file(record)
        upload_record = upload_gemini_file(client, file_path)
        upsert_gemini_file_metadata(upload_record)

        record["provider"] = "gemini"
        record["last_uploaded_at"] = upload_record["uploaded_at"]
        record["gemini_name"] = upload_record["gemini_name"]
        record["gemini_uri"] = upload_record["uri"]
        upsert_manifest_record(manifest, record)
        uploaded_delta.append(record["filename"])

    return uploaded_delta


def upload_openai_deltas(changed_articles, manifest):
    if changed_articles and not VECTOR_STORE_ID:
        raise ValueError("VECTOR_STORE_ID is required when AI_PROVIDER=openai")

    uploaded_delta = []
    file_paths = []

    for record in changed_articles:
        file_paths.append(write_markdown_file(record))

    file_batch = None
    if file_paths:
        manager = VectorStoreManager()
        file_batch = manager.upload_delta_files(VECTOR_STORE_ID, file_paths)
        if not file_batch:
            raise RuntimeError("OpenAI delta upload failed")

    for record in changed_articles:
        record["provider"] = "openai"
        record["last_uploaded_at"] = datetime.now(timezone.utc).isoformat()
        record["openai_vector_store_id"] = VECTOR_STORE_ID
        record["openai_file_batch_id"] = getattr(file_batch, "id", None) if file_batch else None
        upsert_manifest_record(manifest, record)
        uploaded_delta.append(record["filename"])

    return uploaded_delta


def preserve_unchanged_manifest_records(unchanged_articles, manifest):
    for record in unchanged_articles:
        previous = manifest.get("articles", {}).get(str(record["article_id"]), {})
        record["last_uploaded_at"] = previous.get("last_uploaded_at")
        record["gemini_name"] = previous.get("gemini_name")
        record["gemini_uri"] = previous.get("gemini_uri")
        upsert_manifest_record(manifest, record)


def run_daily_job():
    if AI_PROVIDER not in {"gemini", "openai"}:
        raise ValueError("AI_PROVIDER must be either 'gemini' or 'openai'")

    started_at = datetime.now(timezone.utc).isoformat()

    print(f"[*] Starting OptiBot Daily Scraper Job (AI provider: {AI_PROVIDER})")
    scraper = ZendeskScraper()
    articles = scraper.scrape_all(min_articles=ARTICLE_LIMIT)
    if not articles:
        raise RuntimeError("No articles scraped. Aborting daily job.")

    print("\n[*] Preparing Markdown records and hashes...")
    records = prepare_article_records(articles)

    manifest = load_manifest(MANIFEST_PATH)
    new_articles, updated_articles, unchanged_articles = detect_delta(records, manifest)
    changed_articles = new_articles + updated_articles

    print(f"\n[*] Delta summary - Scraped: {len(records)}, New: {len(new_articles)}, Updated: {len(updated_articles)}, Unchanged: {len(unchanged_articles)}")

    if AI_PROVIDER == "gemini":
        uploaded_delta = upload_gemini_deltas(changed_articles, manifest)
    else:
        uploaded_delta = upload_openai_deltas(changed_articles, manifest)

    preserve_unchanged_manifest_records(unchanged_articles, manifest)
    save_manifest(MANIFEST_PATH, manifest)

    index_rebuilt = False
    if changed_articles and AI_PROVIDER == "gemini":
        print("\n[*] Rebuilding local chunk index because Gemini deltas were uploaded...")
        build_index()
        index_rebuilt = True
    elif changed_articles and AI_PROVIDER == "openai":
        print("\n[*] OpenAI deltas uploaded. Skipping local index rebuild.")
    else:
        print(f"\n[*] No deltas found. Skipping {AI_PROVIDER} upload and index rebuild.")

    summary = {
        "started_at": started_at,
        "ai_provider": AI_PROVIDER,
        "scraped_articles": len(records),
        "new_articles": len(new_articles),
        "updated_articles": len(updated_articles),
        "unchanged_articles": len(unchanged_articles),
        "uploaded_delta_files": len(uploaded_delta),
        "uploaded_delta_filenames": uploaded_delta,
        "index_rebuilt": index_rebuilt,
        "manifest_path": str(MANIFEST_PATH),
        "vector_store_id": VECTOR_STORE_ID if AI_PROVIDER == "openai" else None,
    }
    write_run_log(RUN_LOG_PATH, summary)

    print(f"\n[DONE] Daily job complete! Manifest saved to {MANIFEST_PATH}")

    return summary


def main():
    try:
        run_daily_job()
        return 0
    except Exception as exc:
        print(f"[ERROR] Daily job failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

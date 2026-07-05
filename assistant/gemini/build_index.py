import json
import re
from glob import glob
from pathlib import Path

ARTICLES_DIR = Path("data/articles")
OUTPUT_PATH = Path("data/chunks.json")
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def parse_markdown(path: Path):
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    source_match = re.search(r"^\*\*Source\*\*:\s*(.+)$", text, re.MULTILINE)

    title = title_match.group(1).strip() if title_match else path.stem
    article_url = source_match.group(1).strip() if source_match else ""

    body = re.sub(r"^#\s+.+$", "", text, count=1, flags=re.MULTILINE)
    body = re.sub(r"^\*\*(Source|Updated|Labels)\*\*:.+$", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n-{3,}\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    return title, article_url, body


def split_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = max(0, end - overlap)

    return chunks


def build_index():
    paths = sorted(glob(str(ARTICLES_DIR / "*.md")))
    chunks = []

    print("=" * 60)
    print("Building local chunk index")
    print("=" * 60)
    print(f"Files discovered: {len(paths)}")

    for file_number, path_str in enumerate(paths, 1):
        path = Path(path_str)
        title, article_url, body = parse_markdown(path)
        article_chunks = split_text(body)

        print(f"[{file_number}/{len(paths)}] {path.name}: {len(article_chunks)} chunks")

        for chunk_index, chunk_text in enumerate(article_chunks):
            chunks.append({
                "chunk_id": f"{path.name}::{chunk_index}",
                "title": title,
                "article_url": article_url,
                "filename": path.name,
                "chunk_index": chunk_index,
                "text": chunk_text,
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "files_loaded": len(paths),
            "chunks_created": len(chunks),
            "chunks": chunks,
        }, f, ensure_ascii=False, indent=2)

    average = round(len(chunks) / len(paths), 2) if paths else 0

    print("\n" + "=" * 60)
    print("Index build complete")
    print(f"Files loaded: {len(paths)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Average chunks/file: {average}")
    print(f"Saved index: {OUTPUT_PATH}")
    print("=" * 60)

    return chunks


if __name__ == "__main__":
    build_index()

import glob
import os
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class VectorStoreManager:
    """Manage OpenAI Vector Store creation and file uploads."""

    def __init__(self):
        import httpx

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in .env file")

        http_client = httpx.Client(
            timeout=120.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client,
            max_retries=2,
        )

    def create_vector_store(self, name="OptiSigns Support Docs"):
        """Create a new vector store for OptiSigns documentation."""
        print("Creating Vector Store...")

        vector_store = self.client.beta.vector_stores.create(name=name)

        print("[OK] Created Vector Store")
        print(f"     ID: {vector_store.id}")
        print(f"     Name: {vector_store.name}")
        print(f"     Status: {vector_store.status}")

        return vector_store

    def upload_file_paths(self, vector_store_id: str, file_paths: Iterable[str | Path]):
        """Upload specific files to an existing vector store."""
        paths: List[Path] = [Path(path) for path in file_paths]
        if not paths:
            print("[*] No OpenAI delta files to upload.")
            return None

        print(f"[*] Uploading {len(paths)} file(s) to Vector Store {vector_store_id}...")
        file_streams = [path.open("rb") for path in paths]

        try:
            file_batch = self.client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store_id,
                files=file_streams,
            )

            print("\n[OK] OpenAI upload complete!")
            print(f"     Status: {file_batch.status}")
            print(f"     File counts: {file_batch.file_counts}")
            return file_batch
        except Exception as exc:
            print(f"[ERROR] OpenAI upload failed: {exc}")
            return None
        finally:
            for stream in file_streams:
                stream.close()

    def upload_delta_files(self, vector_store_id: str, file_paths: Iterable[str | Path]):
        """Upload only changed Markdown files to an existing vector store."""
        if not vector_store_id:
            raise ValueError("VECTOR_STORE_ID is required for OpenAI delta uploads")
        return self.upload_file_paths(vector_store_id, file_paths)

    def upload_files(self, vector_store_id, articles_dir="data/articles"):
        """Upload all markdown files to vector store."""
        print(f"\n[*] Preparing to upload files from {articles_dir}...")

        file_paths = glob.glob(os.path.join(articles_dir, "*.md"))

        if not file_paths:
            print(f"[ERROR] No markdown files found in {articles_dir}")
            return None

        print(f"[+] Found {len(file_paths)} markdown files")
        print("[*] Opening file streams...")
        print(f"[*] Uploading files to Vector Store {vector_store_id}...")
        print(f"    This may take a while for {len(file_paths)} files...")

        return self.upload_file_paths(vector_store_id, file_paths)

    def get_vector_store(self, vector_store_id):
        """Get vector store details."""
        try:
            return self.client.beta.vector_stores.retrieve(vector_store_id)
        except Exception as exc:
            print(f"[ERROR] Failed to retrieve vector store: {exc}")
            return None


def main():
    """Main execution - create vector store and upload files."""
    manager = VectorStoreManager()
    vector_store = manager.create_vector_store()
    if not vector_store:
        print("[ERROR] Failed to create vector store")
        return 1

    file_batch = manager.upload_files(vector_store.id)
    if not file_batch:
        print("[ERROR] Failed to upload files")
        return 1

    print(f"\n[DONE] Save this to .env: VECTOR_STORE_ID={vector_store.id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

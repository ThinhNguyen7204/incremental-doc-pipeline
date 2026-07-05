import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

INDEX_PATH = Path("data/chunks.json")
LOG_PATH = Path("logs/gemini_test_output.txt")
TOP_K = 5

SYSTEM_PROMPT = """You are OptiBot, the customer-support bot for OptiSigns.com.
• Tone: helpful, factual, concise.
• Only answer using the uploaded docs.
• Max 5 bullet points; else link to the doc.
• Cite up to 3 "Article URL:" lines per reply."""

STOPWORDS = {
    "a", "an", "the", "i", "you", "we", "to", "do", "does", "how", "what",
    "is", "are", "of", "for", "with", "and", "or", "in", "on", "my", "your",
    "add", "use", "using", "can", "please", "me", "it", "this", "that"
}


def create_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to .env first.")
    return genai.Client(api_key=api_key)


def get_model_name():
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def tokenize(text):
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def load_chunks():
    if not INDEX_PATH.exists():
        raise FileNotFoundError("data/chunks.json not found. Run assistant/build_index.py first.")

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("chunks", [])


def score_chunk(query, chunk):
    query_tokens = tokenize(query)
    if not query_tokens:
        return 0

    title = chunk.get("title", "")
    text = chunk.get("text", "")
    haystack = f"{title}\n{text}".lower()
    title_lower = title.lower()
    query_lower = query.lower()

    score = 0
    for token in query_tokens:
        if token in haystack:
            score += haystack.count(token)
        if token in title_lower:
            score += 5

    if query_lower in haystack:
        score += 20

    if "youtube" in query_lower and "youtube" in haystack:
        score += 30

    return score


def retrieve_chunks(question, top_k=TOP_K):
    chunks = load_chunks()
    scored = []

    for chunk in chunks:
        score = score_chunk(question, chunk)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def build_prompt(question, chunks):
    context_blocks = []

    for index, chunk in enumerate(chunks, 1):
        context_blocks.append(
            f"[Document {index}]\n"
            f"Title: {chunk.get('title', '')}\n"
            f"Article URL: {chunk.get('article_url', '')}\n"
            f"Content:\n{chunk.get('text', '')}"
        )

    context = "\n\n---\n\n".join(context_blocks)

    return f"""{SYSTEM_PROMPT}

Use only the following retrieved OptiSigns support documentation context.
If the answer is not in the context, say you could not find it in the uploaded docs.
Return no more than 5 bullet points.
End with up to 3 unique lines in exactly this format: Article URL: <url>

Retrieved context:
{context}

User question: {question}
"""


def answer_question(question):
    import time
    client = create_client()
    model_name = get_model_name()
    chunks = retrieve_chunks(question)

    if not chunks:
        return "I could not find relevant information in the uploaded docs.", []

    prompt = build_prompt(question, chunks)
    
    # Retry logic to handle temporary 503 or 429 errors from Gemini
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            answer = response.text.strip() if response.text else "No response generated."
            return answer, chunks
        except Exception as e:
            if attempt == 2:  # 3rd attempt failed
                raise
            error_msg = str(e)
            if '503' in error_msg or '429' in error_msg:
                time.sleep(2 ** attempt)  # Wait 1s, then 2s
            else:
                raise


def save_log(question, answer, chunks):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write("Question:\n")
        f.write(question + "\n\n")
        f.write("Retrieved chunks:\n")
        for chunk in chunks:
            f.write(f"- {chunk.get('title')} | {chunk.get('article_url')} | {chunk.get('chunk_id')}\n")
        f.write("\nAnswer:\n")
        f.write(answer + "\n")


def main():
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = input("Ask OptiBot: ").strip()

    print("=" * 60)
    print("Gemini OptiBot")
    print("=" * 60)
    print(f"Model: {get_model_name()}")
    print(f"Question: {question}\n")

    answer, chunks = answer_question(question)
    print(answer)

    save_log(question, answer, chunks)
    print(f"\n[Saved log] {LOG_PATH}")
    print(f"[Retrieved chunks] {len(chunks)}")


if __name__ == "__main__":
    main()

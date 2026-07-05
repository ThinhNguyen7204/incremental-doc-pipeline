import re
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request

from assistant.gemini.gemini_bot import answer_question, get_model_name

app = Flask(__name__)


ARTICLE_URL_RE = re.compile(r"Article URL[\s\*:]*<?(https?://[^\s>]+)", re.IGNORECASE)


def extract_citations(answer: str):
    urls = []
    for match in ARTICLE_URL_RE.findall(answer or ""):
        clean_url = match.rstrip(".)]\n\r\t ")
        if clean_url not in urls:
            urls.append(clean_url)
    return urls[:3]


def citation_label(url: str):
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return parsed.netloc
    return path.split("/")[-1].replace("-", " ").title()


@app.get("/")
def index():
    return render_template("index.html", model_name=get_model_name())


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or "").strip()

    if not question:
        return jsonify({"error": "Message is required."}), 400

    try:
        answer, chunks = answer_question(question)
        citations = [
            {"url": url, "label": citation_label(url)}
            for url in extract_citations(answer)
        ]

        return jsonify({
            "answer": answer,
            "citations": citations,
            "retrieved_count": len(chunks),
            "model": get_model_name(),
        })
    except FileNotFoundError:
        return jsonify({
            "error": "Local chunk index not found. Run: python assistant/build_index.py",
        }), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

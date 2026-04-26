from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from openai import OpenAI
import os

SYSTEM_PROMPT = """
You are a helpful PDF assistant for technical documentation.

Rules:
- Answer ONLY using the provided context
- Always cite the page number so the user knows where to read more
- If the answer is not in the context, say "I couldn't find that in the document" — do not guess
- Keep answers clear, concise and beginner-friendly
- If code is involved, format it properly
"""

def get_answer(question: str, collection_name: str, chat_history: list):
    # ── Clients ───────────────────────────────────────────
    client = OpenAI(
        api_key  = os.getenv("GOOGLE_API_KEY"),
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    embedding_model = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview"
    )

    # ── Vector DB ─────────────────────────────────────────
    vector_db = QdrantVectorStore.from_existing_collection(
        embedding       = embedding_model,
        url             = os.getenv("QDRANT_URL"),
        api_key         = os.getenv("QDRANT_API_KEY") or None,
        collection_name = collection_name
    )

    # ── MMR Retrieval ─────────────────────────────────────
    results = vector_db.max_marginal_relevance_search(
        query      = question,
        k          = 6,
        fetch_k    = 35,
        lambda_mult= 0.65
    )

    if not results:
        yield "I couldn't find relevant info in the document."
        return

    # ── Build Context ─────────────────────────────────────
    context_parts = []
    for r in results:
        content = r.metadata.get("parent_content", r.page_content)
        page    = r.metadata.get("page_label", r.metadata.get("page", "N/A"))
        context_parts.append(f"Page Content:\n{content}\nPage Number: {page}")

    context = "\n\n---\n\n".join(context_parts)

    # ── Messages ──────────────────────────────────────────
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *chat_history,
        {
            "role"   : "user",
            "content": f"Context:\n{context}\n\nQuestion: {question}"
        }
    ]

    # ── Stream Response ───────────────────────────────────
    response = client.chat.completions.create(
        model    = "gemini-2.5-flash",
        messages = messages,
        stream   = True
    )

    for chunk in response:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta  
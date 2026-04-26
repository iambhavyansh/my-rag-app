from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
import time, json, tempfile, os
from queue import Queue

BATCH_TOKEN_LIMIT = 25000
DELAY_SECONDS     = 62

progress_store = {}



def estimate_tokens(text):
    return len(text) // 4

def is_useful(chunk):
    text = chunk.page_content.strip()
    if len(text) < 80:
        return False
    if len(text) > 0 and sum(c.isdigit() for c in text) / len(text) > 0.4:
        return False
    return True

def smart_batch(chunks, token_limit=BATCH_TOKEN_LIMIT):
    batches, current_batch, current_tokens = [], [], 0
    for chunk in chunks:
        t = estimate_tokens(chunk.page_content)
        if current_tokens + t > token_limit:
            batches.append(current_batch)
            current_batch, current_tokens = [chunk], t
        else:
            current_batch.append(chunk)
            current_tokens += t
    if current_batch:
        batches.append(current_batch)
    return batches

def index_pdf(file_bytes: bytes, collection_name: str):
    print(f"📄 Starting indexing for collection: {collection_name}")
    progress_store[collection_name] = {"message": "Loading PDF...", "done": False}

   
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # ── Load ──────────────────────────────────────────
        loader = PyPDFLoader(file_path=tmp_path)
        docs   = loader.load()
        print(f"   Loaded {len(docs)} pages")

        # ── Split ─────────────────────────────────────────
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 500,
            chunk_overlap = 150,
            separators    = ["\n\n", "\n", ".", " ", ""]
        )
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 2000,
            chunk_overlap = 300,
            separators    = ["\n\n", "\n", ".", " ", ""]
        )

        parent_chunks = parent_splitter.split_documents(docs)
        child_chunks  = child_splitter.split_documents(docs)

        
        parent_map = {}
        for p in parent_chunks:
            page = p.metadata.get("page", 0)
            if page not in parent_map:
                parent_map[page] = p.page_content

        for chunk in child_chunks:
            page = chunk.metadata.get("page", 0)
            chunk.metadata["parent_content"] = parent_map.get(page, chunk.page_content)

        # ── Filter ────────────────────────────────────────
        chunks = [c for c in child_chunks if is_useful(c)]
        print(f"✅ Usable chunks: {len(chunks)}")

        # ── Embed & Store ─────────────────────────────────
        embedding_model = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-2-preview"
        )
        batches = smart_batch(chunks)
        print(f"📦 Total batches: {len(batches)}")
        print(f"⏱️  Estimated time: ~{len(batches) * DELAY_SECONDS // 60} mins")

        for i, batch in enumerate(batches):
            retries = 0
            while retries < 3:
                try:
                    print(f"⏳ Batch {i+1}/{len(batches)}")
                    QdrantVectorStore.from_documents(
                        documents       = batch,
                        embedding       = embedding_model,
                        url             = os.getenv("QDRANT_URL"),
                        api_key         = os.getenv("QDRANT_API_KEY") or None,
                        collection_name = collection_name
                    )
                    print(f"✅ Batch {i+1} done")

                    if i < len(batches) - 1:
                        print(f"😴 Sleeping {DELAY_SECONDS}s...")
                        for remaining in range(62, 0, -1):
                            progress_store[collection_name] = {
                                "message": f"Rate limit pause... {remaining}s (batch {i+1}/{len(batches)})",
                                "done": False
                            }
                            time.sleep(1)
                        time.sleep(DELAY_SECONDS)
                    break

                except Exception as e:
                    retries += 1
                    wait = 60 * retries
                    print(f"❌ Error: {e} — retry {retries}/3 in {wait}s")
                    time.sleep(wait)

            if retries == 3:
                print(f"🚨 Batch {i+1} permanently failed — skipping")
        progress_store[collection_name] = {"message": "Done!", "done": True}
        print(f"\n🎉 Indexing complete for {collection_name}!")

    finally:
        os.unlink(tmp_path)   
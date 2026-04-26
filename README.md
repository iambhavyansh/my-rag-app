# ⚡ RAG PDF Assistant

> Upload any PDF. Ask anything. Get answers with page references — powered by Gemini, Qdrant and FastAPI.

---

## 🌐 Live Demo

**Try it here →** [https://my-rag-app-rust.vercel.app](https://my-rag-app-rust.vercel.app)

> ⚠️ **Note:** Backend may take ~30 seconds to wake up on first use — Render's free tier likes to nap. The UI will count down for you so you know it hasn't crashed. It's just stretching. 🥱

---

## 🤔 What is this?

**RAG PDF Assistant** is a full-stack AI application that lets you upload any PDF document and have a real conversation with it. No more scrolling through 1000 pages looking for that one paragraph — just ask, and it finds it for you.

Built for anyone who's ever stared at a massive PDF and thought *"I wish I could just talk to this thing."*

---

## ✨ Features

- 📄 **Upload any PDF** — drag and drop or click to upload
- 🔍 **Smart retrieval** — finds the most relevant sections using vector similarity search
- 💬 **Multi-turn chat** — remembers your last 6 questions so you can have a real conversation
- ⚡ **Streaming responses** — answers appear token by token, just like ChatGPT
- 📌 **Page references** — every answer tells you exactly which page to look at
- 🔄 **Live indexing progress** — real-time countdown so you know what's happening
- 🌙 **Modern dark UI** — clean sidebar + chat layout, no frameworks needed

---

## 🧠 How it works — RAG explained simply

**RAG** stands for **Retrieval Augmented Generation** and it's the magic behind this app. Instead of feeding your entire 1000 page PDF to an AI (which would be impossibly expensive and slow), RAG does this:

```
📄 Your PDF
    ↓
✂️  Split into small chunks (400 tokens each)
    ↓
🔢  Convert each chunk into a vector (a list of numbers that captures meaning)
    ↓
🗄️  Store all vectors in Qdrant (a vector database)
    ↓
❓  You ask a question
    ↓
🔍  Your question is also converted to a vector
    ↓
📐  Find the chunks whose vectors are closest to your question vector
    ↓
🤖  Send only those relevant chunks to Gemini
    ↓
💬  Get a precise, grounded answer back
```

This means the AI only ever reads the parts of your PDF that are actually relevant to your question — making it fast, cheap and accurate.

### 🧩 Parent-Child Chunking

To preserve context, chunks are split at two levels:

- **Child chunks** (400 tokens) → used for precise vector search
- **Parent chunks** (2000 tokens) → retrieved and sent to the LLM for full context

This way search is precise but answers have enough surrounding context to make sense.

### 🎯 MMR Search

Instead of returning the top 5 most similar chunks (which often all say the same thing), the app uses **Maximal Marginal Relevance** — it picks chunks that are relevant AND diverse, so the LLM gets a richer picture of your document.

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| 🎨 Frontend | HTML + CSS + Vanilla JS |
| ⚙️ Backend | FastAPI (Python) |
| 🧠 Embeddings | Gemini Embedding API |
| 🤖 LLM | Gemini 2.5 Flash |
| 🗄️ Vector DB | Qdrant Cloud |
| 🚀 Hosting | Vercel (frontend) + Render (backend) |

---

## ⚙️ FastAPI Backend

The backend is built with **FastAPI** — a modern Python web framework that's fast, async-ready and comes with automatic API documentation out of the box.

Four routes power the app:

```
POST /upload        → receives PDF, starts indexing in background
GET  /status/{id}   → checks if indexing is complete
GET  /progress/{id} → streams live indexing progress (SSE)
POST /chat          → receives question, streams answer back
```

Indexing runs as a **background task** so the API never times out waiting for a large PDF to be processed. Each uploaded PDF gets a unique `collection_id` (UUID) so multiple PDFs can coexist in Qdrant without colliding.

---

## 🐢 Why does indexing take so long? (The Free Tier Tax)

Ah yes. The rate limits. Let's talk about them.

The Gemini Embedding API on the free tier gives you:
- **30,000 tokens per minute**
- **100 requests per minute**

Sounds like a lot until you have a 1000 page PDF with thousands of chunks. At that point the API looks at your request and goes:

> *"Slow down buddy, this isn't the paid plan."* 🚦

So between every batch of chunks, the app politely waits **62 seconds** — just long enough to reset the rate limit window without getting blocked. For a large PDF this means indexing can take anywhere from a few minutes to half an hour.

The good news: it only happens **once per PDF**. After indexing, answers are instant. Think of it as the app doing its homework so you don't have to. 📚

And yes, the UI shows you a live countdown so you're not just staring at a spinner wondering if it crashed. It didn't crash. It's just... being careful. 🐌

---

## 📁 Project Structure

```
my-rag-app/
├── backend/
│   ├── main.py          ← FastAPI app + all routes
│   ├── indexer.py       ← PDF loading, chunking, embedding
│   ├── retriever.py     ← vector search + LLM streaming
│   ├── .env             ← API keys 
│   └── requirements.txt
├── frontend/
│   ├── index.html       ← app structure
│   ├── style.css        ← all styling
│   └── app.js           ← all logic + API calls
└── README.md
```

---

## 🙏 Built with

- [LangChain](https://langchain.com) — document loading, splitting, vector store
- [Google Gemini](https://aistudio.google.com) — embeddings + language model
- [Qdrant](https://qdrant.tech) — vector database
- [FastAPI](https://fastapi.tiangolo.com) — backend framework

---

*Made with lots of ☕ and a healthy respect for rate limits.*

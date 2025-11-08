# 🏗️ Mini-RAG Architecture

A technical overview of the Retrieval-Augmented Generation system architecture, pipeline components, and design decisions.

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Interface (index.html)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ API Key Init │  │ Doc Upload   │  │ Question Interface  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────────────┘  │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI Server (fastapi_app_clean.py)              │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              SimpleRAGSystem Class                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │    │
│  │  │  Loader  │  │ Embedder │  │Retriever │  │Generator│ │    │
│  │  └─────┬────┘  └─────┬────┘  └─────┬────┘  └────┬───┘ │    │
│  └────────┼─────────────┼──────────────┼─────────────┼─────┘    │
└───────────┼─────────────┼──────────────┼─────────────┼──────────┘
            │             │              │             │
            ▼             ▼              ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌─────────┐ ┌──────────┐
    │ PDF/Text     │ │  Google AI   │ │ChromaDB │ │ Gemini   │
    │ Documents    │ │  Embeddings  │ │ Vector  │ │ 2.0 Flash│
    │ (pdfplumber) │ │ (embedding-  │ │  Store  │ │   API    │
    │              │ │    001)      │ │         │ │          │
    └──────────────┘ └──────────────┘ └─────────┘ └──────────┘
```

## 🔄 Document Processing Pipeline

### 1. Document Upload Flow

```
User uploads PDF/text → DocumentLoader.load_and_chunk_file()
                              │
                              ▼
                   Extract text with pdfplumber
                              │
                              ▼
              RecursiveCharacterTextSplitter
              - chunk_size: 1000 characters
              - chunk_overlap: 200 characters
                              │
                              ▼
                   Create metadata for each chunk
                   {source, page, chunk_id}
                              │
                              ▼
                   Return List[Document] objects
```

### 2. Embedding and Storage

```
List[Document] chunks → VectorStoreManager.add_documents()
                              │
                              ▼
                   GoogleGenerativeAIEmbeddings
                   - Model: embedding-001
                   - Retry logic: 3 attempts
                              │
                              ▼
                   Batch embedding (100 chunks/batch)
                              │
                              ▼
                   ChromaDB persistent storage
                   - Location: ./chroma_db/
                   - Persistence: Auto-save to disk
                              │
                              ▼
                   Return document IDs
```

**Key Design Decision**: Batching embeddings prevents rate limiting and improves throughput. Persistent storage eliminates re-embedding on restart.

## 🔍 Retrieval and Generation Pipeline

### 3. Question Answering Flow

```
User question → SimpleRAGSystem.answer_question()
                              │
                              ▼
                   Step 1: Document Retrieval
                   ┌──────────────────────────────┐
                   │ DocumentRetriever.retrieve() │
                   │ - Embed query               │
                   │ - Similarity search (top-k) │
                   │ - Calculate confidence      │
                   └──────┬───────────────────────┘
                          │
                          ▼
                   Retrieved Chunks + Retrieval Confidence
                          │
                          ▼
                   Step 2: Context Preparation
                   ┌──────────────────────────────┐
                   │ Format chunks with metadata  │
                   │ [Document 1, Page X]        │
                   │ chunk content...            │
                   └──────┬───────────────────────┘
                          │
                          ▼
                   Step 3: LLM Generation
                   ┌──────────────────────────────┐
                   │ResponseGenerator.generate()  │
                   │ - Build prompt              │
                   │ - Call Gemini API           │
                   │ - Extract answer            │
                   │ - Parse confidence (1-10)   │
                   └──────┬───────────────────────┘
                          │
                          ▼
                   Step 4: Confidence Calculation
                   ┌──────────────────────────────┐
                   │ final_confidence =          │
                   │   0.6 × retrieval_conf +    │
                   │   0.4 × (llm_conf / 10)     │
                   └──────┬───────────────────────┘
                          │
                          ▼
                   Step 5: Source Extraction
                   ┌──────────────────────────────┐
                   │ Extract unique sources      │
                   │ Format with page numbers    │
                   │ Add relevance scores        │
                   │ Filter if irrelevant        │
                   └──────┬───────────────────────┘
                          │
                          ▼
                   Return {answer, confidence, sources}
```

## 🎯 Confidence Scoring Method

### Formula
```
final_confidence = 0.6 × retrieval_confidence + 0.4 × (llm_confidence / 10)
```

### Components

1. **Retrieval Confidence** (60% weight)
   - Calculated from cosine similarity scores of retrieved chunks
   - Formula: `sum(similarity_scores) / len(similarity_scores)`
   - Range: 0.0 to 1.0
   - High score → Query matches document content well
   - Low score → Query not well-represented in knowledge base

2. **LLM Confidence** (40% weight)
   - Self-assessment by Gemini model (1-10 scale)
   - Normalized to 0.0-1.0 by dividing by 10
   - Reflects model's certainty about answer quality

### Confidence Thresholds

- **≥ 70%**: High confidence
- **30-69%**: Medium confidence
- **< 30%**: Low confidence (sources hidden as likely irrelevant)

## 🧩 Component Details

### DocumentLoader (utils/loader.py)
- **Purpose**: Extract and chunk text from documents
- **Supported Formats**: PDF (via pdfplumber), TXT, MD
- **Chunking Strategy**: RecursiveCharacterTextSplitter
  - Tries to split on paragraphs first
  - Falls back to sentences, then words
  - Maintains context with overlap
- **Metadata**: Tracks source file, page numbers, chunk IDs

### VectorStoreManager (utils/embedder.py)
- **Purpose**: Manage embeddings and vector storage
- **Embedding Model**: Google AI embedding-001
  - 768-dimensional vectors
  - Optimized for semantic search
- **Storage**: ChromaDB with persistence
  - SQLite backend for metadata
  - Vector indices for fast retrieval
- **Retry Logic**: 3 attempts with exponential backoff

### DocumentRetriever (utils/retriever.py)
- **Purpose**: Find relevant chunks for queries
- **Algorithm**: Cosine similarity search
- **Parameters**: Configurable top-k (default 3)
- **Output**: Ranked chunks with scores

### ResponseGenerator (utils/generator.py)
- **Purpose**: Generate answers from context
- **Model**: Gemini 2.0 Flash
  - Fast, cost-effective
  - Structured output support
- **Prompt Engineering**:
  - Clear role definition
  - Context injection
  - Confidence self-assessment
  - Source attribution requirements

## 🛠️ Design Decisions

### Why ChromaDB?
- **Pros**: Local-first, easy setup, persistence built-in
- **Cons**: Not suitable for massive scale (use Pinecone/Weaviate for production)
- **Alternative**: Could use FAISS for in-memory search

### Why Gemini 2.0 Flash?
- **Pros**: Free tier, fast responses, good quality
- **Cons**: Rate limits on free tier
- **Alternatives**: GPT-3.5, Claude Sonnet, Llama 3

### Why Chunking with Overlap?
- **Problem**: Long documents exceed LLM context limits
- **Solution**: Break into chunks with overlap
- **Benefit**: Maintains continuity across chunk boundaries
- **Trade-off**: Some redundancy in storage

### Why Weighted Confidence?
- **Rationale**: Retrieval confidence is more objective (cosine similarity)
- **Weighting**: 60% retrieval, 40% LLM self-assessment
- **Benefit**: Balances data-driven and model uncertainty
- **Alternative**: Could use ensemble of confidence metrics

### Why No Vector Database Auth?
- **Design Choice**: Local deployment, single-user
- **Security**: Runs on localhost only
- **Production**: Would need authentication, HTTPS, rate limiting

### Conversation Persistence Design
- **Storage Format**: JSON files per client (`./clients/{name}/conversations.json`)
- **Auto-save**: After every Q&A interaction
- **Auto-load**: When switching between clients
- **Benefits**: Preserves context across sessions, supports conversation export
- **Trade-off**: File I/O on every question (acceptable for single-user use)
- **Alternative**: Could use SQLite for better concurrent access

## 📈 Performance Characteristics

- **Embedding Speed**: ~100 chunks/second (batch processing)
- **Retrieval Latency**: <100ms for top-3 search
- **Generation Time**: 1-3 seconds (Gemini API call)
- **Concurrent Users**: 1 (single-instance FastAPI)
- **Storage**: ~5KB per chunk (text + embedding + metadata)

## 🔮 Future Enhancements

1. **Enhanced Chat Interface**: Fixed bottom chat bar with scrollable conversation history for seamless reference to past Q&A
2. **Cloud Storage Integration**: Connect to Google Drive, Dropbox, OneDrive for automatic document sync alongside local storage
3. **Multi-language Support**: Internationalization (i18n) for Spanish, French, German, Mandarin, Hindi to expand global accessibility

---

**Ready to deploy?** Check `README.md` for setup instructions!

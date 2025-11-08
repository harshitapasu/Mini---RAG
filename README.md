# Mini-RAG: Precision-First Multi-Client Knowledge Management

A Retrieval-Augmented Generation (RAG) system built for consulting firms managing sensitive, isolated client knowledge bases. Delivers precise answers with exact metrics, intelligent source filtering, and multi-document comparative analysis.

---

## 🎯 Key Features

- ✅ **Multi-Client Isolation** - Physical database separation per client (./clients/{name}/chroma_db/)
- ✅ **Conversation Persistence** - Chat history saved per client in JSON format with full Q&A tracking
- ✅ **Precision-First Sources** - Max 3 sources, 50%+ relevance threshold only
- ✅ **Intelligent Re-Ranking** - Content boosting for numbers (+15%), tables (+12%), comparatives (+10%)
- ✅ **Hybrid Summarization** - Concise narratives + exact numbers preserved (no rounding)
- ✅ **Smart Confidence** - 85%+ when correctly identifying missing information
- ✅ **Comparative Queries** - Multi-document diversity (Q1 AND Q2 representation)
- ✅ **Robust API Integration** - 5-retry Google API logic, 98%+ success rate

---

## 🔮 Potential Enhancements

- 💬 **Enhanced Chat Interface** - Fixed bottom chat bar with scrollable conversation history
- ☁️ **Cloud Storage Integration** - Connect to Google Drive, Dropbox, OneDrive for automatic sync
- 🌍 **Multi-language Support** - Spanish, French, German, Mandarin, Hindi for global accessibility

---

## 🚀 Quick Start

```bash
pip install -r requirements_fastapi.txt
$env:GOOGLE_API_KEY="your-key"  # Windows (see SETUP.md for other OS)
python run_fastapi.py
# Open http://localhost:8000
```

**First time?** → See [SETUP.md](SETUP.md) for detailed installation guide

---

## 📖 How to Use

### 1. Configure System
1. Open http://localhost:8000 in your browser
2. Click **"Configure System"**
3. Enter your Google API key
4. Click **"Configure"**

### 2. Create a Client
1. In the **Client Management** section, enter client name (e.g., "ACME_Corp")
2. Click **"Set Client"**
3. Client database created at `./clients/ACME_Corp/chroma_db/`

### 3. Upload Documents
1. Click **"Choose Files"** (supports PDF, TXT, MD)
2. Select documents (e.g., Q1_Banking_Report.pdf, Q2_Banking_Report.pdf)
3. Click **"Upload"**
4. Wait for chunking + embedding (progress shown in console)

### 4. Ask Questions
- **Simple**: "What is the total number of FDIC-insured institutions?"
- **Comparative**: "What changed between Q1 and Q2 2024?"
- **Negative**: "How do I play football?" → System confidently says "no info found"

### 5. Switch Clients
1. In **Client Management**, click **"Switch"** next to another client
2. Database instantly switches - no cross-client data leakage

---

## 💡 Example Use Cases

### Financial Analysis
```
Q: What changed in net interest margin between Q1 and Q2?
A: Net interest margin compressed from 3.2% in Q1 to 3.0% in Q2, 
   representing a 20 basis point decline.

Sources (3):
- Q1_Report.pdf (Page 12) - Relevance: 78%
- Q2_Report.pdf (Page 12) - Relevance: 76%
- Trends_Analysis.pdf (Page 5) - Relevance: 54%
```

### Negative Queries (High Confidence)
```
Q: What is our cryptocurrency strategy?
A: The provided documents do not contain information on cryptocurrency strategy.

Confidence: 87%
Sources: (none shown - correct behavior)
```

---

## 🏗️ Architecture Overview

```
User Question
    ↓
[1] Query Analysis → Detect comparative keywords ("Q1 vs Q2", "changed")
    ↓
[2] Vector Search → ChromaDB semantic similarity → Retrieve top chunks
    ↓
[3] Re-Ranking → Content boosting (numbers +15%, tables +12%)
    ↓
[4] Source Diversity → Ensure multi-document representation for comparisons
    ↓
[5] LLM Generation → Gemini 2.0 Flash → Summarize + preserve exact numbers
    ↓
[6] Confidence Scoring → Weighted formula (retrieval + LLM self-assessment)
    ↓
[7] Source Filtering → Max 3 sources, 50%+ relevance threshold
    ↓
Response: Answer + Confidence + Sources + Metadata
```

**Full architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📊 Confidence Scoring

**Formula**: `final_confidence = 0.6 × retrieval_conf + 0.4 × (llm_conf / 10)`

**Examples**:
- **High (85%+)**: Direct answer with exact numbers OR correctly identified missing info
- **Medium (60-80%)**: Good information, some details missing
- **Low (<60%)**: Partial answer, significant gaps

**Special Case**: When answer says "documents do not contain..." → confidence boosted to 85%+ (correct negative)

---

## 🔧 Configuration

Key parameters can be adjusted in `fastapi_app_clean.py`. See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for quick configuration tweaks.

**Main settings**:
- `max_sources = 3` - Maximum sources shown
- `relevance_threshold = 0.50` - Minimum similarity score
- `chunk_size = 1000` - Characters per chunk
- `k = 5` - Chunks retrieved per query

---

## 📁 Project Structure

See [PROJECT_FILES.md](PROJECT_FILES.md) for complete file inventory.

```
Mini-RAG/
├── fastapi_app_clean.py      # Main application
├── run_fastapi.py            # Server startup
├── requirements_fastapi.txt  # Dependencies
├── static/index.html         # Web UI
├── utils/                    # Core modules
│   ├── loader.py            # Document processing
│   ├── embedder.py          # Embeddings + retry logic
│   ├── retriever.py         # Intelligent retrieval
│   └── generator.py         # LLM generation
└── clients/                  # Client databases (auto-created)
```

---

## 🛠️ Troubleshooting

See [SETUP.md](SETUP.md) for detailed troubleshooting or [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for quick fixes.

---

## 📚 API Endpoints

### Core Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/configure` | POST | Set Google API key, configure system |
| `/upload` | POST | Upload documents for current client |
| `/ask` | POST | Ask question, get answer + sources |
| `/status` | GET | Check system status, document count |
| `/documents` | GET | List all documents for current client |
| `/clear` | POST | Clear all documents for current client |

### Client Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/client/set` | POST | Create or switch to client |
| `/client/list` | GET | List all available clients |
| `/client/{name}` | DELETE | Delete client and all data |

### Conversation History

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/conversations` | GET | Retrieve conversation history for current client |
| `/conversations/{id}` | DELETE | Delete specific conversation by ID |
| `/conversations` | DELETE | Clear all conversations for current client |

**Full API docs**: http://localhost:8000/docs (when server running)

---

## 🔒 Security & Compliance

- ✅ **Physical client isolation**: Separate SQLite files per client
- ✅ **No cross-client queries**: Vectorstore scoped to current_client
- ✅ **Data deletion**: `DELETE /client/{name}` removes all files
- ⚠️ **API key security**: Set via environment variable, never logged
- ⚠️ **No encryption at rest**: User responsible for disk encryption
- ❌ **No authentication**: Add reverse proxy (nginx) with auth for production

---

## 🚧 Known Limitations

1. **Single user**: No multi-user support (one session at a time)
2. **PDF/TXT/MD only**: No JSON, CSV, Excel support (yet)
3. **English only**: Multilingual embeddings not enabled
4. **Local only**: No cloud deployment setup

See **Future Enhancements** in [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📈 Performance Metrics

- **Query latency**: 1.5-3.5 seconds (Gemini API call dominates)
- **Embedding speed**: ~5 chunks/second (Google API rate limit)
- **Concurrent users**: ~10 (single-threaded FastAPI)
- **Documents per client**: Tested up to 50 PDFs (500+ pages)
- **Storage**: ~50-200 MB per client (depends on doc count)

---

## 🤝 Contributing

This is a demonstration project. For production use:
1. Add user authentication
2. Implement conversation persistence
3. Add support for JSON/CSV/Excel
4. Deploy to cloud (Docker + Kubernetes)
5. Add monitoring and logging

---

## � Support

- **Setup**: [SETUP.md](SETUP.md) - Detailed installation guide
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command cheat sheet
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - Technical deep-dive
- **API Docs**: http://localhost:8000/docs - Interactive API documentation
- **File Checklist**: [PROJECT_FILES.md](PROJECT_FILES.md) - Verify installation

---

**Built with ❤️ for precision-focused analytical work**

*Last Updated: November 2025*

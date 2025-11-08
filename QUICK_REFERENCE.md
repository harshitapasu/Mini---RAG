# Mini-RAG Quick Reference Card

One-page cheat sheet for common operations.

---

## 🚀 Quick Start (First Time)

```bash
# 1. Install
pip install -r requirements_fastapi.txt

# 2. Set API key
$env:GOOGLE_API_KEY="your-key"  # Windows
export GOOGLE_API_KEY="your-key"  # Linux/Mac

# 3. Run
python run_fastapi.py

# 4. Open browser
http://localhost:8000
```

---

## 📝 Common Commands

### Start Server
```bash
python run_fastapi.py
```

### Stop Server
```
Press CTRL+C in terminal
```

### Check Python Version
```bash
python --version  # Should be 3.9+
```

### Verify Installation
```bash
python -c "import fastapi, chromadb; print('✅ OK')"
```

---

## 🔑 API Key Management

### Set (Session)
```powershell
# Windows
$env:GOOGLE_API_KEY="AIzaSyB..."

# Linux/Mac
export GOOGLE_API_KEY="AIzaSyB..."
```

### Verify
```powershell
# Windows
echo $env:GOOGLE_API_KEY

# Linux/Mac
echo $GOOGLE_API_KEY
```

### Get New Key
https://aistudio.google.com/app/apikey

---

## 👥 Client Operations

### Create/Switch Client
1. Enter client name: `ACME_Corp`
2. Click "Set Client"
3. ✅ Database created at `./clients/ACME_Corp/chroma_db/`

### List All Clients
Click "Check Status" → See "Available clients"

### Delete Client
1. Click "Delete" button next to client name
2. Confirm deletion
3. ⚠️ All documents permanently removed

---

## 📄 Document Operations

### Upload Documents
1. Click "Choose Files"
2. Select PDF/TXT files
3. Click "Upload"
4. Wait for "✅ Uploaded X files, created Y chunks"

### Supported Formats
- ✅ PDF (`.pdf`)
- ✅ Text (`.txt`, `.md`)
- ❌ JSON, CSV, Excel (not yet supported)

### View Documents
Click "Check Status" → See "Documents: X"

---

## 💬 Asking Questions

### Simple Question
```
Q: What is the total number of FDIC-insured institutions?
```

### Comparative Question
```
Q: What changed in net interest margin between Q1 and Q2?
```

### Negative Question (Tests "No Info" Handling)
```
Q: How do I play football?
Expected: High confidence (85%+) + "documents do not contain" + No sources
```

---

## 📊 Understanding Responses

### Confidence Scores
- **85%+** = High confidence (exact numbers OR correctly identified missing info)
- **60-80%** = Medium (good info, some gaps)
- **<60%** = Low (partial answer)

### Source Relevance
- **>50%** = High quality (shown)
- **<50%** = Low quality (hidden)
- **Max 3 sources** = Hard limit

### Metrics
- **Precision@K** = % of high-quality sources (adaptive threshold: 70% of top score)
- **Grounding Accuracy** = How well answer is grounded in sources

---

## 🐛 Troubleshooting (Fast Fixes)

| Problem | Quick Fix | Details |
|---------|-----------|---------|
| Module not found | `pip install -r requirements_fastapi.txt` | [SETUP.md](SETUP.md#issue-1) |
| API key error | `$env:GOOGLE_API_KEY="your-key"` | [SETUP.md](SETUP.md#issue-2) |
| Port 8000 in use | Change port in `run_fastapi.py` to 8001 | [SETUP.md](SETUP.md#issue-3) |
| Empty answer | Check console, verify docs uploaded | [SETUP.md](SETUP.md#issue-5) |
| Google 500 error | Normal - auto retries 5x | [SETUP.md](SETUP.md#issue-4) |
| Low relevance | Upload more relevant documents | [SETUP.md](SETUP.md#issue-6) |

**Detailed troubleshooting**: See [SETUP.md](SETUP.md#common-issues)

---

## 📁 File Locations

| Item | Path |
|------|------|
| Client databases | `./clients/{ClientName}/chroma_db/` |
| Web interface | `./static/index.html` |
| Main app | `./fastapi_app_clean.py` |
| Utils | `./utils/*.py` |
| Docs | `./README.md`, `./SETUP.md` |

---

## 🔧 Configuration Quick Tweaks

### Change Max Sources (3 → 5)
**File**: `fastapi_app_clean.py`  
**Line**: ~562  
**Change**: `max_sources = 5`

### Lower Relevance Threshold (50% → 40%)
**File**: `fastapi_app_clean.py`  
**Line**: ~561  
**Change**: `relevance_threshold = 0.40`

### Change Chunk Size (1000 → 1500)
**File**: `fastapi_app_clean.py`  
**Line**: Search for `RecursiveCharacterTextSplitter`  
**Change**: `chunk_size=1500, chunk_overlap=300`

### Switch LLM Model
**File**: `utils/generator.py`  
**Line**: ~15  
**Change**: `model="gemini-1.5-pro"` (instead of gemini-2.0-flash-exp)

---

## 📞 Where to Get Help

| Topic | Resource |
|-------|----------|
| Setup | `SETUP.md` |
| Usage | `README.md` |
| Architecture | `ARCHITECTURE.md` |
| API docs | http://localhost:8000/docs |
| File checklist | `PROJECT_FILES.md` |

---

## 🎯 Example Session Flow

```
1. Start server → python run_fastapi.py
2. Open browser → http://localhost:8000
3. Initialize → Enter API key
4. Create client → "TestClient"
5. Upload docs → Select PDFs
6. Ask question → "What is the main topic?"
7. View answer → Check confidence + sources
8. Switch client → Create "Client2"
9. Repeat 5-7 for new client
10. Stop server → CTRL+C
```

---

## 💡 Pro Tips

✅ **Use descriptive client names**: `ACME_Q1_2024` better than `client1`  
✅ **Upload related docs together**: Q1 + Q2 reports for comparisons  
✅ **Check console during upload**: Shows progress + errors  
✅ **Try broad questions first**: "What is this about?" before specific queries  
✅ **Exact numbers matter**: System preserves "4,538" not "~4,500"  
✅ **High confidence + "no info"**: Good answer, not failure  

---

## 🔒 Security Reminders

⚠️ **Never commit API key** to git  
⚠️ **Add `.env` to `.gitignore`** if used  
⚠️ **Client data not encrypted** at rest - use disk encryption  
⚠️ **No authentication** - add nginx reverse proxy for production  
⚠️ **One user at a time** - not multi-user ready  

---

**Print this page for quick reference!**

*Last Updated: November 2025*

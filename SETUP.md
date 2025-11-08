# Mini-RAG Setup Guide

Complete step-by-step instructions for setting up and running the Mini-RAG system.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Google API Key Setup](#google-api-key-setup)
4. [First-Time Configuration](#first-time-configuration)
5. [Verification](#verification)
6. [Common Issues](#common-issues)

---

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)
- **Python**: 3.9 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for application + 200MB per client
- **Internet**: Required for Google API calls

### Check Python Version
```bash
python --version
# Should show: Python 3.9.x or higher

# If not installed, download from: https://www.python.org/downloads/
```

---

## Installation

### Step 1: Download Project

```bash
# Option A: Git clone
git clone <your-repository-url>
cd Mini-RAG

# Option B: Download ZIP
# Extract to desired folder, then:
cd path/to/Mini-RAG
```

### Step 2: Create Virtual Environment (Recommended)

**Windows (PowerShell)**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\.venv\Scripts\Activate.ps1
```

**Linux/Mac**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` prefix in your terminal.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output**:
```
Collecting fastapi==0.104.1
Collecting uvicorn[standard]==0.24.0
Collecting chromadb==0.4.24
...
Successfully installed fastapi-0.104.1 uvicorn-0.24.0 chromadb-0.4.24 ...
```

**If you see errors**:
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Then retry
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -c "import fastapi, chromadb, google.generativeai; print('✅ All packages installed')"
```

Should output: `✅ All packages installed`

---

## Google API Key Setup

### Step 1: Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with Google account
3. Click **"Create API Key"**
4. Copy the key (starts with `AIza...`)

**Important**: 
- ✅ Free tier: 60 requests/minute (sufficient for this project)
- ✅ No credit card required
- ⚠️ Keep key secret (don't commit to GitHub)

### Step 2: Set Environment Variable

**Windows (PowerShell)** - Session-only:
```powershell
$env:GOOGLE_API_KEY="AIzaSyB1234567890abcdefghijklmnopqrstuv"

# Verify it's set
echo $env:GOOGLE_API_KEY
```

**Windows (PowerShell)** - Permanent:
```powershell
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'AIzaSyB1234567890abcdefghijklmnopqrstuv', 'User')

# Restart PowerShell, then verify:
echo $env:GOOGLE_API_KEY
```

**Linux/Mac** - Session-only:
```bash
export GOOGLE_API_KEY="AIzaSyB1234567890abcdefghijklmnopqrstuv"

# Verify
echo $GOOGLE_API_KEY
```

**Linux/Mac** - Permanent:
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export GOOGLE_API_KEY="AIzaSyB1234567890abcdefghijklmnopqrstuv"' >> ~/.bashrc

# Reload
source ~/.bashrc

# Verify
echo $GOOGLE_API_KEY
```

### Alternative: .env File (Not Recommended for Security)

Create `.env` file in project root:
```
GOOGLE_API_KEY=AIzaSyB1234567890abcdefghijklmnopqrstuv
```

**Add to .gitignore**:
```bash
echo ".env" >> .gitignore
```

---

## First-Time Configuration

### Step 1: Start the Server

```bash
python run_fastapi.py
```

**Expected output**:
```
✅ All requirements satisfied
✅ Directories created: ./clients/, ./knowledge_base/
✅ Google API key configured
Starting Mini-RAG FastAPI server...
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**If you see errors**, see [Common Issues](#common-issues) below.

### Step 2: Open Web Interface

1. Open browser
2. Navigate to: **http://localhost:8000**
3. You should see the Mini-RAG interface

### Step 3: Initialize System (First Time Only)

1. Click **"Initialize System"** button
2. A prompt will ask for Google API key
3. Paste your key (starts with `AIza...`)
4. Click **"Initialize"**
5. Should see: ✅ "System initialized successfully"

**Note**: If you set environment variable, you can skip step 2-3 (system auto-detects).

### Step 4: Create Your First Client

1. In **Client Management** section, enter client name: `TestClient`
2. Click **"Set Client"**
3. Should see: ✅ "Switched to client: TestClient"
4. Database created at: `./clients/TestClient/chroma_db/`

### Step 5: Upload Test Document

**Option A: Use Sample Document**

Create `test.txt` with this content:
```
Banking Sector Report - Q1 2024

Total FDIC-insured institutions: 4,538 as of March 31, 2024.
Net interest margin: 3.2%
Total assets: $23.5 trillion
```

**Option B: Use Your Own PDF**

Any PDF file works (financial reports, articles, documentation).

**Upload Steps**:
1. Click **"Choose Files"**
2. Select `test.txt` or your PDF
3. Click **"Upload"**
4. Wait for processing (console shows progress)
5. Should see: ✅ "Uploaded 1 file, created X chunks"

### Step 6: Ask Your First Question

1. In question box, type: `What is the total number of FDIC-insured institutions?`
2. Click **"Ask Question"**
3. Wait 2-3 seconds
4. Should see:
   - **Answer**: "The total number of FDIC-insured institutions is 4,538 as of March 31, 2024."
   - **Confidence**: ~85%
   - **Sources**: test.txt with high relevance

**Congratulations!** 🎉 Your Mini-RAG system is working.

---

## Verification

### Check 1: System Status

Click **"Check Status"** button, should show:
```
✅ System initialized
📁 Documents: 1
👤 Current client: TestClient
📋 Available clients: TestClient
```

### Check 2: Client Database Files

**Windows**:
```powershell
ls .\clients\TestClient\chroma_db\
```

**Linux/Mac**:
```bash
ls ./clients/TestClient/chroma_db/
```

Should see:
- `chroma.sqlite3` (database file)
- `<uuid>` folder (vector index)

### Check 3: API Documentation

Visit: http://localhost:8000/docs

Should see interactive API documentation (Swagger UI).

---

## Common Issues

### Issue 1: "ModuleNotFoundError: No module named 'fastapi'"

**Cause**: Dependencies not installed or wrong Python environment

**Fix**:
```bash
# Make sure virtual environment is activated
# Windows:
.\.venv\Scripts\Activate.ps1

# Linux/Mac:
source .venv/bin/activate

# Then reinstall
pip install -r requirements.txt
```

---

### Issue 2: "Google API key not configured"

**Cause**: Environment variable not set

**Fix**:
```bash
# Windows PowerShell:
$env:GOOGLE_API_KEY="your-key-here"

# Linux/Mac:
export GOOGLE_API_KEY="your-key-here"

# Verify:
echo $env:GOOGLE_API_KEY   # Windows
echo $GOOGLE_API_KEY        # Linux/Mac
```

---

### Issue 3: Server won't start - "Address already in use"

**Cause**: Port 8000 is already in use

**Fix Option 1** - Stop other process:
```bash
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

**Fix Option 2** - Use different port:

Edit `run_fastapi.py`, change:
```python
uvicorn.run("fastapi_app_clean:app", host="0.0.0.0", port=8001, ...)
```

Then access: http://localhost:8001

---

### Issue 4: Google API 500 errors during upload

**Cause**: Google API rate limiting or temporary issues

**Fix**: 
- ✅ **Normal behavior** - System retries automatically (5 attempts)
- ✅ Watch console for: "⚠️ API error (attempt 1/5). Retrying in 3s..."
- ✅ Success rate typically 98%+ after retries
- ⚠️ If all retries fail, wait 60 seconds and try again

**Console output**:
```
✅ Embedded 10/182 chunks (Success: 100.0%)
⚠️  API error (attempt 1/5). Retrying in 3s...
✅ Embedded 20/182 chunks (Success: 95.0%)
✅ Embedded 30/182 chunks (Success: 98.3%)
...
✅ Embedded 182/182 chunks (Success: 98.9%)
```

---

### Issue 5: Empty answer returned

**Symptoms**: Answer section is blank, no error shown

**Possible Causes & Fixes**:

1. **No documents uploaded**
   - Fix: Upload documents first, check "Documents: X" in status

2. **Question doesn't match documents**
   - Fix: Try broader question like "What is this document about?"

3. **Gemini API error**
   - Fix: Check console for error messages, verify API key is valid

4. **Console shows "Warning: Answer became empty after cleaning"**
   - Fix: This is logged, answer should still appear (fallback enabled)

---

### Issue 6: Low relevance scores (< 30%)

**Cause**: Documents don't contain answer to question

**Fix**:
- ✅ Try broader questions
- ✅ Upload more relevant documents
- ✅ Check uploaded files actually contain text (not scanned images)
- ✅ For PDFs: Ensure text is selectable (not image-based PDFs)

---

### Issue 7: "Cannot read properties of undefined" in browser console

**Cause**: JavaScript error, usually from old cached files

**Fix**:
```
Hard refresh browser:
- Windows: Ctrl + Shift + R
- Mac: Cmd + Shift + R
```

---

### Issue 8: Python version too old

**Symptoms**: `SyntaxError` or `ImportError` related to type hints

**Fix**:
```bash
# Check version
python --version

# If < 3.9, download new version from:
# https://www.python.org/downloads/

# Then create new virtual environment with new Python
python3.11 -m venv .venv
```

---

## Next Steps

1. ✅ **Test with your documents**: Upload your own PDFs
2. ✅ **Try comparative questions**: Upload Q1 and Q2 reports, ask "What changed?"
3. ✅ **Create multiple clients**: Organize documents by project/client
4. 📖 **Read ARCHITECTURE.md**: Understand system internals
5. 🔧 **Customize**: See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for configuration tweaks

---

## Getting Help

- **Quick fixes**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Console output**: Check terminal for error messages
- **API docs**: http://localhost:8000/docs
- **File checklist**: [PROJECT_FILES.md](PROJECT_FILES.md)

---

**Setup complete!** 🚀 You're ready to use Mini-RAG.

*Last Updated: November 2025*

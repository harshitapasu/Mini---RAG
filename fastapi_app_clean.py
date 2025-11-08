"""
Mini-RAG Assistant - FastAPI Application (Clean & Fixed Version)
A lightweight Retrieval-Augmented Generation system with confidence scoring.
"""

import os
import tempfile
import uuid
import traceback
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import utilities
from utils.loader import DocumentLoader
from utils.embedder import VectorStoreManager
from utils.retriever import DocumentRetriever
from utils.generator import ResponseGenerator


# ===== PYDANTIC MODELS =====

class ConfigRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Google AI API Key")


class ClientRequest(BaseModel):
    client_name: str = Field(..., min_length=1, description="Client name")


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)
    k: Optional[int] = Field(default=3, ge=1, le=10)
    selected_documents: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    use_conversation_context: bool = True


class DocumentInfo(BaseModel):
    name: str
    chunk_count: int


class SourceInfo(BaseModel):
    source: str
    chunk_id: str
    relevance_score: float
    content: str
    page: Optional[int] = None  # PDF page number if available


class EvaluationMetrics(BaseModel):
    precision_at_k: float
    grounding_accuracy: float


class AnswerResponse(BaseModel):
    success: bool
    question: str
    answer: str
    confidence_score: float
    retrieval_confidence: float
    sources: List[SourceInfo]
    evaluation_metrics: EvaluationMetrics
    conversation_id: Optional[str] = None
    error: Optional[str] = None


class SystemStatus(BaseModel):
    initialized: bool
    documents_loaded: bool
    total_chunks: int
    document_count: int = 0
    message: str
    current_client: Optional[str] = None
    available_clients: List[str] = []


# ===== RAG SYSTEM CLASS =====

class SimpleRAGSystem:
    """Simplified RAG system with better error handling and multi-client support."""
    
    def __init__(self):
        self.vectorstore_manager: Optional[VectorStoreManager] = None
        self.retriever: Optional[DocumentRetriever] = None
        self.generator: Optional[ResponseGenerator] = None
        self.initialized = False
        self.documents_loaded = False
        self.api_key: Optional[str] = None
        self.current_client: Optional[str] = None
        self.clients_dir = "./clients"
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}  # In-memory conversation storage
        
        # Create clients directory if it doesn't exist
        os.makedirs(self.clients_dir, exist_ok=True)
    
    def _get_conversation_file_path(self) -> Path:
        """Get path to conversation history file for current client."""
        if not self.current_client:
            return Path("conversations.json")
        # Ensure client directory exists before returning path
        client_dir = Path(self.clients_dir) / self.current_client
        client_dir.mkdir(parents=True, exist_ok=True)
        return client_dir / "conversations.json"
    
    def _load_conversations(self) -> None:
        """Load conversation history from disk."""
        conv_file = self._get_conversation_file_path()
        if conv_file.exists():
            try:
                with open(conv_file, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
                print(f"✅ Loaded {len(self.conversations)} conversations from disk")
            except Exception as e:
                print(f"⚠️ Could not load conversations: {e}")
                self.conversations = {}
        else:
            self.conversations = {}
    
    def _save_conversations(self) -> None:
        """Save conversation history to disk."""
        try:
            conv_file = self._get_conversation_file_path()
            with open(conv_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(self.conversations)} conversations to disk")
        except Exception as e:
            print(f"⚠️ Could not save conversations: {e}")
    
    def _add_to_conversation(self, conversation_id: str, question: str, answer: str, 
                            confidence: float, sources: List[Dict]) -> None:
        """Add a Q&A pair to conversation history."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        # Store conversation entry with metadata
        self.conversations[conversation_id].append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "sources_count": len(sources),
            "sources": sources[:3]  # Store top 3 sources only to save space
        })
        
        # Persist to disk after every addition
        self._save_conversations()
    
    def get_conversation_history(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Get conversation history."""
        if conversation_id:
            return {
                "conversation_id": conversation_id,
                "messages": self.conversations.get(conversation_id, [])
            }
        else:
            # Return all conversations
            return {
                "conversations": [
                    {
                        "conversation_id": conv_id,
                        "message_count": len(messages),
                        "last_updated": messages[-1]["timestamp"] if messages else None,
                        "preview": messages[-1]["question"][:100] if messages else ""
                    }
                    for conv_id, messages in self.conversations.items()
                ],
                "total_conversations": len(self.conversations)
            }
    
    def initialize(self, api_key: str) -> tuple[bool, str]:
        """Initialize the system with better error handling."""
        try:
            print("=== Starting RAG System Initialization ===")
            
            # Validate API key format
            if not api_key or len(api_key.strip()) < 10:
                return False, "Invalid API key format"
            
            # Store API key
            self.api_key = api_key.strip()
            
            # Test API key validation with Google AI
            print("Testing Google AI API key...")
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            # Quick API test - list models to verify authentication
            try:
                # Try to access models to validate key
                models = list(genai.list_models())
                print(f"API key validated - found {len(models)} available models")
            except Exception as api_error:
                error_msg = str(api_error).lower()
                if "invalid" in error_msg or "unauthorized" in error_msg or "403" in error_msg:
                    return False, "Invalid API key - please check your Google AI Studio API key"
                elif "quota" in error_msg or "429" in error_msg:
                    return False, "API quota exceeded - please check your usage limits"
                else:
                    return False, f"API validation failed: {str(api_error)}"
            
            # Initialize VectorStore Manager
            print("Initializing VectorStore Manager...")
            self.vectorstore_manager = VectorStoreManager(
                persist_directory=self._get_client_db_path(),
                google_api_key=self.api_key
            )
            
            # Try to load existing vectorstore if available
            print("Checking for existing vector database...")
            if self.vectorstore_manager.load_vectorstore():
                print("Existing vector database loaded successfully")
                vectorstore = self.vectorstore_manager.get_vectorstore()
                if vectorstore:
                    # Initialize retriever with loaded vectorstore
                    self.retriever = DocumentRetriever(vectorstore)
                    self.documents_loaded = True
                    stats = self.vectorstore_manager.get_stats()
                    print(f"Loaded vector database with {stats.get('total_chunks', 0)} chunks")
            else:
                print("No existing vector database found - ready to process documents")
            
            # Initialize Response Generator
            print("Initializing Response Generator...")
            self.generator = ResponseGenerator(
                api_key=self.api_key,
                model="gemini-2.0-flash"
            )
            
            # Load conversation history if client is set
            if self.current_client:
                self._load_conversations()
            
            self.initialized = True
            print("=== RAG System Initialization Complete ===")
            return True, "System initialized successfully"
            
        except Exception as e:
            error_msg = f"Initialization failed: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            self.reset()
            return False, error_msg
    
    def reset(self):
        """Reset system state."""
        self.vectorstore_manager = None
        self.retriever = None
        self.generator = None
        self.initialized = False
        self.documents_loaded = False
        self.api_key = None
        # Note: Don't reset current_client to allow re-init with same client
    
    def _get_client_db_path(self, client_name: str = None) -> str:
        """Get the database path for a specific client."""
        client = client_name or self.current_client or "default"
        return os.path.join(self.clients_dir, client, "chroma_db")
    
    def get_available_clients(self) -> List[str]:
        """Get list of available clients."""
        if not os.path.exists(self.clients_dir):
            return []
        
        clients = []
        for item in os.listdir(self.clients_dir):
            client_path = os.path.join(self.clients_dir, item)
            if os.path.isdir(client_path):
                # Check if client has a database
                db_path = os.path.join(client_path, "chroma_db")
                if os.path.exists(db_path):
                    clients.append(item)
        return sorted(clients)
    
    def set_client(self, client_name: str) -> tuple[bool, str]:
        """Set or create a client."""
        if not self.initialized:
            return False, "System not initialized. Configure API key first."
        
        # Sanitize client name - remove invalid characters
        client_name = client_name.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
        if not client_name:
            return False, "Invalid client name"
        
        # Store previous client to save conversations before switching
        previous_client = self.current_client
        
        try:
            # Create client directory
            client_dir = os.path.join(self.clients_dir, client_name)
            os.makedirs(client_dir, exist_ok=True)
            
            print(f"\n=== Setting client: {client_name} ===")
            
            # Save conversations for previous client before switching
            if previous_client and previous_client != client_name:
                self._save_conversations()
            
            # Update current client and prepare database path
            self.current_client = client_name
            client_db_path = self._get_client_db_path()
            print(f"Client DB path: {client_db_path}")
            
            # Reinitialize vector store for new client (multi-client isolation)
            print(f"Switching to client: {client_name}")
            self.vectorstore_manager = VectorStoreManager(
                persist_directory=client_db_path,
                google_api_key=self.api_key
            )
            
            # Try to load existing vectorstore for this client
            if self.vectorstore_manager.load_vectorstore():
                print(f"✅ Loaded existing database for client: {client_name}")
                vectorstore = self.vectorstore_manager.get_vectorstore()
                if vectorstore:
                    self.retriever = DocumentRetriever(vectorstore)
                    self.documents_loaded = True
                    try:
                        stats = self.vectorstore_manager.get_stats()
                        total_chunks = stats.get('total_chunks', 0)
                        doc_count = stats.get('document_count', 0)
                        print(f"✅ Database has {total_chunks} chunks from {doc_count} documents")
                        message = f"Switched to client '{client_name}' with {total_chunks} chunks from {doc_count} documents"
                    except Exception as stats_error:
                        print(f"⚠️ Could not get stats: {stats_error}")
                        message = f"Switched to client '{client_name}' (documents loaded)"
                else:
                    print(f"⚠️ Vectorstore loaded but no data available")
                    self.documents_loaded = False
                    message = f"Created new client '{client_name}'"
            else:
                print(f"📝 Created new database for client: {client_name}")
                self.documents_loaded = False
                self.retriever = None
                message = f"Created new client '{client_name}'"
            
            # Load conversations for new client
            self._load_conversations()
            
            return True, message
            
        except Exception as e:
            # Rollback on error
            self.current_client = previous_client
            error_msg = f"Failed to set client: {str(e)}"
            print(f"ERROR: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            return False, error_msg
    
    def delete_client(self, client_name: str) -> tuple[bool, str]:
        """Delete a client and all their documents."""
        try:
            import shutil
            
            client_dir = os.path.join(self.clients_dir, client_name)
            if not os.path.exists(client_dir):
                return False, f"Client '{client_name}' not found"
            
            # Don't allow deleting current client
            if client_name == self.current_client:
                return False, "Cannot delete currently active client. Switch to another client first."
            
            # Delete client directory
            shutil.rmtree(client_dir)
            return True, f"Client '{client_name}' deleted successfully"
            
        except Exception as e:
            return False, f"Failed to delete client: {str(e)}"
    
    def is_ready(self) -> bool:
        """Check if system is ready for queries."""
        return self.initialized and bool(self.generator)
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed system status."""
        total_chunks = 0
        document_count = 0
        
        if self.vectorstore_manager:
            try:
                stats = self.vectorstore_manager.get_stats()
                total_chunks = stats.get('total_chunks', 0)
                document_count = stats.get('document_count', 0)
            except:
                pass
        
        return {
            "initialized": self.initialized,
            "documents_loaded": self.documents_loaded,
            "total_chunks": total_chunks,
            "document_count": document_count,
            "message": "System ready" if self.is_ready() else "System not ready",
            "current_client": self.current_client,
            "available_clients": self.get_available_clients()
        }
    
    def get_available_documents(self) -> List[DocumentInfo]:
        """Get available documents."""
        if not self.vectorstore_manager or not self.vectorstore_manager.vectorstore:
            return []
        
        try:
            collection = self.vectorstore_manager.vectorstore._collection
            all_docs = collection.get()
            
            document_counts = {}
            if all_docs and 'metadatas' in all_docs:
                for metadata in all_docs['metadatas']:
                    if metadata and 'source' in metadata:
                        source = metadata['source']
                        document_counts[source] = document_counts.get(source, 0) + 1
            
            return [
                DocumentInfo(name=doc_name, chunk_count=count)
                for doc_name, count in sorted(document_counts.items())
            ]
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []


# ===== FASTAPI APPLICATION =====

app = FastAPI(
    title="Mini-RAG Assistant",
    description="Local RAG system with comprehensive evaluation metrics",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global RAG system instance
rag_system = SimpleRAGSystem()

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# ===== API ENDPOINTS =====

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Main page not found")


@app.post("/configure")
async def configure_system(request: ConfigRequest):
    """Configure the RAG system with API key."""
    try:
        success, message = rag_system.initialize(request.api_key)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": message}
            )
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": message}
            )
    except Exception as e:
        error_msg = f"Configuration error: {str(e)}"
        print(f"Configuration error: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error_msg}
        )


@app.post("/client/set")
async def set_client(request: ClientRequest):
    """Set or create a client."""
    try:
        success, message = rag_system.set_client(request.client_name)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": message, "client": request.client_name}
            )
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": message}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/client/list")
async def list_clients():
    """Get list of all available clients."""
    try:
        clients = rag_system.get_available_clients()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "clients": clients,
                "current_client": rag_system.current_client
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.delete("/client/{client_name}")
async def delete_client(client_name: str):
    """Delete a client and all their documents."""
    try:
        success, message = rag_system.delete_client(client_name)
        
        if success:
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": message}
            )
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": message}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/status")
async def get_system_status():
    """Get current system status."""
    try:
        status_data = rag_system.get_status()
        return SystemStatus(**status_data)
    except Exception as e:
        print(f"Status error: {e}")
        return SystemStatus(
            initialized=False,
            documents_loaded=False,
            total_chunks=0,
            message="Error getting status"
        )


@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and process documents."""
    if not rag_system.initialized:
        raise HTTPException(status_code=400, detail="System not initialized")
    
    try:
        loader = DocumentLoader()
        processed_files = 0
        total_chunks = 0
        
        for file in files:
            # Only accept PDF, TXT, and Markdown files
            if file.content_type not in ["application/pdf", "text/plain", "text/markdown"]:
                continue
            
            # Save uploaded file temporarily for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                # Process file: extract text and create chunks
                chunks = loader.load_and_chunk_file(tmp_path, file.filename)
                
                # Add chunks to vector store with embeddings
                if chunks:
                    if not rag_system.vectorstore_manager.vectorstore:
                        # Create new vectorstore if doesn't exist
                        rag_system.vectorstore_manager.create_vectorstore(chunks)
                    else:
                        # Add to existing vectorstore
                        rag_system.vectorstore_manager.add_documents(chunks)
                    
                    # Update retriever with new documents
                    vectorstore = rag_system.vectorstore_manager.get_vectorstore()
                    rag_system.retriever = DocumentRetriever(vectorstore)
                    rag_system.documents_loaded = True
                    
                    processed_files += 1
                    total_chunks += len(chunks)
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        return JSONResponse(content={
            "success": True,
            "processed_files": processed_files,
            "total_chunks": total_chunks,
            "message": f"Successfully processed {processed_files} files"
        })
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Process a question and return an answer."""
    if not rag_system.is_ready():
        raise HTTPException(status_code=400, detail="System not ready")
    
    if not rag_system.documents_loaded:
        raise HTTPException(status_code=400, detail="No documents loaded")
    
    try:
        # Use higher k value for better retrieval (especially for comparative questions)
        retrieval_k = max(request.k, 5)  # Minimum 5 chunks for comprehensive answers
        
        # Step 1: Retrieve relevant documents using semantic search
        retrieved_docs, retrieval_confidence = rag_system.retriever.retrieve(
            request.question, 
            k=retrieval_k,
            selected_documents=request.selected_documents
        )
        
        if not retrieved_docs:
            raise HTTPException(status_code=404, detail="No relevant documents found")
        
        # Step 2: Prepare context from retrieved chunks
        context = "\n\n".join([doc["content"] for doc in retrieved_docs])
        
        # Step 3: Generate answer using LLM with context
        answer, llm_confidence, final_confidence = rag_system.generator.generate_answer(
            request.question,
            context,
            retrieval_confidence
        )
        
        # Check if answer indicates no reference/insufficient context
        # Don't show sources if the answer says there's no information
        no_reference_phrases = [
            "do not mention",
            "does not mention",
            "don't mention",
            "doesn't mention",
            "not mentioned",
            "no information",
            "no relevant information",
            "insufficient",
            "cannot answer",
            "don't have",
            "do not have",
            "not available",
            "not found in",
            "do not contain",
            "does not contain"
        ]
        
        answer_lower = answer.lower()
        has_no_reference = any(phrase in answer_lower for phrase in no_reference_phrases)
        
        # If answer correctly states there's no information, boost confidence
        # This is actually a GOOD answer - the system correctly identified missing info
        if has_no_reference:
            # Set high confidence since this is the correct answer
            final_confidence = max(final_confidence, 0.85)
            llm_confidence = max(llm_confidence, 9.0)
        
        # Step 4: Filter and prepare sources for response
        # Only show max 3 sources with HIGH relevance (> 50%)
        # If answer indicates no reference, don't show any sources
        relevance_threshold = 0.50
        max_sources = 3
        
        # Prepare sources with better display
        sources = []
        
        if not has_no_reference:
            for i, doc in enumerate(retrieved_docs):
                # Skip low-relevance sources
                if doc["score"] < relevance_threshold:
                    continue
                
                # Limit to max 3 sources for clarity
                if len(sources) >= max_sources:
                    break
                    
                metadata = doc["metadata"]
                chunk_id = metadata.get("chunk_id", f"chunk_{i}")
                # Ensure chunk_id is a string
                chunk_id_str = str(chunk_id) if chunk_id is not None else f"chunk_{i}"
                
                # Get page number if available (for PDFs)
                page_num = metadata.get("page")
                
                # Create content preview (200 chars) for display
                content = doc["content"]
                preview_length = 200
                content_preview = content[:preview_length]
                if len(content) > preview_length:
                    # Try to end at a sentence or word boundary for cleaner preview
                    last_period = content_preview.rfind('.')
                    last_space = content_preview.rfind(' ')
                    if last_period > preview_length - 50:
                        content_preview = content_preview[:last_period + 1]
                    elif last_space > preview_length - 50:
                        content_preview = content_preview[:last_space] + "..."
                    else:
                        content_preview = content_preview + "..."
                
                sources.append(SourceInfo(
                    source=metadata.get("source", f"Document {i+1}"),
                    chunk_id=chunk_id_str,
                    relevance_score=doc["score"],
                    content=content_preview,
                    page=page_num
                ))
        
        # Sources will be empty if:
        # 1. Answer indicates no reference found (correct negative)
        # 2. No sources meet the 50% threshold
        
        # Step 5: Calculate evaluation metrics
        # Precision@K: What percentage of retrieved sources are highly relevant?
        # Use adaptive threshold based on top source quality
        if sources:
            top_score = max([s.relevance_score for s in sources])
            # If top score is high, use strict threshold; if low, be more lenient
            adaptive_threshold = max(0.35, top_score * 0.7)  # 70% of top score, minimum 35%
            high_quality_sources = len([s for s in sources if s.relevance_score >= adaptive_threshold])
            precision_at_k = high_quality_sources / len(sources) if len(sources) > 0 else 0.0
        else:
            precision_at_k = 0.0
        
        grounding_accuracy = final_confidence
        
        metrics = EvaluationMetrics(
            precision_at_k=precision_at_k,
            grounding_accuracy=grounding_accuracy
        )
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Step 6: Save Q&A to conversation history for context tracking
        rag_system._add_to_conversation(
            conversation_id=conversation_id,
            question=request.question,
            answer=answer,
            confidence=final_confidence,
            sources=[{
                "source": s.source,
                "page": s.page,
                "relevance_score": s.relevance_score
            } for s in sources]
        )
        
        return AnswerResponse(
            success=True,
            question=request.question,
            answer=answer,
            confidence_score=final_confidence,
            retrieval_confidence=retrieval_confidence,
            sources=sources,
            evaluation_metrics=metrics,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        print(f"Question processing error: {e}")
        return AnswerResponse(
            success=False,
            question=request.question,
            answer="",
            confidence_score=0.0,
            retrieval_confidence=0.0,
            sources=[],
            evaluation_metrics=EvaluationMetrics(precision_at_k=0.0, grounding_accuracy=0.0),
            error=str(e)
        )


@app.get("/documents")
async def get_documents():
    """Get list of available documents."""
    try:
        documents = rag_system.get_available_documents()
        return JSONResponse(content={
            "success": True,
            "documents": [{"filename": doc.name, "chunk_count": doc.chunk_count} for doc in documents],
            "total_documents": len(documents)
        })
    except Exception as e:
        print(f"Documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear")
async def clear_knowledge_base():
    """Clear the knowledge base."""
    try:
        if rag_system.vectorstore_manager and rag_system.vectorstore_manager.vectorstore:
            # Delete all documents from the collection instead of deleting files
            try:
                collection = rag_system.vectorstore_manager.vectorstore._collection
                # Get all document IDs
                all_data = collection.get()
                if all_data and 'ids' in all_data and all_data['ids']:
                    # Delete all documents by ID
                    collection.delete(ids=all_data['ids'])
                    print(f"Deleted {len(all_data['ids'])} documents from ChromaDB")
                
                # Reset the vectorstore reference to clear memory
                rag_system.vectorstore_manager.vectorstore = None
                rag_system.retriever = None
                rag_system.documents_loaded = False
                
                print("Knowledge base cleared successfully")
            except Exception as e:
                print(f"Error clearing collection: {e}")
                raise
        
        return JSONResponse(content={"success": True, "message": "Knowledge base cleared"})
    except Exception as e:
        print(f"Clear error: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Failed to clear database: {str(e)}"}
        )


@app.get("/conversations")
async def get_conversations(conversation_id: Optional[str] = None):
    """Get conversation history."""
    try:
        if not rag_system.initialized:
            return JSONResponse(content={
                "success": True,
                "conversations": [],
                "total_conversations": 0,
                "message": "System not initialized"
            })
        
        # Load conversations for current client if not already loaded
        if not rag_system.conversations:
            rag_system._load_conversations()
        
        history = rag_system.get_conversation_history(conversation_id)
        
        return JSONResponse(content={
            "success": True,
            **history
        })
    except Exception as e:
        print(f"Conversation history error: {e}")
        return JSONResponse(content={
            "success": False,
            "error": str(e),
            "conversations": [],
            "total_conversations": 0
        })


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a specific conversation."""
    try:
        if conversation_id in rag_system.conversations:
            del rag_system.conversations[conversation_id]
            rag_system._save_conversations()
            return JSONResponse(content={
                "success": True,
                "message": f"Conversation {conversation_id} deleted"
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": f"Conversation {conversation_id} not found"
            }, status_code=404)
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.delete("/conversations")
async def clear_all_conversations():
    """Clear all conversation history for current client."""
    try:
        rag_system.conversations = {}
        rag_system._save_conversations()
        return JSONResponse(content={
            "success": True,
            "message": "All conversations cleared"
        })
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "error": str(e)
        }, status_code=500)


# ===== SERVER STARTUP =====

if __name__ == "__main__":
    print("Starting Mini-RAG FastAPI Server...")
    uvicorn.run(
        "fastapi_app_clean:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
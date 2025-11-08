"""
Embedder Module
Handles embedding generation and vector store management using Chroma with Google embeddings.
"""

import os
import time
from typing import List, Tuple, Optional
import google.generativeai as genai
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings


class GoogleGenerativeAIEmbeddings(Embeddings):
    """Custom embeddings class using Google's Generative AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Google embeddings."""
        if api_key:
            genai.configure(api_key=api_key)
        elif os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents with retry logic and progress tracking."""
        embeddings = []
        total = len(texts)
        failed_count = 0
        
        for i, text in enumerate(texts, 1):
            embedding = self._embed_with_retry(text, "retrieval_document")
            embeddings.append(embedding)
            
            # Track failures (zero embeddings)
            if embedding == [0.0] * 768:
                failed_count += 1
            
            # Progress indicator every 10 chunks
            if i % 10 == 0 or i == total:
                success_rate = ((i - failed_count) / i) * 100
                print(f"📊 Progress: {i}/{total} chunks embedded ({success_rate:.1f}% success)")
            
            # Add delay to avoid rate limiting (increased for stability)
            time.sleep(0.2)
        
        if failed_count > 0:
            print(f"⚠️  {failed_count}/{total} chunks failed to embed (using fallback embeddings)")
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a query with retry logic."""
        return self._embed_with_retry(text, "retrieval_query")
    
    def _embed_with_retry(self, text: str, task_type: str, max_retries: int = 5) -> List[float]:
        """Embed text with retry logic for rate limiting and server errors."""
        for attempt in range(max_retries):
            try:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type=task_type
                )
                return result["embedding"]
            except Exception as e:
                error_str = str(e)
                print(f"Error embedding text (attempt {attempt + 1}/{max_retries}): {error_str}")
                
                # Check if it's a retryable error
                is_rate_limit = "429" in error_str or "quota" in error_str.lower()
                is_server_error = "500" in error_str or "503" in error_str or "internal error" in error_str.lower()
                is_retryable = is_rate_limit or is_server_error
                
                if is_retryable and attempt < max_retries - 1:
                    # Exponential backoff: 3, 6, 12, 24 seconds
                    wait_time = (2 ** attempt) * 3
                    if is_server_error:
                        print(f"⚠️  Google API internal error. Retrying in {wait_time} seconds...")
                    else:
                        print(f"⚠️  Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                elif attempt == max_retries - 1:
                    print(f"❌ Max retries ({max_retries}) reached. Skipping this chunk.")
                    return [0.0] * 768
                else:
                    # Non-retryable error
                    print(f"❌ Non-retryable error. Skipping this chunk.")
                    return [0.0] * 768
        
        return [0.0] * 768


class VectorStoreManager:
    """Manage embeddings and Chroma vector store."""
    
    def __init__(self, 
                 persist_directory: str = "./chroma_db",
                 google_api_key: Optional[str] = None):
        """
        Initialize the vector store manager.
        
        Args:
            persist_directory: Directory to persist Chroma database
            google_api_key: Google AI API key for embeddings
        """
        self.persist_directory = persist_directory
        
        # Initialize Google embeddings
        print("Initializing Google AI embeddings...")
        self.embeddings = GoogleGenerativeAIEmbeddings(api_key=google_api_key)
        print("Google AI embeddings initialized!")
        
        self.vectorstore = None
    
    def create_vectorstore(self, chunks: List[Tuple[str, dict]]) -> None:
        """
        Create a new Chroma vector store from document chunks.
        
        Args:
            chunks: List of (chunk_text, metadata) tuples
        """
        if not chunks:
            print("Warning: No chunks provided to create vector store")
            return
        
        # Convert chunks to LangChain Document objects
        documents = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in chunks
        ]
        
        print(f"Creating vector store with {len(documents)} chunks...")
        print(f"⏳ This may take a few minutes for large document sets...")
        
        try:
            # Create Chroma vector store with persistence
            self.vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Persist to disk
            self.vectorstore.persist()
            print(f"✅ Vector store created and persisted to {self.persist_directory}")
        except Exception as e:
            print(f"❌ Error creating vector store: {str(e)}")
            print(f"💡 Tip: If you see '500 internal error', wait a few minutes and try again.")
            print(f"💡 Google AI API may be temporarily unavailable or rate limited.")
            raise
    
    def load_vectorstore(self) -> bool:
        """
        Load an existing Chroma vector store from disk.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.persist_directory):
                print(f"No existing vector store found at {self.persist_directory}")
                return False
            
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            print(f"Vector store loaded from {self.persist_directory}")
            return True
        except Exception as e:
            print(f"Error loading vector store: {str(e)}")
            return False
    
    def add_documents(self, chunks: List[Tuple[str, dict]]) -> None:
        """
        Add new documents to an existing vector store.
        
        Args:
            chunks: List of (chunk_text, metadata) tuples
        """
        if not chunks:
            print("Warning: No chunks provided to add")
            return
        
        documents = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in chunks
        ]
        
        if self.vectorstore is None:
            print("No vector store exists. Creating new one...")
            self.create_vectorstore(chunks)
        else:
            print(f"Adding {len(documents)} chunks to existing vector store...")
            print(f"⏳ This may take a few minutes for large document sets...")
            
            try:
                self.vectorstore.add_documents(documents)
                self.vectorstore.persist()
                print("✅ Documents added and persisted successfully")
            except Exception as e:
                print(f"❌ Error adding documents: {str(e)}")
                print(f"💡 Tip: If you see '500 internal error', the Google AI API is temporarily unavailable.")
                print(f"💡 Wait 2-3 minutes and try uploading again.")
                raise
    
    def get_vectorstore(self):
        """
        Get the current vector store instance.
        
        Returns:
            Chroma vector store instance or None
        """
        return self.vectorstore
    
    def clear_vectorstore(self) -> None:
        """Delete the persisted vector store."""
        import shutil
        
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
            print(f"Vector store cleared from {self.persist_directory}")
        
        self.vectorstore = None
    
    def get_stats(self) -> dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with vector store statistics
        """
        if self.vectorstore is None:
            return {
                "total_chunks": 0,
                "document_count": 0,
                "exists": False
            }
        
        try:
            # Get collection info
            collection = self.vectorstore._collection
            count = collection.count()
            
            # Count unique documents
            all_docs = collection.get()
            document_count = 0
            if all_docs and 'metadatas' in all_docs:
                unique_sources = set()
                for metadata in all_docs['metadatas']:
                    if metadata and 'source' in metadata:
                        unique_sources.add(metadata['source'])
                document_count = len(unique_sources)
            
            return {
                "total_chunks": count,
                "document_count": document_count,
                "exists": True,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {
                "total_chunks": 0,
                "document_count": 0,
                "exists": False,
                "error": str(e)
            }
    
    def initialize_or_load(self, chunks: Optional[List[Tuple[str, dict]]] = None) -> bool:
        """
        Initialize vector store from chunks or load existing one.
        
        Args:
            chunks: Optional list of (chunk_text, metadata) tuples
            
        Returns:
            True if vector store is ready, False otherwise
        """
        # Try loading existing vector store first
        if self.load_vectorstore():
            # If new chunks provided, add them
            if chunks:
                self.add_documents(chunks)
            return True
        
        # If no existing store and chunks provided, create new one
        if chunks:
            self.create_vectorstore(chunks)
            return True
        
        print("No vector store available and no chunks provided")
        return False

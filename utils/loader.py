"""
Document Loader Module
Handles PDF and text file loading, parsing, and chunking.
"""

import os
from typing import List, Tuple
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter


class DocumentLoader:
    """Load and process PDF and text documents into chunks."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document loader.
        
        Args:
            chunk_size: Maximum size of each text chunk
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def load_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file using pdfplumber.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        # Add page marker to help with later extraction
                        text += f"[Page {page_num}] {page_text}\n"
        except Exception as e:
            print(f"Error loading PDF {file_path}: {str(e)}")
        return text
    
    def load_pdf_with_pages(self, file_path: str) -> List[Tuple[str, dict]]:
        """
        Extract text from PDF with page-aware chunking.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of (chunk_text, metadata) tuples with page information
        """
        source_name = os.path.basename(file_path)
        all_chunks = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        # Chunk each page separately to maintain page context
                        page_chunks = self.text_splitter.split_text(page_text)
                        
                        for chunk_idx, chunk in enumerate(page_chunks):
                            if chunk.strip():  # Skip empty chunks
                                metadata = {
                                    "source": source_name,
                                    "page": page_num,
                                    "chunk_id": f"{page_num}-{chunk_idx + 1}",
                                    "chunk_size": len(chunk)
                                }
                                all_chunks.append((chunk, metadata))
                                
        except Exception as e:
            print(f"Error loading PDF {file_path}: {str(e)}")
            # Fallback to regular loading
            return self.load_and_chunk_file(file_path)
        
        return all_chunks
    
    def load_text_file(self, file_path: str) -> str:
        """
        Load content from a text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Text content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading text file {file_path}: {str(e)}")
            return ""
    
    def load_document(self, file_path: str) -> str:
        """
        Load a document (PDF or text file).
        
        Args:
            file_path: Path to the document
            
        Returns:
            Extracted text content
        """
        if file_path.lower().endswith('.pdf'):
            return self.load_pdf(file_path)
        elif file_path.lower().endswith(('.txt', '.md')):
            return self.load_text_file(file_path)
        else:
            print(f"Unsupported file type: {file_path}")
            return ""
    
    def chunk_text(self, text: str, source_name: str) -> List[Tuple[str, dict]]:
        """
        Split text into chunks with metadata.
        
        Args:
            text: Text to be chunked
            source_name: Name of the source document
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        chunks = self.text_splitter.split_text(text)
        chunked_documents = []
        
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": source_name,
                "chunk_id": i,
                "chunk_size": len(chunk)
            }
            chunked_documents.append((chunk, metadata))
        
        return chunked_documents
    
    def process_document(self, file_path: str) -> List[Tuple[str, dict]]:
        """
        Complete pipeline: load document and chunk it.
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        source_name = os.path.basename(file_path)
        text = self.load_document(file_path)
        
        if not text.strip():
            print(f"Warning: No text extracted from {source_name}")
            return []
        
        return self.chunk_text(text, source_name)
    
    def process_directory(self, directory_path: str) -> List[Tuple[str, dict]]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory_path: Path to the directory containing documents
            
        Returns:
            List of all (chunk_text, metadata) tuples
        """
        all_chunks = []
        supported_extensions = ('.pdf', '.txt', '.md')
        
        if not os.path.exists(directory_path):
            print(f"Directory not found: {directory_path}")
            return []
        
        for filename in os.listdir(directory_path):
            if filename.lower().endswith(supported_extensions):
                file_path = os.path.join(directory_path, filename)
                print(f"Processing: {filename}")
                chunks = self.process_document(file_path)
                all_chunks.extend(chunks)
                print(f"  -> Generated {len(chunks)} chunks")
        
        return all_chunks
    
    def load_and_chunk_file(self, file_path: str, original_name: str = None) -> List[Tuple[str, dict]]:
        """
        Load and chunk a single file with specified original name.
        
        Args:
            file_path: Path to the file to process
            original_name: Original filename to use in metadata
            
        Returns:
            List of (chunk_text, metadata) tuples
        """
        source_name = original_name or os.path.basename(file_path)
        text = self.load_document(file_path)
        
        if not text.strip():
            print(f"Warning: No text extracted from {source_name}")
            return []
        
        return self.chunk_text(text, source_name)
    
    def process_uploaded_files(self, uploaded_files) -> List[Tuple[str, dict]]:
        """
        Process files uploaded through Streamlit.
        
        Args:
            uploaded_files: List of Streamlit UploadedFile objects
            
        Returns:
            List of all (chunk_text, metadata) tuples
        """
        all_chunks = []
        
        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name
            print(f"Processing uploaded file: {file_name}")
            
            # Save temporarily
            temp_path = os.path.join("knowledge_base", file_name)
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process the file
            chunks = self.process_document(temp_path)
            all_chunks.extend(chunks)
            print(f"  -> Generated {len(chunks)} chunks")
        
        return all_chunks

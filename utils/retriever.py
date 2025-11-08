"""
Retriever Module
Handles document retrieval with similarity search and confidence scoring.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np


class DocumentRetriever:
    """Retrieve relevant documents with confidence scoring."""
    
    def __init__(self, vectorstore):
        """
        Initialize the retriever.
        
        Args:
            vectorstore: Chroma vector store instance
        """
        self.vectorstore = vectorstore
    
    def retrieve(self, query: str, k: int = 5, selected_documents: Optional[List[str]] = None) -> Tuple[List[dict], float]:
        """
        Retrieve top-k most relevant documents with enhanced matching for comparative queries.
        
        This method implements intelligent retrieval that:
        - Detects comparative questions (e.g., "Q1 vs Q2", "first vs second")
        - Ensures representation from different time periods/documents
        - Prioritizes chunks with quantitative data
        
        Args:
            query: User's question
            k: Number of top documents to retrieve (default: 5)
            selected_documents: Optional list of specific documents to search in
            
        Returns:
            Tuple of (retrieved_documents, retrieval_confidence)
            - retrieved_documents: List of dicts with content, metadata, and score
            - retrieval_confidence: Float between 0 and 1
        """
        if self.vectorstore is None:
            print("Warning: No vector store available")
            return [], 0.0
        
        try:
            # Detect if this is a comparative query
            comparative_keywords = ['between', 'vs', 'versus', 'compare', 'compared', 'difference', 
                                   'changed', 'change', 'first and second', 'Q1 and Q2', 'quarter']
            is_comparative = any(keyword in query.lower() for keyword in comparative_keywords)
            
            # Search more chunks initially for better coverage
            search_k = k * 4 if is_comparative else k * 3
            
            if selected_documents:
                # Filter by selected documents using metadata
                broad_search_k = search_k * 3  
                results = self.vectorstore.similarity_search_with_score(query, k=broad_search_k)
                
                # Filter results by selected documents
                filtered_results = []
                for doc, score in results:
                    if doc.metadata.get('source') in selected_documents:
                        filtered_results.append((doc, score))
                results = filtered_results[:search_k]
            else:
                results = self.vectorstore.similarity_search_with_score(query, k=search_k)
            
            if not results:
                print("No results found for query")
                return [], 0.0
            
            # Re-rank results to boost chunks with quantitative content
            # Also filter out low-value chunks like table of contents
            re_ranked_results = []
            for doc, score in results:
                # Convert L2 distance to similarity score (0 to 1)
                similarity = np.exp(-score)
                
                content = doc.page_content
                content_lower = content.lower()
                
                # Filter out table of contents and other low-value content
                skip_patterns = [
                    'table of contents',
                    'contents\n',
                    'page number',
                    'chapter 1\n',
                    'chapter 2\n',
                    'section 1\n',
                    'section 2\n',
                    '...........',  # TOC dots
                    'copyright notice',
                    'all rights reserved',
                ]
                
                # Skip if content is just a table of contents or similar
                if any(pattern in content_lower for pattern in skip_patterns):
                    # Check if content is mostly just TOC (short with lots of page numbers)
                    word_count = len(content.split())
                    if word_count < 100:  # Short chunks are more likely to be TOC
                        continue
                
                # Boost score for chunks containing numbers/metrics
                has_numbers = any(char.isdigit() for char in content)
                has_percentages = '%' in content
                has_currency = '$' in content
                has_tables = 'TABLE' in content.upper() or '|' in content
                
                # Calculate boost factor
                boost = 1.0
                if has_numbers:
                    boost += 0.15  # 15% boost for numbers
                if has_percentages:
                    boost += 0.10  # 10% boost for percentages
                if has_currency:
                    boost += 0.08  # 8% boost for currency
                if has_tables:
                    boost += 0.12  # 12% boost for tables
                
                # For comparative queries, boost chunks from different sources
                if is_comparative:
                    # Prefer chunks with comparative/temporal keywords
                    temporal_words = ['quarter', 'Q1', 'Q2', 'Q3', 'Q4', 'year', 'period', 
                                    'change', 'increase', 'decrease', 'compared']
                    if any(word in content for word in temporal_words):
                        boost += 0.10
                
                # Apply boost (cap at 1.5x)
                boosted_similarity = min(similarity * boost, 1.0)
                
                re_ranked_results.append((doc, score, boosted_similarity))
            
            # Sort by boosted similarity (descending)
            re_ranked_results.sort(key=lambda x: x[2], reverse=True)
            
            # Process and diversify results to get comprehensive coverage
            retrieved_docs = []
            scores = []
            seen_sources = {}  # Track chunks per source for diversity
            
            # For comparative queries, ensure we get chunks from different documents
            if is_comparative and selected_documents and len(selected_documents) > 1:
                # Group by source
                source_groups = {}
                for doc, score, boosted_sim in re_ranked_results:
                    source = doc.metadata.get('source', 'Unknown')
                    if source not in source_groups:
                        source_groups[source] = []
                    source_groups[source].append((doc, score, boosted_sim))
                
                # Take top chunks from each source alternately
                max_per_source = max(2, k // len(source_groups))
                for source in source_groups:
                    for doc, score, boosted_sim in source_groups[source][:max_per_source]:
                        if len(retrieved_docs) < k:
                            retrieved_docs.append({
                                "content": doc.page_content,
                                "metadata": doc.metadata,
                                "score": boosted_sim,
                                "distance": score
                            })
                            scores.append(boosted_sim)
            else:
                # Standard retrieval with diversity
                for doc, score, boosted_sim in re_ranked_results:
                    source_name = doc.metadata.get('source', 'Unknown')
                    
                    if source_name not in seen_sources:
                        seen_sources[source_name] = 0
                    
                    # Take up to 3 chunks per source
                    if seen_sources[source_name] < 3:
                        retrieved_docs.append({
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": boosted_sim,
                            "distance": score
                        })
                        scores.append(boosted_sim)
                        seen_sources[source_name] += 1
                        
                        if len(retrieved_docs) >= k:
                            break
            
            # Fill remaining slots if needed
            if len(retrieved_docs) < k:
                for doc, score, boosted_sim in re_ranked_results:
                    if len(retrieved_docs) >= k:
                        break
                    # Check if already added
                    if not any(d["content"] == doc.page_content for d in retrieved_docs):
                        retrieved_docs.append({
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": boosted_sim,
                            "distance": score
                        })
                        scores.append(boosted_sim)
            
            # Calculate retrieval confidence as average similarity
            retrieval_confidence = np.mean(scores) if scores else 0.0
            
            # Ensure confidence is between 0 and 1
            retrieval_confidence = max(0.0, min(1.0, retrieval_confidence))
            
            return retrieved_docs, retrieval_confidence
            
        except Exception as e:
            print(f"Error during retrieval: {str(e)}")
            return [], 0.0
    
    def retrieve_context(self, query: str, k: int = 8, selected_documents: Optional[List[str]] = None) -> Tuple[str, List[Dict], float]:
        """
        Retrieve comprehensive context for RAG with formatted text.
        
        Args:
            query: User's question
            k: Number of top documents to retrieve (increased for comprehensive search)
            selected_documents: Optional list of specific documents to search in
            
        Returns:
            Tuple of (formatted_context, retrieved_docs, retrieval_confidence)
        """
        retrieved_docs, retrieval_confidence = self.retrieve(query, k=k, selected_documents=selected_documents)
        
        if not retrieved_docs:
            return "", [], 0.0
        
        # Format context for LLM
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc["metadata"].get("source", "Unknown")
            chunk_id = doc["metadata"].get("chunk_id", "?")
            content = doc["content"].strip()
            
            context_parts.append(
                f"[Source {i}: {source}, Chunk {chunk_id}]\n{content}"
            )
        
        formatted_context = "\n\n---\n\n".join(context_parts)
        
        return formatted_context, retrieved_docs, retrieval_confidence
    
    def get_retrieval_stats(self, query: str, k: int = 3) -> Dict:
        """
        Get detailed retrieval statistics for analysis.
        
        Args:
            query: User's question
            k: Number of documents to retrieve
            
        Returns:
            Dictionary with retrieval statistics
        """
        retrieved_docs, retrieval_confidence = self.retrieve_with_scores(query, k=k)
        
        if not retrieved_docs:
            return {
                "num_retrieved": 0,
                "avg_similarity": 0.0,
                "min_similarity": 0.0,
                "max_similarity": 0.0,
                "sources": []
            }
        
        scores = [doc["score"] for doc in retrieved_docs]
        sources = [doc["metadata"].get("source", "Unknown") for doc in retrieved_docs]
        
        return {
            "num_retrieved": len(retrieved_docs),
            "avg_similarity": retrieval_confidence,
            "min_similarity": min(scores),
            "max_similarity": max(scores),
            "score_std": np.std(scores),
            "sources": sources,
            "unique_sources": len(set(sources))
        }

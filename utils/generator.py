"""
Generator Module
Handles LLM response generation with confidence scoring using Google Gemini.
"""

import os
import re
from typing import Tuple, Optional
import google.generativeai as genai


class ResponseGenerator:
    """Generate answers using Google Gemini with grounding and confidence scoring."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize the response generator.
        
        Args:
            api_key: Google AI API key
            model: Model to use (default: gemini-2.0-flash-exp)
        """
        if api_key:
            genai.configure(api_key=api_key)
        elif os.getenv("GOOGLE_API_KEY"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Ensure model name has proper format
        if not model.startswith("models/"):
            model = f"models/{model}"
        self.model = genai.GenerativeModel(model)
        
    def generate_answer(self, 
                       query: str, 
                       context: str, 
                       retrieval_confidence: float,
                       conversation_context: Optional[str] = None) -> Tuple[str, float, float]:
        """
        Generate an answer based on retrieved context with confidence scoring.
        
        The prompt instructs Gemini to:
        1. Answer ONLY based on provided context (grounding)
        2. Explicitly state if context is insufficient
        3. Provide a self-assessed confidence score (1-10)
        
        Args:
            query: User's question
            context: Retrieved context from documents
            retrieval_confidence: Confidence score from retrieval (0-1)
            
        Returns:
            Tuple of (answer, llm_confidence, final_confidence)
            - answer: Generated response
            - llm_confidence: LLM's self-assessed confidence (1-10)
            - final_confidence: Combined confidence score (0-1)
        """
        # Construct grounded prompt with confidence scoring
        conversation_section = ""
        if conversation_context:
            conversation_section = f"""
Previous Conversation Context:
{conversation_context}

---

"""

        prompt = f"""You are a precise AI analyst that summarizes information from documents while maintaining accuracy on key facts.

CRITICAL INSTRUCTIONS:
1. **Summarize vs. Exact Copy**:
   - SUMMARIZE text descriptions, explanations, and narratives
   - ALWAYS keep EXACT numbers, percentages, dates, and metrics from the context
   - DO NOT paraphrase or round numbers - use them exactly as stated
   - DO NOT make assumptions or infer values not explicitly stated

2. **For Comparative Questions**: 
   - Clearly identify what changed between time periods/documents
   - Use EXACT metrics from each document (e.g., "4,538 in Q1 vs. 4,476 in Q2")
   - Summarize the nature of changes in your own words
   - Organize comparisons in clear, structured format
   - Only compare items that are explicitly mentioned in both contexts

3. **Answer Structure**:
   - Start with a direct, summarized answer
   - Support with specific evidence: exact numbers, dates, percentages
   - Use bullet points for clarity when listing multiple items
   - Briefly note which document each key fact came from (e.g., "Q2 report shows...")
   - Keep descriptions concise but include all relevant exact figures

4. **Grounding Requirements**:
   - Base summaries ONLY on information in the context
   - Use EXACT numbers/dates/percentages - never estimate or round
   - If context lacks information, state: "The provided documents do not contain information on [topic]"
   - DO NOT make assumptions beyond what's explicitly stated
   - DO NOT use external knowledge or general banking knowledge
   - If you need to calculate a change (e.g., difference), only do so if both values are explicitly provided
   - Ensure proper spelling and grammar in your response
   - When you correctly identify missing information, this is HIGH confidence (9-10)

5. **Examples of Good Responses**:
   ✅ "The number of institutions decreased from 4,538 to 4,476, representing a decline in the banking sector."
   ✅ "Net interest margin was 3.2% in Q1 and 3.0% in Q2, showing compression."
   ❌ "There was approximately a 1% decrease" (when exact numbers available)
   ❌ "The banking sector saw some changes" (too vague when specifics available)

6. **Confidence Scoring** (1-10):
   - 9-10: Context provides specific numbers/facts that directly answer the question OR you correctly identified that the documents do not contain the requested information
   - 7-8: Good relevant information with exact metrics but some details missing
   - 5-6: Partial answer with some specifics but significant gaps
   - 3-4: Limited relevant information, mostly vague context
   - 1-2: Context barely relates to question and you cannot determine if information is present or absent

FORMATTING GUIDELINES:
- Use **bold** for key findings and important exact metrics
- Use bullet points (•) for lists
- Use numbered lists for sequential/comparative information
- Keep narrative text concise, preserve exact numbers
- For comparisons: "Q1: **4,538** → Q2: **4,476** (decrease of 62)"
- Cite document names for key facts: "The Q2 Banking Profile shows..."

{conversation_section}Context from documents:
{context}

---

Question: {query}

Provide a clear, summarized answer using ONLY the context above, with EXACT numbers and metrics preserved. End with "CONFIDENCE: X/10" on a new line."""

        try:
            # Call Gemini
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 2000,  # Increased for longer, more detailed answers
                }
            )
            
            full_response = response.text
            
            # Check if response is empty
            if not full_response or not full_response.strip():
                print("Warning: Received empty response from Gemini")
                return "Unable to generate response. Please try again.", 1.0, 0.0
            
            # Extract confidence score from response
            llm_confidence = self._extract_confidence(full_response)
            
            # Remove confidence line from answer for cleaner display
            answer = self._clean_answer(full_response)
            
            # Ensure answer is not empty after cleaning
            if not answer or not answer.strip():
                print(f"Warning: Answer became empty after cleaning. Full response: {full_response[:200]}")
                # Return full response minus just the confidence line
                answer = full_response
            
            # Calculate final combined confidence
            # Formula: 60% retrieval confidence + 40% LLM confidence (normalized)
            final_confidence = 0.6 * retrieval_confidence + 0.4 * (llm_confidence / 10)
            
            return answer, llm_confidence, final_confidence
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(error_msg)
            return error_msg, 0.0, 0.0
    
    def _extract_confidence(self, response: str) -> float:
        """
        Extract confidence score from LLM response.
        
        Args:
            response: Full LLM response text
            
        Returns:
            Confidence score (1-10), defaults to 5.0 if not found
        """
        # Look for pattern like "CONFIDENCE: 8/10" or "Confidence: 8"
        patterns = [
            r'CONFIDENCE:\s*(\d+(?:\.\d+)?)\s*/?\s*10',
            r'Confidence:\s*(\d+(?:\.\d+)?)\s*/?\s*10',
            r'confidence score:\s*(\d+(?:\.\d+)?)\s*/?\s*10',
            r'(\d+(?:\.\d+)?)\s*/\s*10\s*confidence'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                score = float(match.group(1))
                # Ensure score is within valid range
                return max(1.0, min(10.0, score))
        
        # Default to medium confidence if not found
        return 5.0
    
    def _clean_answer(self, response: str) -> str:
        """
        Remove confidence scoring line from answer.
        
        Args:
            response: Full LLM response
            
        Returns:
            Cleaned answer text
        """
        if not response:
            return ""
            
        # Remove lines containing confidence scores
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip lines that contain confidence scoring
            if re.search(r'CONFIDENCE:\s*\d+', line, re.IGNORECASE):
                continue
            # Skip empty lines at the end
            if line.strip() or cleaned_lines:  # Keep line if it has content or if we already have content
                cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines).strip()
    
    def generate_with_context_check(self,
                                   query: str,
                                   context: str,
                                   retrieval_confidence: float,
                                   conversation_context: Optional[str] = None,
                                   min_confidence_threshold: float = 0.3) -> dict:
        """
        Generate answer with automatic context sufficiency check.
        
        Args:
            query: User's question
            context: Retrieved context
            retrieval_confidence: Retrieval confidence score
            min_confidence_threshold: Minimum confidence to provide answer
            
        Returns:
            Dictionary with answer, confidence scores, and metadata
        """
        if not context.strip():
            return {
                "answer": "I don't have any relevant context to answer this question. Please upload relevant documents first.",
                "llm_confidence": 0.0,
                "retrieval_confidence": 0.0,
                "final_confidence": 0.0,
                "context_available": False
            }
        
        answer, llm_confidence, final_confidence = self.generate_answer(
            query, context, retrieval_confidence, conversation_context
        )
        
        result = {
            "answer": answer,
            "llm_confidence": llm_confidence,
            "retrieval_confidence": retrieval_confidence,
            "final_confidence": final_confidence,
            "context_available": True,
            "sufficient_confidence": final_confidence >= min_confidence_threshold
        }
        
        # Add warning for low confidence
        if final_confidence < min_confidence_threshold:
            result["warning"] = (
                f"Low confidence ({final_confidence:.2f}). "
                "The answer may not be well-supported by the available context."
            )
        
        return result

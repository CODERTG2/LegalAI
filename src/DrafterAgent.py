import json
from typing import List, Dict, Any

class DrafterAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def assess(self, query, answer, formatted_context):        
        prompt = f"""Analyze this Q&A and determine what improvements are needed. Respond with a JSON object containing boolean flags:

Query: {query}
Answer: {answer}
Available Context: {formatted_context}

Assess:
1. Is the answer well-grounded in the provided context? 
2. Does the answer directly address the query?
3. Is the context sufficient to answer the query?
4. Any other brief suggestions for improvement?

Respond ONLY with JSON:
{{
    "needs_grounding": true/false,
    "needs_query_focus": true/false,
    "insufficient_context": true/false,
    "assessment_summary": "brief explanation"
}}"""
        
        response_content = self.llm_client.chat(
            messages=[
                {"role": "system", "content": "You are an expert evaluator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
        )

        try:
            content = response_content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error parsing assessment JSON: {e}")
            return {"needs_grounding": False, "needs_query_focus": False, "sufficient_context": True, "assessment_summary": "Error parsing assessment"}
    
    def draft(self, query, answer, formatted_context):
        assessment = self.assess(query, answer, formatted_context)
        if answer and not any([assessment.get("needs_grounding"), assessment.get("needs_query_focus"), assessment.get("insufficient_context")]):
            return answer
        
        improvement_focus = []
        if assessment.get("needs_grounding"):
            improvement_focus.append("Better ground the answer in the provided context")
        if assessment.get("needs_query_focus"): 
            improvement_focus.append("Make the answer more directly responsive to the query")
        if assessment.get("assessment_summary"):
            improvement_focus.append(assessment["assessment_summary"])
            
        # User requested prompt structure
        prompt = f"""Answer the following query using the provided context. Make sure to cite any sources you are using.
        
        Query: {query}
        Context: {formatted_context}
        
        Instructions:
        - Act as an AI assistant.
        - State the answer directly with citations, where you give the author, article name, and source.
        - Do NOT use phrases like "Based on the provided context" or "According to the documents".
        - Focus on improvements: {', '.join(improvement_focus)}
        
        Answer:"""

        response = self.llm_client.chat(
            messages=[
                {"role": "system", "content": "You are an expert in medical diagnostic devices. Provide clear, well-grounded answers."},
                {"role": "user", "content": prompt}
            ],
        )
        
        return response
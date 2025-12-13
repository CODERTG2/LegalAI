import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from DeepSeekClient import DeepSeekClient
from util import cosine_similarity

load_dotenv()

class NewsClient:
    def __init__(self, query, query_embedding, model):
        self.api_key = os.getenv('NEWS_API_KEY')
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables")
        self.base_url = "https://eventregistry.org/api/v1"
        self.search_endpoint = f"{self.base_url}/article/getArticles"
        self.query = query
        self.multi_queries = None
        self.model = model
        self.deepseek_client = DeepSeekClient()
    
    def query_processing(self):
        prompt = f"""
        Given the following question, generate a list of keywords that could be used to retrieve information from a database of articles.
        The retrieved information will be used to answer the original question.
        Stay relevant to the question itself.

        The question to create queries based off of is:
        {self.query}

        Return the output as a list of 3 queries only with no punctuation or numbering. Just have the questions in separate lines.
        Example Query: "What is the latest news on climate change?"
        Example Output: climate change latest news
        Example Query: "Who won the best actor Oscar in 2023?"
        Example Output: best actor Oscar 2023
        """
        response = self.deepseek_client.chat(
            messages=[
                {"role": "system", "content": "You are an expert in breaking down queries into search terms."},
                {"role": "user", "content": prompt}
            ]
        )
        output = response["message"]["content"]
        self.multi_queries = output.split('\n')
        if len(self.multi_queries) > 3:
            self.multi_queries = self.multi_queries[:3]
            
        return self.multi_queries
    
    def search_articles(
        self, 
        query: str,
        count: int = 2,
        sort_by: str = "rel",
        lang: Optional[str] = "eng"
    ) -> List[Dict]:
        payload = {
            "action": "getArticles",
            "keyword": query,
            "articlesPage": 1,
            "articlesCount": min(count, 100),
            "articlesSortBy": sort_by,
            "articlesSortByAsc": False,
            "articlesArticleBodyLen": -1,
            "resultType": "articles",
            "dataType": ["news"],
            "apiKey": self.api_key,
            "forceMaxDataTimeWindow": 31
        }
        
        if lang:
            payload["lang"] = lang
        
        try:
            response = requests.post(
                self.search_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            if "articles" in data and "results" in data["articles"]:
                articles = data["articles"]["results"]
                return articles
            else:
                return []
                
        except requests.exceptions.RequestException as e:
            # print(f"Error fetching articles: {e}")
            raise
    
    def get_best_articles(self, query: str, count: int = 2) -> List[Dict]:
        return self.search_articles(
            query=query,
            count=count,
            sort_by="rel"
        )
    
    def chunking(article, model, sentences_per_chunk=5):
        """Set sentence chunking for articles."""
        text = article["body"]
        sentences = text.split(". ")
        context = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = ". ".join(chunk_sentences)
            
            if chunk_text and not chunk_text.endswith("."):
                chunk_text += "."
            
            chunk_dict = article.copy()
            
            chunk_dict["body"] = chunk_text
            chunk_dict["embedding"] = model.encode(chunk_text)

            chunks.append({
                "chunk": chunk_dict,
                "distance": cosine_similarity(chunk_dict["embedding"], self.query_embedding)
            })
        
        return chunks
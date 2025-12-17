import os
import sys
# Fix for FAISS/Torch OpenMP conflict on macOS
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
from mcp.server.fastmcp import FastMCP
from typing import List
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer
import numpy as np
import mongoengine
from dotenv import load_dotenv

from BillClient import BillClient
from LLMClient import GroqClient
from NewsClient import NewsClient
from OrderClient import OrderClient
from OpinionClient import OpinionClient
from Evaluator import Evaluator
from CacheHit import cache_hit
from CacheDB import CacheDB
from util import cosine_similarity

mcp = FastMCP("LegalAI")
llm_client = GroqClient()
bills = BillClient()
orders = OrderClient()
opinions = OpinionClient()

load_dotenv()
try:
    model = SentenceTransformer("src/assets/model", trust_remote_code=True)
    mongoengine.connect(host=os.getenv("MONGO_URI"))

except:
    model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

convo_history = []
context_history = []

@mcp.tool()
def search(query: str):
    context = []
    domains = choose_domain(query)
    logging.info(f"Selected domains: {domains}")

    query_embedding = np.array(model.encode(f"search_query: {query}"), dtype=np.float32).reshape(1,-1)
    norm_qe = query_embedding/np.linalg.norm(query_embedding)
    
    answer, cached_query, similarity = cache_hit(query_embedding)
    if answer:
        logging.info("Cache hit!")
        return answer
    
    if "Congressional Bills" in domains:
        try:
            logging.info("Searching Congressional Bills...")
            context.extend(bills.search_congressional_bills(query, norm_qe))
        except Exception as e:
            logging.error(f"ERROR: Failed to search Congressional Bills: {e}")

    if "Executive Orders" in domains:
        try:
            logging.info("Searching Executive Orders...")
            context.extend(orders.search_executive_orders(query, norm_qe))
        except Exception as e:
            logging.error(f"ERROR: Failed to search Executive Orders: {e}")

    if "Supreme Court Decisions" in domains:
        try:
            logging.info("Searching Supreme Court Decisions...")
            context.extend(opinions.search_supreme_court_decisions(query, norm_qe))
        except Exception as e:
            logging.error(f"ERROR: Failed to search Supreme Court Decisions: {e}")

    if "News Articles" in domains:
        try:
            logging.info("Searching News Articles...")
            context.extend(get_news_articles(query, norm_qe))
        except Exception as e:
            logging.error(f"ERROR: Failed to search News Articles: {e}")
    
    logging.info("Sorting context...")
    context.sort(key=lambda item: item['metric'], reverse=True)
    
    logging.info("Selecting best context...")
    best_context = context[:5]
    formatted_context = format_context(best_context)

    logging.info("Generating response...")
    response = llm_client.chat(
        f"""Answer the following query using the provided context. Make sure to cite any sources you are using.
        Query: {query}
        Context: {formatted_context}
        Answer:"""
    )

    logging.info("Evaluating response...")
    evaluator = Evaluator(query, query_embedding, best_context, formatted_context, response, model, llm_client)
    response, evaluation = evaluator.evaluate()
    context_history.extend(context)

    logging.info("Verifying response...")
    if verify(query, query_embedding, best_context, formatted_context, response):
        convo_history.append({
            "query": query,
            "previous_response": response
        })

        final_response = response + evaluation
        logging.info("Saving response to cache...")
        CacheDB(
                query=query,
                answer=final_response,
                embedding=query_embedding.flatten().tolist(),
                evaluation="neutral",
                feedback="",
            ).save()

        logging.info("Returning response...")
        return final_response

    else:
        convo_history.append({
            "query": query,
            "previous_response": "context was not enough"
        })
        return "I cannot respond to this query based on the provided context. Please try again or ask a different question."

@mcp.tool()
def choose_domain(query: str):
    return llm_client.chat(
        f"""Choose what domain this query can best be answered by:
        1. Congressional Bills
        2. Executive Orders
        3. Supreme Court Decisions
        4. News Articles
        Your response should be formatted as a list of strings: 
        Example 1 - ["Congressional Bills"]
        Example 2 - ["Congressional Bills", "Executive Orders"]
        Example 3 - ["Congressional Bills", "Executive Orders", "Supreme Court Decisions", "News Articles"]

        Query: {query}
        Answer:
        """
    )


@mcp.tool()
def get_news_articles(query: str, query_embedding):
    news = NewsClient(query, query_embedding, llm_client)
    keywords = news.query_processing()
    
    found_articles = []

    for keyword in keywords:
        articles = news.get_best_articles(keyword, count=5)
        if articles:
            found_articles.extend(articles)

    if not found_articles:
        try:
            nltk.data.find('corpora/stopwords')
        except nltk.downloader.DownloadError:
            nltk.download('stopwords')
        stop_words = set(stopwords.words('english'))
        word_tokens = word_tokenize(query)
        filtered_words = [w for w in word_tokens if not w.lower() in stop_words]
        
        for i in range(0, len(filtered_words), 2):
            query_chunk = ' '.join(filtered_words[i:i+2])
            articles = news.get_best_articles(query_chunk, count=5)
            if articles:
                found_articles.extend(articles)
        
        if not found_articles:
            filtered_sentence = ' '.join(filtered_words)
            articles = news.get_best_articles(filtered_sentence, count=5)
            if articles:
                found_articles.extend(articles)
            else:
                return [{
                    "chunk": {
                        "body": "No relevant news articles were found.",
                        "title": "System Message",
                        "date": "N/A"
                    },
                    "distance": 0
                }]
    
    seen_uris = set()
    unique_articles = []
    for art in found_articles:
        uri = art.get('uri')
        if uri and uri not in seen_uris:
            seen_uris.add(uri)
            unique_articles.append(art)
        elif not uri:
            unique_articles.append(art)

    context = []
    for article in unique_articles:
        context.extend(news.chunking(article, model))
    
    return context

@mcp.tool()
def verify(query, query_embedding, documents, formatted_context, response):
    try:
        vector_guardrail_1 = documents[0]["metric"] >= 0.5
    except:
        vector_guardrail_1 = False
    vector_guardrail_2 = cosine_similarity(query_embedding, np.array(model.encode(response), dtype=np.float32)) <= 0.5
    llm_guardrail = "true" in llm_client.chat(
        f"""Is the response generated based in context and answering the question? Only say 'true' or 'false'.
        
        If you say "true" that means that the response is based in context and is answering the question.
        If you say "false" that means that the response is not based in context or not answering the question.

        Question: {query}
        Context: {formatted_context}
        Response: {response}

        Answer:
        """
    )

    logging.info(f"guardrail 1: {vector_guardrail_1}, 2: {vector_guardrail_2}, deepseek: {llm_guardrail}")

    if llm_guardrail & (vector_guardrail_1 | vector_guardrail_2):
        return True
    elif vector_guardrail_1 & vector_guardrail_2:
        return True
    else:
        return False

def format_context(context: List[dict]) -> str:
    formatted_context = []
    
    for item in context:
        chunk = item.get('chunk', {})
        
        # Congressional Bill
        if 'congress' in chunk and 'number' in chunk:
            title = chunk.get('title', 'Unknown Bill')
            congress = chunk.get('congress', 'Unknown')
            number = chunk.get('number', 'Unknown')
            latest_action = chunk.get('latestAction', {})
            action_text = latest_action.get('text', 'No action text')
            action_date = latest_action.get('actionDate', 'Unknown Date')
            
            entry = f"Congressional Bill: {title} ({congress}th Congress, H.R. {number})\n" \
                    f"Date: {action_date}\n" \
                    f"Latest Action: {action_text}"
            formatted_context.append(entry)
            
        # Executive Order
        elif 'order_number' in chunk and 'signing_date' in chunk:
            title = chunk.get('title', 'Unknown Order')
            date = chunk.get('signing_date', 'Unknown Date')
            chunk_text_obj = chunk.get('chunk_text', {})
            text = chunk_text_obj.get('text', '') if isinstance(chunk_text_obj, dict) else str(chunk_text_obj)
            
            entry = f"Executive Order: {title} ({date})\n" \
                    f"Text: {text}"
            formatted_context.append(entry)
            
        # Supreme Court Opinion
        elif 'resource_uri' in chunk and 'text' in chunk:
            date = chunk.get('date_created', 'Unknown Date')
            text = chunk.get('text', '')
            url = chunk.get('absolute_url', '')
            
            entry = f"Supreme Court Decision ({date})\n" \
                    f"URL: {url}\n" \
                    f"Text: {text}"
            formatted_context.append(entry)
            
        # News Article
        elif 'body' in chunk and 'title' in chunk:
            title = chunk.get('title', 'Unknown Title')
            body = chunk.get('body', '')
            date = chunk.get('date', 'Unknown Date') # Assuming date field exists, defaulting if not
            
            entry = f"News Article: {title} ({date})\n" \
                    f"Content: {body}"
            formatted_context.append(entry)
            
        else:
            # Fallback for unknown types
            formatted_context.append(f"Unknown Source: {str(chunk)}")
            
    return "\n\n".join(formatted_context)

@mcp.tool()
def follow_up(query: str):
    query_embedding = np.array(model.encode(query), dtype=np.float32)
    current = context_history.copy()
    for context in current:
        context["similarity"] = cosine_similarity(np.array(context["chunk"]["embedding"], dtype=np.float32), query_embedding)
    
    current.sort(key=lambda item: item['similarity'], reverse=False)
    relevant_context = current[:5]
    formatted_context = format_context(relevant_context)

    llm_check = llm_client.chat(f"""
    Read the query and say "true" or "false" if there is sufficient context to answer it.
    Query: {query}
    Context: {formatted_context}

    Answer:
    """)

    if "true" in llm_check or relevant_context[0]["similarity"] < 0.5:
        response = llm_client.chat(f"""
        Answer a follow up question based in context and conversation history. Make sure to cite any sources you are using.
        Follow-up question: {query}
        Context: {formatted_context}
        Conversation History: {convo_history}

        Answer:
        """)
        convo_history.append({
            "query": query,
            "previous_response": response
        })
        return response
    else:
        search(query)

@mcp.tool()
def update_user_evaluation(query, response, evaluation: str):
    CacheDB.objects(query=query, answer=response).update(evaluation=evaluation)

@mcp.tool()
def update_user_feedback(query, response, feedback: str):
    CacheDB.objects(query=query, answer=response).update(feedback=feedback)

@mcp.tool()
def clean_history():
    context_history.clear()
    convo_history.clear()

if __name__ == "__main__":
    logging.info("Starting MCP server...")
    # print("Starting MCP server...")
    mcp.run(transport="stdio")
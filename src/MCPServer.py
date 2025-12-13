import logging
from mcp.server.fastmcp import FastMCP
from typing import List
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer

from BillClient import BillClient
from DeepSeekClient import DeepSeekClient
from NewsClient import NewsClient
from OrderClient import OrderClient
from OpinionClient import OpinionClient
from util import cosine_similarity

mcp = FastMCP("LegalAI")
dsclient = DeepSeekClient()
bills = BillClient()
orders = OrderClient()
opinions = OpinionClient()
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

@mcp.tool()
def search(query: str):
    # TODO: just combine everything together here.
    context = []
    domains = choose_domain(query)
    query_embedding = model.encode(f"search_query: {query}")
    if "Congressional Bills" in domains:
        context.append(for doc in get_congressional_bills(query_embedding))
    if "Executive Orders" in domains:
        context.append(for doc in get_executive_orders(query_embedding))
    if "Supreme Court Decisions" in domains:
        context.append(for doc in get_supreme_court_decisions(query, query_embedding))
    if "News Articles" in domains:
        context.append(for doc in get_news_articles(query))

    best_context = context.sort(key=lambda item: item['distance'])[:5]

    response = dsclient.chat(
        f"""Answer the following query using the provided context. Make sure to cite any sources you are using.
        If you cannot answer the query using the provided context, respond with "I cannot respond to this query based on the provided context. Please try again or ask a different question."
        Query: {query}
        Context: {best_context}
        Answer:"""
    )
    
    return response if verify(query, query_embedding, context, format_context(context), response) else "I cannot respond to this query based on the provided context. Please try again or ask a different question."

@mcp.tool()
def choose_domain(query: str):
    return dsclient.chat(
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
def get_congressional_bills(query_embedding):
    embedding = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    return bills.search_congressional_bills(embedding/np.linalg.norm(embedding))

@mcp.tool()
def get_executive_orders(query_embedding):
    embedding = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    return orders.search_congressional_bills(embedding/np.linalg.norm(embedding))


@mcp.tool()
def get_supreme_court_decisions(query_embedding):
    embedding = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
    return opinions.search_congressional_bills(embedding/np.linalg.norm(embedding))

@mcp.tool()
def get_news_articles(query: str, querry_embedding):
    news = NewsClient(query, querry_embedding, dsclient)
    keywords = news.query_processing()
    context = []

    for keyword in keywords:
        articles = news.get_best_articles(keyword, count=5)
        if articles:
            context.extend(articles)

    if not context:
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
                context.extend(articles)
        
        if not context:
            filtered_sentence = ' '.join(filtered_words)
            articles = news.get_best_articles(filtered_sentence, count=5)
            if articles:
                context.extend(articles)
            else:
                return "No relevant news articles were found."
    
    for article in articles:
        context.extend(news.chunking(article, model))
    
    return context

@mcp.tool()
def verify(query, query_embedding, documents, formatted_context, response):
    vector_guardrail_1 = documents[0]["distance"] >= 0.5
    vector_guardrail_2 = cosine_similarity(querry_embedding, model.encode(response)) >= 0.5
    deepseek_guardrail = "false" in dsclient.chat(
        f"""Is the response generated not based in context or not answering the question? Only say 'true' or 'false'.
        
        If you say "true" that means that the response is not based in context or not answering the question.
        If you say "false" that means that the response is based in context and is answering the question.

        Question: {query}
        Context: {formatted_context}
        Response: {response}

        Answer:
        """
    )

    return vector_guardrail_1 & vector_guardrail_2 & deepseek_guardrail

def format_context():
    # TODO: format context
    pass

if __name__ == "__main__":
    logging.info("Starting MCP server...")
    print("Starting MCP server...")
    mcp.run(transport="stdio")
import logging
from mcp.server.fastmcp import FastMCP
from typing import List

from DeepSeekClient import DeepSeekClient

mcp = FastMCP("LegalAI")
dsclient = DeepSeekClient()

@mcp.tool()
def search(query: str):
    # TODO: just combine everything together here.
    context = []
    domains = choose_domain(query)
    if "Congressional Bills" in domains:
        context.append(for doc in get_congressional_bills(query))
    if "Executive Orders" in domains:
        context.append(for doc in get_executive_orders(query))
    if "Supreme Court Decisions" in domains:
        context.append(for doc in get_supreme_court_decisions(query))
    if "News Articles" in domains:
        context.append(for doc in get_news_articles(query))
    
    response = dsclient.chat(
        f"""Answer the following query using the provided context:
        If you cannot answer the query using the provided context, respond with "I cannot respond to this query based on the provided context. Please try again or ask a different question."
        Query: {query}
        Context: {context}
        Answer:"""
    )
    
    return response if verify(query, context, response) else "I cannot respond to this query based on the provided context. Please try again or ask a different question."

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
def get_congressional_bills(query: str):
    # TODO: figure out a way to either store a local vector + graph db of congressional bills or create a scraper or find an API
    pass

@mcp.tool()
def get_executive_orders(query: str):
    # TODO: figure out a way to either store a local vector + graph db of executive orders or create a scraper or find an API
    pass

@mcp.tool()
def get_supreme_court_decisions(query: str):
    # TODO: figure out a way to either store a local vector + graph db of supreme court decisions or create a scraper or find an API
    pass

@mcp.tool()
def get_news_articles(query: str):
    # TODO: news article search - use news dash
    pass

@mcp.tool()
def verify(query, documents, response):
    # TODO: vector embedding and deepseek approval
    pass

if __name__ == "__main__":
    logging.info("Starting MCP server...")
    print("Starting MCP server...")
    mcp.run(transport="stdio")
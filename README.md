# Veritas

Veritas is a powerful legal AI system designed to democratize access to legal knowledge. It combines a robust semantic search engine with Retrieval-Augmented Generation (RAG) to provide accurate, context-aware answers from a diverse range of US legal documents.

Built on the **Model Context Protocol (MCP)**, Veritas integrates a unified Python retrieval backend with a modern web interface, allowing users to query Congressional Bills, Executive Orders, Supreme Court Decisions, and related News Articles through a single intuitive search engine.

## Features

-   **Multi-Domain Retrieval**: Seamlessly indexes and searches across four critical data sources:
    -   Congressional Bills
    -   Executive Orders
    -   Supreme Court Decisions
    -   Contextual News Articles
-   **Semantic Intelligence**: Utilizes advanced `SentenceTransformer` embeddings to understand the *meaning* behind queries, ensuring high-quality retrieval beyond simple keyword matching.
-   **RAG Architecture**: Retrieves the most relevant legal chunks and feeds them into a Large Language Model (Llama 3.3 via Groq) to generate grounded, citation-backed responses.
-   **Verification Guardrails**: Implements a robust verification system using both vector similarity thresholds and a secondary LLM verification step to ensure relevance and reduce hallucinations.
-   **MCP-First Design**: Leveraging the Model Context Protocol allows for modular tool exposure, easy extensibility, and standardized client-server communication.

## Architecture

Veritas operates as a cohesive client-server application:

1.  **MCP Server (`src/MCPServer.py`)**: A Python-based server implementing the `LegalAI` MCP service. It handles:
    -   Loading FAISS vector indices for millisecond-latency retrieval.
    -   Interacting with the Groq API for high-speed LLM inference.
    -   Exposing intelligent tools like `search`, `choose_domain`, `follow_up`, and `verify`.
    -   Managing conversation and context history.
2.  **Web Client (`server.js`)**: A Node.js Express server that:
    -   Acts as an MCP client, launching and connecting to the Python server via stdio transport.
    -   Serves a modern, responsive frontend (`public/`) for seamless user interaction.
    -   Proxies user API requests to the MCP backend tools.

## Prerequisites

-   **Python 3.10+**
-   **Node.js 18+**
-   **Groq API Key**: You need a valid API key from [Groq](https://console.groq.com/) to power the LLM inference.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/veritas.git
cd veritas
```

### 2. Backend Setup (Python)

Create a virtual environment and install the required dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install mcp[cli] sentence-transformers nltk numpy python-dotenv requests faiss-cpu
```

Create a `.env` file in the root directory and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Frontend Setup (Node.js)

Install the required Node.js packages:

```bash
npm install
```

### 4. Data Setup

Veritas relies on pre-built vector indices for its RAG capabilities. Ensure you have the following data artifacts populating `src/assets/`:
-   `bills.index` / `bills.json`
-   `orders.index` / `orders.json`
-   `opinions.index` / `opinions.json` (if applicable)

*Note: Utilities to scrape data, process chunks, and generate these indices are located in the `scripts/` directory.*

## Usage

Start the application using the NPM start script. This will launch the Express server, which in turn automatically initializes the Python MCP server.

```bash
npm start
```

Access the web interface at:
**http://localhost:3000**

## Project Structure

-   `src/`: Python backend source code.
    -   `MCPServer.py`: Main entry point for the MCP server.
    -   `*Client.py`: Specialized handlers for different data domains (Bills, Orders, etc.).
    -   `assets/`: Stores vector indices (.index) and metadata JSON files.
-   `public/`: Frontend static files (HTML, CSS, JS).
-   `scripts/`: Utilities for data scraping, processing, and index generation.
-   `server.js`: Node.js web server and MCP client bridge.
-   `MCPClientManager.js`: Manages the lifecycle and connection to the Python MCP server.

## License

[MIT](LICENSE)
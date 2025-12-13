import json
import networkx as nx
import matplotlib.pyplot as plt
import os
import requests
import sys
from dotenv import load_dotenv

# Load env from current directory or parent
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Add src to path to allow importing if needed, but we'll self-contain for ease
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

class DeepSeekClient:
    """Client for DeepSeek R1 via OpenRouter API."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            print("Warning: OPENROUTER_API_KEY not found in environment.")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "deepseek/deepseek-r1"
    
    def chat(self, messages, model=None):
        if not self.api_key: return None
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.1
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API request failed: {e}")
            return None

def extract_graph_data(client, text):
    """
    Extracts entities and relationships from text using DeepSeek.
    """
    prompt = f"""
    Analyze the following legal text from a congressional bill and extract a Knowledge Graph.
    Identify:
    - Entities: Persons, Organizations, Government Bodies, Laws, key Dates, Locations.
    - Relationships: Interactions between these entities (e.g., 'sponsored', 'amends', 'established', 'reports to').
    
    Return ONLY valid JSON with this structure:
    {{
      "entities": [ {{"id": "UniqueId", "type": "Type", "name": "Name"}}, ... ],
      "relationships": [ {{"source": "SourceId", "target": "TargetId", "relation": "ACTION"}}, ... ]
    }}
    
    Text:
    {text[:2000]} ...
    """
    
    response = client.chat([{"role": "user", "content": prompt}])
    if not response: return None
    
    try:
        clean_resp = response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_resp)
    except Exception as e:
        print(f"Failed to parse JSON response: {e}")
        return None

def main():
    # Load chunks
    chunks_path = os.path.join(os.path.dirname(__file__), 'chunks.json')
    if not os.path.exists(chunks_path):
        print(f"Error: {chunks_path} not found.")
        return

    print("Loading chunks...")
    with open(chunks_path, 'r') as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks)} chunks.")
    
    # Initialize Client
    client = DeepSeekClient()
    
    # Initialize Graph
    G = nx.DiGraph()
    
    # Limit to first 5 for demonstration
    limit = 5
    print(f"Processing first {limit} chunks...")
    
    for i, chunk in enumerate(chunks[:limit]):
        # Extract text from chunk structure
        # Structure varies, assuming chunk['chunk_text']['text'] based on notebook analysis
        chunk_data = chunk.get('chunk_text', {})
        if isinstance(chunk_data, dict):
            text = chunk_data.get('text', '')
        else:
            text = str(chunk_data)
            
        if not text:
            continue
            
        print(f"Extracting from chunk {i+1}...")
        data = extract_graph_data(client, text)
        
        if data:
            for entity in data.get('entities', []):
                G.add_node(entity['id'], label=entity['name'], type=entity['type'])
            for rel in data.get('relationships', []):
                G.add_edge(rel['source'], rel['target'], relation=rel['relation'])
    
    print(f"Graph constructed: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    
    if G.number_of_nodes() > 0:
        plt.figure(figsize=(12, 12))
        pos = nx.spring_layout(G, k=0.5)
        nx.draw(G, pos, with_labels=True, node_size=1500, node_color="skyblue", font_size=8, font_weight="bold", arrows=True, alpha=0.8)
        edge_labels = nx.get_edge_attributes(G, 'relation')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
        
        output_file = os.path.join(os.path.dirname(__file__), 'bill_knowledge_graph.png')
        plt.title("Knowledge Graph from Congressional Bills")
        plt.savefig(output_file)
        print(f"Graph image saved to {output_file}")
    else:
        print("No graph data extracted.")

if __name__ == "__main__":
    main()

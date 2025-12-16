import faiss
import json
from GraphRAG import GraphRAG

class OrderClient:
    def __init__(self):
        self.index = faiss.read_index("src/assets/orders.index")
        with open("src/assets/orders.json", "r") as f:
            self.chunks = json.load(f)
        self.graph_path = "src/assets/orders_knowledge_graph.gexf"
        

    def search_executive_orders(self, query_embedding):
        D, I = self.index.search(query_embedding, k=15)

        context = []
        for d, i in zip(D[0], I[0]):
            context.append({
                "chunk": self.chunks[i],
                "distance": 1-d
            })
        context.sort(key=lambda x: x["distance"], reverse=True)
        
        graph_rag = GraphRAG("src/assets/orders_knowledge_graph.gexf", query)
        return graph_rag.filter_entities(context)
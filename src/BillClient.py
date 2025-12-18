import faiss
import json
from GraphRAG import GraphRAG

class BillClient:
    def __init__(self):
        self.index = faiss.read_index("src/assets/bills.index")
        with open("src/assets/bills.json", "r") as f:
            self.chunks = json.load(f)

    def search_congressional_bills(self, query, query_embedding, k=5):
        D, I = self.index.search(query_embedding, k=k)

        context = []
        for d, i in zip(D[0], I[0]):
            context.append({
                "chunk": self.chunks[i],
                "distance": float(1-d)
            })
        context.sort(key=lambda x: x["distance"], reverse=True)
        
        graph_rag = GraphRAG("src/assets/bills_knowledge_graph.gexf", query)
        return graph_rag.filter_entities(context)

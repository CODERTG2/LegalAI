import faiss
import json
from GraphRAG import GraphRAG

class OpinionClient:
    def __init__(self):
        self.index = faiss.read_index("src/assets/opinions.index")
        with open("src/assets/opinions.json", "r") as f:
            self.chunks = json.load(f)

    def search_supreme_court_decisions(self, query, query_embedding):
        D, I = self.index.search(query_embedding, k=15)

        context = []
        for d, i in zip(D[0], I[0]):
            context.append({
                "chunk": self.chunks[i],
                "distance": float(1-d)
            })
        context.sort(key=lambda x: x["distance"], reverse=True)
        
        graph_rag = GraphRAG("src/assets/opinions_knowledge_graph.gexf", query)
        return graph_rag.filter_entities(context)
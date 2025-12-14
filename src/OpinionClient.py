import faiss
import json

class OpinionClient:
    def __init__(self):
        self.index = faiss.read_index("src/assets/opinions.index")
        with open("src/assets/opinions.json", "r") as f:
            self.chunks = json.load(f)

    def search_supreme_court_decisions(self, query_embedding):
        D, I = self.index.search(query_embedding, k=5)

        context = []
        context = []
        for d, i in zip(D[0], I[0]):
            context.append({
                "chunk": self.chunks[i],
                "distance": d
            })
        
        return context
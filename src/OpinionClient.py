import faiss
import json

class OpinionClient:
    def __init__():
        self.index = faiss.read_index("src/assets/opinions.index")
        with open("src/assets/opinions.json", "r") as f:
            self.chunks = json.load(f)

    def search_supreme_court_decisions(self, query_embedding):
        if query_embedding.shape[1] != self.index.d:
            raise Exception("Query embedding dimension must match index dimension")

        D, I = self.index.search(query_embedding, k=5)

        context = []
        for d, i in D, I:
            context.append({
                "chunk": self.chunks[i]
                "distance" = d
            })
        
        return context
from gliner import GLiNER
import networkx as nx

class GraphRAG:
    def __init__(self, graph_path, query):
        self.graph_path = graph_path
        self.graph = nx.read_gexf(self.graph_path)
        self.query = query
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        if "bills" in self.graph_path:
            self.labels = ["Person", "Legislator", "Committee", "Government Agency", "Bill", "Date", "Topic"]
        # TODO: figure out labels for these
        elif "orders" in self.graph_path:
            self.labels = ["Person", "Legislator", "Committee", "Government Agency", "Executive Order", "Date", "Topic"]
        elif "opinions" in self.graph_path:
            self.labels = ["Person", "Legislator", "Committee", "Government Agency", "Opinion", "Date", "Topic"]

    def filter_entities(self, context):
        tags = self.traverse()
        max_distance = context[0]["distance"]
        return self.entities_from_context(context, tags, max_distance), 

    def traverse(self):
        # TODO: return two things: filter entities and knowledge graph context.
        entities = self.model.predict_entities(self.query, self.labels)
        keys = [e['text'].strip() for e in entities]

        # TODO: filter graph based on these keys
        tags = []
        for key in keys:
            tags.extend(list(self.graph.neighbors(key)))

        return tags
    
    def entities_from_context(self, context, tags, max_distance):
        for c in context:
            try:
                # bills & orders
                entities = self.model.predict_entities(c["chunk"]["chunk_text"]["text"], self.labels)
            except:
                try:
                    # opinions
                    entities = self.model.predict_entities(c["chunk"]["text"], self.labels)
                except:
                    entities = []
            keys = [e['text'].strip() for e in entities]
            counter = 0
            for key in keys:
                if key in tags:
                    counter += 1
            c["counter"] = counter

        context.sort(key=lambda x: x["counter"], reverse=True)
        max_tags = context[0]["counter"]
        for c in context:
            c["metric"] = (c["distance"] + max_distance * (float(c["counter"]) / max_tags)) / (2*max_distance)

        return context.sort(key=lambda x: x["metric"], reverse=True)


    
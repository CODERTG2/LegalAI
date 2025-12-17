from gliner import GLiNER
import networkx as nx
import numpy as np

class GraphRAG:
    def __init__(self, graph_path, query):
        self.graph_path = graph_path
        self.graph = nx.read_gexf(self.graph_path)
        self.query = query
        self.model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        if "bills" in self.graph_path:
            self.labels = [
                            # People & Roles
                            "Person", "Legislator", "Judge", 
                            
                            # Institutions
                            "Committee", "Government Agency", "Court", "Organization",
                            
                            # Legal Docs
                            "Bill", "Statute", "Case Citation", "Executive Order",
                            
                            # Context
                            "Date", "Location", "Topic"
                        ]
        elif "orders" in self.graph_path:
            self.labels = [
                            # People & Roles
                            "Person", "Legislator", "Judge", "President", "Secretary",
                            
                            # Institutions
                            "Committee", "Government Agency", "Court", "Organization", "Department",
                            
                            # Legal Docs
                            "Bill", "Statute", "Case Citation", "Executive Order", "Act",
                            
                            # Context
                            "Date", "Location", "Topic"
                        ]
        elif "opinions" in self.graph_path:
            self.labels = [
                            # People & Roles
                            "Judge", "Justice", "Petitioner", "Respondent", "Plaintiff", "Defendant", "Attorney",
                            
                            # Institutions
                            "Court", "Government Agency", "Organization", "Committee",
                            
                            # Legal Docs & Concepts
                            "Case Citation", "Statute", "Constitution", "Amendment", "Precedent", "Doctrine",
                            
                            # Context
                            "Date", "Location", "Topic"
                        ]

    def filter_entities(self, context):
        tags = self.traverse()
        max_distance = context[0]["distance"]
        if max_distance == 0:
            max_distance = context[-1]["distance"]
        return self.entities_from_context(context, tags, max_distance)

    def traverse(self):
        entities = self.model.predict_entities(self.query, self.labels)
        keys = [e['text'].strip() for e in entities]

        tags = []
        for key in keys:
            try:
                tags.extend(list(self.graph.neighbors(key)))
            except:
                pass

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
        if max_tags == 0:
            max_tags = context[-1]["counter"]
        if max_tags == 0:
            max_tags = 1
        for c in context:
            c["metric"] = float(np.mean((c["distance"] + max_distance * (float(c["counter"]) / max_tags)) / (2*max_distance)))

        context.sort(key=lambda x: x["metric"], reverse=True)
        return context


    
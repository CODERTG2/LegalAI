import numpy as np
from DrafterAgent import DrafterAgent
from util import cosine_similarity

class Evaluator:
    def __init__(self, query, query_embedding, context, formatted_context, response, model, llm_client):
        self.query = query
        self.query_embedding = query_embedding
        self.context = context
        self.formatted_context = formatted_context
        self.response = response
        self.model = model
        self.llm_client = llm_client
        self.response_embedding = np.array(self.model.encode(self.response), dtype=np.float32)
    
    def evaluate(self):
        context_query = float(1-self.context[0]["distance"])
        answer_query = float(1-cosine_similarity(self.query_embedding, self.response_embedding))
        context_answer = float(1-cosine_similarity(self.response_embedding, np.array(self.context[0]["chunk"]["embedding"], dtype=np.float32)))

        if context_query < 0.7 or answer_query < 0.7 or context_answer < 0.7:
            drafter = DrafterAgent(self.llm_client)
            new_response = drafter.draft(self.query, self.formatted_context, self.response)
            new_response_embedding = np.array(self.model.encode(new_response), dtype=np.float32)
            new_answer_query = float(1-cosine_similarity(self.query_embedding, new_response_embedding))
            new_context_answer = float(1-cosine_similarity(np.array(self.context[0]["chunk"]["embedding"], dtype=np.float32), new_response_embedding))
            if new_answer_query > answer_query or new_context_answer > context_answer:
                return new_response, self.formatted_evaluation(context_query, new_answer_query, new_context_answer)
            else:
                return self.response, self.formatted_evaluation(context_query, answer_query, context_answer)
        else:
            return self.response, self.formatted_evaluation(context_query, answer_query, context_answer)

    def formatted_evaluation(self, context_query, answer_query, context_answer):
        formatted_text = "\n\n---\n**Evaluation Scores:**\n\n"

        if context_answer >= 0.8:
            formatted_text += f"**Answer grounded in source:** 🟢 Excellent - {context_answer:.3f}\n"
        elif context_answer >= 0.5:
            formatted_text += f"**Answer grounded in source:** 🟡 Good - {context_answer:.3f}\n"
        elif context_answer >= 0.3:
            formatted_text += f"**Answer grounded in source:** 🟠 Fair - {context_answer:.3f}\n"
        else:
            formatted_text += f"**Answer grounded in source:** 🔴 Poor - {context_answer:.3f}\n"

        if context_query >= 0.8:
            formatted_text += f"**Source relevance to question:** 🟢 Excellent - {context_query:.3f}\n"
        elif context_query >= 0.5:
            formatted_text += f"**Source relevance to question:** 🟡 Good - {context_query:.3f}\n"
        elif context_query >= 0.3:
            formatted_text += f"**Source relevance to question:** 🟠 Fair - {context_query:.3f}\n"
        else:
            formatted_text += f"**Source relevance to question:** 🔴 Poor - {context_query:.3f}\n"

        if answer_query >= 0.8:
            formatted_text += f"**Answer quality:** 🟢 Excellent - {answer_query:.3f}\n"
        elif answer_query >= 0.5:
            formatted_text += f"**Answer quality:** 🟡 Good - {answer_query:.3f}\n"
        elif answer_query >= 0.3:
            formatted_text += f"**Answer quality:** 🟠 Fair - {answer_query:.3f}\n"
        else:
            formatted_text += f"**Answer quality:** 🔴 Poor - {answer_query:.3f}\n"

        return formatted_text


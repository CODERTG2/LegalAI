from mongoengine import Document, StringField, DateTimeField, ListField, FloatField
from datetime import datetime

class CacheDB(Document):
    query = StringField(required=True)
    answer = StringField(required=True)
    embedding = ListField(FloatField(), required=True)
    evaluation = StringField(required=True, enum=["good", "bad", "neutral"])
    feedback = StringField(required=True)
    createdAt = DateTimeField(required=True, default=datetime.now)    

    meta = {
        'collection': 'cache',
        'indexes': [
            {'fields': ['query', 'answer', 'embedding', 'evaluation', 'feedback', 'createdAt'], 'unique': True}
        ]
    }
import re
import requests
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MemoryAgent:
    def __init__(self):
        self.memory = {}

    def store(self, key, value):
        self.memory[key] = value

    def recall(self, key=None):
        if key:
            return self.memory.get(key)
        return self.memory

class WeatherAgent:
    def __init__(self, api_key, memory_agent):
        self.api_key = api_key
        self.memory = memory_agent
        self.url = "http://api.openweathermap.org/data/2.5/weather"

    def answer(self, city):
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        res = requests.get(self.url, params=params)
        if res.status_code != 200:
            return "I couldn't retrieve the weather right now."
        data = res.json()
        previous = self.memory.recall(city)
        self.memory.store(city, data["main"])
        response = f"The current weather in {city} is {data['weather'][0]['description']} with a temperature of {data['main']['temp']}°C."
        if previous:
            response += f" Earlier it was {previous['temp']}°C."
        return response

class QueryProcessor:
    def process(self, query):
        query = query.lower()
        query = re.sub(r"[^\w\s]", "", query)
        synonyms = {
            "location": "located address",
            "where": "located address",
            "reservation": "reserve booking",
            "menu": "food dishes",
            "fish": "seafood"
        }
        for k, v in synonyms.items():
            if k in query:
                query += " " + v
        return query

class DailyDishAgent:
    def __init__(self, questions, answers):
        self.answers = answers
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.doc_vectors = self.vectorizer.fit_transform(questions)

    def answer(self, query):
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.doc_vectors)[0]
        best_idx = np.argmax(similarities)
        if similarities[best_idx] < 0.08:
            return None
        return self.answers[best_idx]

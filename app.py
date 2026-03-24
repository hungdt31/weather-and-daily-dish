import streamlit as st
import re
import requests
import nltk
import numpy as np
import os
import urllib.request
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- NLTK Setup ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download("punkt")

# --- Agent Classes ---
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

# --- Helper Functions ---
def load_faq_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def parse_faq(text):
    faq_pairs = []
    pattern = r"Q:\s*(.*?)\s*A:\s*(.*?)(?=\n\s*\d+\.\s*Q:|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)
    for q, a in matches:
        faq_pairs.append({
            "question": clean_text(q.lower()),
            "answer": clean_text(a)
        })
    return faq_pairs

def route_query(query):
    weather_keywords = ["weather", "rain", "raining", "forecast", "temperature", "hot", "cold", "humidity"]
    query = query.lower()
    for word in weather_keywords:
        if word in query:
            return "weather"
    return "daily_dish"

# --- Initialization ---
@st.cache_resource
def setup_agents():
    # 1. Download PDF if not exists
    faq_pdf_path = "The-Daily-Dish-FAQ.pdf"
    if not os.path.exists(faq_pdf_path):
        url = 'https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/7vgNfis17dQfjHAiIKkBOg/The-Daily-Dish-FAQ.pdf'
        urllib.request.urlretrieve(url, faq_pdf_path)
    
    # 2. Parse PDF
    faq_text = load_faq_pdf(faq_pdf_path)
    faq_data = parse_faq(faq_text)
    faq_questions = [item["question"] for item in faq_data]
    faq_answers = [item["answer"] for item in faq_data]
    
    # 3. Setup Agents
    # Note: the API key should ideally be loaded from an environment variable or secrets
    # Get API key from Streamlit secrets or default environment variables
    API_KEY = st.secrets.get("OPENWEATHER_API_KEY", os.getenv("OPENWEATHER_API_KEY"))
    if not API_KEY:
        st.error("Missing OpenWeather API Key. Please add OPENWEATHER_API_KEY to your secrets.")
    memory_agent = MemoryAgent()
    weather_agent = WeatherAgent(API_KEY, memory_agent)
    daily_dish_agent = DailyDishAgent(faq_questions, faq_answers)
    query_processor = QueryProcessor()
    
    return weather_agent, daily_dish_agent, query_processor

weather_agent, daily_dish_agent, query_processor = setup_agents()
RESTAURANT_CITY = "New york"

# --- Chatbot Logic ---
def get_chatbot_response(user_question):
    route = route_query(user_question)
    processed = query_processor.process(user_question)
    
    if route == "weather":
        return weather_agent.answer(RESTAURANT_CITY)
    
    answer = daily_dish_agent.answer(processed)
    if answer:
        return answer
    return "I’m not sure about that. Please ask a question related to The Daily Dish."

# --- Streamlit UI ---
st.set_page_config(page_title="The Daily Dish Chatbot", page_icon="🍽️")

st.title("🍽️ The Daily Dish Chatbot")
st.markdown("Ask me about **The Daily Dish** menu, reservations, or even the local **weather**!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is on the menu?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    response = get_chatbot_response(prompt)
    
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

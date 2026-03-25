import streamlit as st
import os
import urllib.request
import nltk

from agents import MemoryAgent, WeatherAgent, DailyDishAgent, QueryProcessor
from utils import load_faq_pdf, parse_faq, route_query, extract_city

# --- NLTK Setup ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download("punkt")

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
    API_KEY = os.environ.get("OPENWEATHER_API_KEY")
    if not API_KEY:
        try:
            API_KEY = st.secrets.get("OPENWEATHER_API_KEY")
        except Exception:
            pass
            
    if not API_KEY:
        st.error("Missing OpenWeather API Key. Please add OPENWEATHER_API_KEY to your environment variables or secrets.")
    memory_agent = MemoryAgent()
    weather_agent = WeatherAgent(API_KEY, memory_agent)
    daily_dish_agent = DailyDishAgent(faq_questions, faq_answers)
    query_processor = QueryProcessor()
    
    return weather_agent, daily_dish_agent, query_processor

weather_agent, daily_dish_agent, query_processor = setup_agents()

# --- Chatbot Logic ---
def get_chatbot_response(user_question):
    route = route_query(user_question)
    processed = query_processor.process(user_question)
    
    if route == "weather":
        city = extract_city(user_question, default_city="New York")
        return weather_agent.answer(city)
    
    answer = daily_dish_agent.answer(processed)
    if answer:
        return answer
    return "I’m not sure about that. Please ask a question related to The Daily Dish."

# --- Streamlit UI ---
st.set_page_config(page_title="The Daily Dish Chatbot", page_icon="🍽️")

with st.sidebar:
    st.header("⚙️ Settings")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

st.title("🍽️ The Daily Dish Chatbot")
st.markdown("Ask me about **The Daily Dish** menu, reservations, or even the local **weather**!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "👩‍🍳"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is on the menu?"):
    # Display user message in chat message container
    st.chat_message("user", avatar="👤").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    response = get_chatbot_response(prompt)
    
    # Display assistant response in chat message container
    with st.chat_message("assistant", avatar="👩‍🍳"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

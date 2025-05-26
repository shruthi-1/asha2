import os
import google.generativeai as genai
from dotenv import load_dotenv
from knowledgebase import asha_topics


load_dotenv()

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("❌ API Key not found. Please create a .env file with API_KEY=your_key")

# --- Initialize Gemini Client ---
client = genai.Client(api_key=api_key)


def is_topic_found(query):
    query_lower = query.lower()
    for keyword in asha_topics:
        if keyword in query_lower:
            return asha_topics[keyword]
    return None


def ask_gemini(user_input):
    predefined_response = is_topic_found(user_input)
    if predefined_response:
        return predefined_response

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_input
    )

    return response.text.strip()

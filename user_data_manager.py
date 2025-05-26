import os
import google.generativeai as genai
from dotenv import load_dotenv
from knowledgebase import asha_topics
import re

load_dotenv()

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("❌ API Key not found. Please create a .env file with API_KEY=your_key")

# --- Initialize Gemini Client with better error handling ---
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    test_response = model.generate_content("Hello")
    print("✅ Gemini API connection successful")
except Exception as e:
    print(f"❌ Failed to initialize Gemini API: {str(e)}")
    raise

SENSITIVE_KEYWORDS = [
    "women are superior", "men are inferior", "gender superiority", "gender war",
    "feminist extremism", "hate men", "gender bias", "political debate",
    "controversial gender", "gender discrimination arguments"
]

INAPPROPRIATE_TOPICS = [
    "dating advice", "relationship problems", "personal relationships",
    "political opinions", "religious debates", "controversial social issues"
]

def handle_user_input(user_message: str) -> str:
    message_lower = user_message.lower()
    guardrail_phrases = [
        "are you single", "<script>", "aadhar", "social security", "joke about women", 
        "illegal advice", "why don’t women code", "who makes better leaders"
    ]
    if any(phrase in message_lower for phrase in guardrail_phrases):
        return "⚠️ I'm here to support your career journey. Let's keep our conversation respectful and professional. 💜"
    return None

def is_sensitive_content(query):
    query_lower = query.lower()
    for keyword in SENSITIVE_KEYWORDS + INAPPROPRIATE_TOPICS:
        if keyword in query_lower:
            return True
    extreme_patterns = [
        r"women are (the )?best",
        r"men are (the )?worst",
        r"only women (can|should)",
        r"men can't",
        r"gender superiority"
    ]
    for pattern in extreme_patterns:
        if re.search(pattern, query_lower):
            return True
    return False

def is_nonsense_input(text):
    if not text or len(text.strip()) < 3:
        return True
    if re.fullmatch(r"[\W_]+", text):
        return True
    return False

def generate_sensitive_content_response():
    return ("I'm Asha AI, your career guidance assistant! 💼\n\n"
            "I focus specifically on helping women with:\n"
            "• Career development and job opportunities\n"
            "• Skill building and professional growth  \n"
            "• Resume creation and interview preparation\n"
            "• Educational scholarships and programs\n"
            "• Industry insights and career roadmaps\n\n"
            "I don't engage in discussions about gender comparisons, political topics, or personal relationships. "
            "Let me help you with your professional journey instead! What career goals can I support you with today? 🚀")

def is_topic_found(query):
    query_lower = query.lower()
    for keyword in asha_topics:
        if keyword in query_lower:
            return asha_topics[keyword]
    return None

def detect_career_intent(query, context):
    query_lower = query.lower()
    if any(word in query_lower for word in ["resume", "cv", "curriculum vitae", "build resume"]):
        return "resume_building"
    if any(word in query_lower for word in ["learn", "roadmap", "path", "how to start", "career change"]):
        return "roadmap"
    if any(word in query_lower for word in ["job", "opportunity", "hiring", "career", "work", "employment"]):
        return "job_search"
    if any(word in query_lower for word in ["scholarship", "funding", "grant", "financial aid"]):
        return "scholarship"
    return None

def base_prompt(context_text, user_input):
    return f"""You are Asha AI — a warm, supportive, and intelligent career mentor focused on helping women succeed professionally.

Your goal is to provide **friendly, encouraging, and practical** guidance that feels like it's coming from a helpful older sister or coach, NOT a formal chatbot.

🟣 KEY TONE GUIDELINES:
- Use a **friendly, casual tone** (avoid sounding corporate or robotic)
- Speak like you're talking to a real person, with light humor or empathy
- Use **you** instead of \"users\"
- Add appropriate emojis to make responses feel warm and human
- Ask natural follow-up questions when needed

🟡 CONTENT STYLE:
- Keep it **short and helpful** (2–3 paragraphs max)
- Give **concrete examples, tools, websites**
- Avoid listing generic platforms unless you're giving personal insight
- Prioritize **HerKey** and **JobsForHer** in job-related answers
- Suggest free resources, communities, or practical steps
- If a topic is unclear, ask for clarification in a kind way

👥 CONVERSATION CONTEXT:
{context_text}

👩‍💻 USER QUESTION:
{user_input}

🧠 YOUR TASK:
Respond like a real mentor who deeply cares about the user's career growth. Be warm, smart, and real. Avoid overly formal or scripted responses."""

def create_contextual_prompt(user_input, conversation_context):
    context_text = "\n".join(
        f"User: {msg['user']}\nAsha: {msg['asha']}" for msg in conversation_context[-3:]
    ) if conversation_context else "No prior conversation."
    return base_prompt(context_text, user_input)

def ask_gemini(user_input, conversation_context=None):
    if is_nonsense_input(user_input):
        return "🤔 I didn’t quite understand that. Could you ask me something about your career journey?"
    if not user_input.strip() or re.fullmatch(r"[\W_]+", user_input):
        return "🙋‍♀️ I didn’t quite catch that. Could you please ask a career-related question?"
    if is_sensitive_content(user_input):
        return generate_sensitive_content_response()

    contextual_prompt = create_contextual_prompt(user_input, conversation_context or [])
    if contextual_prompt is None:
        return generate_sensitive_content_response()

    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_HIGH_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_HIGH_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_HIGH_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_HIGH_AND_ABOVE"}
        ]

        response = model.generate_content(contextual_prompt, safety_settings=safety_settings)
        if not hasattr(response, "candidates") or not response.candidates:
            fallback = is_topic_found(user_input)
            return fallback if fallback else "🤖 I didn’t get a valid response. Could you try rephrasing your question?"

        # ✅ Use the `.text` attribute directly (Gemini Flash models return `text`)
        response_text = response.text.strip()

        # ✂️ Trim long responses
        if len(response_text) > 800:
            sentences = response_text.split('. ')
            if len(sentences) > 4:
                response_text = '. '.join(sentences[:4]) + ".\n\n💡 Would you like me to elaborate on any specific point?"

        return response_text

    except Exception as e:
        error_msg = str(e).lower()
        if "403" in error_msg or "forbidden" in error_msg:
            return "🔑 API access issue. Please check your API key or permissions."
        elif "quota" in error_msg:
            return "📊 Looks like your usage quota is exceeded. Try again later or check your plan."
        elif "safety" in error_msg:
            return "⚠️ That content might be flagged as unsafe. Let's focus on career questions!"
        else:
            return "⚙️ Something went wrong on my side. Please try again or rephrase your question."

def get_career_suggestions(field=None):
    tech_careers = [
        "Software Developer", "Data Scientist", "UI/UX Designer", "Product Manager",
        "Cybersecurity Analyst", "DevOps Engineer", "AI/ML Engineer", "Quality Assurance Engineer"
    ]
    non_tech_careers = [
        "Digital Marketing Manager", "Content Writer", "HR Business Partner", "Financial Analyst",
        "Project Manager", "Business Analyst", "Sales Manager", "Operations Manager",
        "Graphic Designer", "Social Media Manager", "Customer Success Manager"
    ]
    if field and "tech" in field.lower():
        return tech_careers
    elif field and "non-tech" in field.lower():
        return non_tech_careers
    else:
        return tech_careers + non_tech_careers

def format_roadmap_response(skill, level="beginner"):
    roadmaps = {
        "python": {
            "beginner": [
                "Week 1-2: Python basics, variables, data types",
                "Week 3-4: Control structures, functions",
                "Week 5-6: Data structures (lists, dictionaries)",
                "Week 7-8: File handling, error handling",
                "Week 9-12: Projects - Calculator, To-do app"
            ],
            "intermediate": [
                "Month 1: OOP concepts, classes, inheritance",
                "Month 2: Libraries (pandas, numpy, requests)",
                "Month 3: Web scraping, APIs",
                "Month 4: Database operations (SQLite, PostgreSQL)",
                "Month 5-6: Advanced projects - Web app, data analysis"
            ]
        },
        "data science": {
            "beginner": [
                "Month 1: Python/R basics, statistics",
                "Month 2: Data manipulation (pandas, dplyr)",
                "Month 3: Data visualization (matplotlib, ggplot2)",
                "Month 4: Machine learning basics",
                "Month 5-6: Projects - analysis, predictions"
            ]
        }
    }
    return roadmaps.get(skill.lower(), {}).get(level, [
        "Custom roadmap: Start with fundamentals",
        "Practice regularly with hands-on projects", 
        "Join communities and seek mentorship",
        "Build a portfolio to showcase your skills"
    ])
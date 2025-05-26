import os
import google.generativeai as genai
from dotenv import load_dotenv
from knowledgebase import asha_topics
import time

load_dotenv()

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("❌ API Key not found. Please create a .env file with API_KEY=your_key")

# --- Initialize Gemini Client ---
genai.configure(api_key=api_key)

def is_topic_found(query):
    query_lower = query.lower()
    for keyword in asha_topics:
        if keyword in query_lower:
            return asha_topics[keyword]
    return None

def ask_gemini(user_input):
    """Enhanced Gemini API call with better error handling"""
    predefined_response = is_topic_found(user_input)
    if predefined_response:
        return predefined_response

    try:
        # Try the newer API first
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(user_input)
        return response.text.strip()
    except AttributeError:
        # Fallback for older API version
        try:
            response = genai.generate_text(
                model="models/text-bison-001",
                prompt=user_input,
                temperature=0.7,
                max_output_tokens=1000
            )
            return response.result.strip() if response.result else "I'm having trouble generating a response right now. Please try again."
        except Exception as e:
            return f"I apologize, but I'm experiencing technical difficulties with the AI service. Please try again in a moment. 🌟\n\nTechnical details: {str(e)}"
    except Exception as e:
        # Handle other API errors
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            return "I've reached my daily usage limit. Please try again tomorrow or contact support for assistance. 🌟"
        elif "api" in str(e).lower():
            return "There seems to be an issue with the AI service. Please try again in a few minutes. 🌟"
        else:
            return f"I encountered an unexpected error. Please try rephrasing your question. 🌟\n\nError: {str(e)}"

def enhanced_ask_gemini(user_input, user_context=None):
    """Enhanced version with user context and retry logic"""
    predefined_response = is_topic_found(user_input)
    if predefined_response:
        return predefined_response

    # Enhanced prompt with context
    enhanced_prompt = f"""
You are Asha AI, an empowering career assistant specifically designed to help women advance their careers. 
You are supportive, knowledgeable, and provide actionable advice.

{f"User context: {user_context}" if user_context else ""}

User question: {user_input}

Please provide a helpful, encouraging response focused on women's career development, opportunities, and empowerment.
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Try the newer API first
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(enhanced_prompt)
            
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            else:
                raise Exception("Empty response from API")
                
        except AttributeError:
            # Fallback for older API version
            try:
                response = genai.generate_text(
                    model="models/text-bison-001",
                    prompt=enhanced_prompt,
                    temperature=0.7,
                    max_output_tokens=1000
                )
                if response and response.result:
                    return response.result.strip()
                else:
                    raise Exception("Empty response from fallback API")
            except Exception as fallback_error:
                if attempt == max_retries - 1:
                    return handle_api_error(fallback_error)
                time.sleep(1)  # Wait before retry
                
        except Exception as e:
            if attempt == max_retries - 1:
                return handle_api_error(e)
            time.sleep(1)  # Wait before retry
    
    return "I'm experiencing technical difficulties. Please try again in a moment. 🌟"

def handle_api_error(error):
    """Centralized error handling for API calls"""
    error_str = str(error).lower()
    
    if "quota" in error_str or "limit" in error_str:
        return """I've reached my daily usage limit for now. Here are some things you can try:

🌟 **Alternative Actions:**
- Browse the quick action buttons in the sidebar for instant career tips
- Try asking a different question in a few hours
- Contact support if you need immediate assistance

💪 **In the meantime, remember:**
- You have unique strengths that make you valuable
- Every challenge is an opportunity to grow
- Your career journey is worth the wait!

Thank you for your patience! 🌸"""
    
    elif "api" in error_str or "service" in error_str:
        return """I'm having a temporary connection issue with my AI brain! 🤖

🔧 **Quick fixes to try:**
- Refresh the page and try again
- Check your internet connection
- Try asking your question in a different way

💡 **While I'm getting back online:**
- Use the sidebar quick actions for instant career guidance
- Browse through our knowledge base topics
- Take a moment to update your profile for better personalized advice

I'll be back to full power soon! 🌟"""
    
    else:
        return f"""I encountered an unexpected hiccup, but don't let that stop your career momentum! 🚀

🌟 **Here's what you can do:**
- Try rephrasing your question
- Use the quick action buttons for instant guidance
- Refresh the page if the issue persists

💪 **Remember:** Every successful woman has faced technical challenges - it's how we adapt and keep moving forward that counts!

Technical note: {str(error)[:100]}... (Contact support if this persists)"""

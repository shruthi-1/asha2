import streamlit as st
from chatbot import enhanced_ask_gemini
from auth import GoogleAuthenticator, validate_google_email, handle_oauth_callback, reset_auth_state
import datetime
import time
import re
import json
import os
import uuid

# --- Streamlit Config ---
st.set_page_config(
    page_title="Asha AI - Empowering Women's Careers", 
    page_icon="🌸", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Google OAuth Configuration ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "915155637703-pgj1r71gbctmk0018s8dif1gugf3ld0k.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = "https://nby3lhwfkpzxcdkiixxjfq.streamlit.app/"

# Initialize Google Authenticator
google_auth = GoogleAuthenticator(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)

# --- Session State Init ---
for key, default in {
    "page": "login",
    "logged_in": False,
    "email": None,
    "profile_picture": None,
    "chat_history": [],
    "chat_dates": [],
    "name": "",
    "user_data_file": None,
    "conversation_context": [],
    "career_stage": "",
    "interests": [],
    "oauth_state": None,
    "google_user_info": None,
    "authenticated": False,
    "user_info": None,
    "credentials": None,
    "all_chats": {},  # Dictionary to store multiple chat sessions
    "current_chat_id": None,
    "show_debug": False  # Hidden debug option
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Enhanced High-Contrast Light Theme ---
light_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');

/* Base styles with maximum contrast */
.stApp { 
    background: #FFFFFF; 
    color: #000000; 
    font-family: 'Inter', 'Poppins', sans-serif;
}

/* Sidebar with high contrast */
section[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, #1A0B2E 0%, #2D1B69 50%, #4A148C 100%);
    border-right: 4px solid #E91E63;
}

section[data-testid="stSidebar"] * {
    color: #FFFFFF !important;
    font-weight: 600;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #FFE0E6 !important;
    font-weight: 700;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}

/* Maximum contrast chat bubbles */
.chat-container { 
    display: flex; 
    flex-direction: column; 
    gap: 20px; 
    padding: 25px;
}

.chat-bubble { 
    max-width: 75%; 
    padding: 24px 32px; 
    margin: 12px; 
    border-radius: 20px; 
    font-size: 17px; 
    font-weight: 500;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
    line-height: 1.7;
    border: 3px solid;
}

.user-bubble { 
    background: #E91E63; 
    color: #FFFFFF; 
    align-self: flex-end; 
    border-bottom-right-radius: 8px;
    border-color: #AD1457;
    font-weight: 600;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.bot-bubble { 
    background: #FFFFFF; 
    color: #000000; 
    align-self: flex-start; 
    border-color: #000000;
    border-bottom-left-radius: 8px;
    font-weight: 500;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* High contrast buttons */
.stButton > button {
    background: #E91E63;
    color: #FFFFFF;
    border: 3px solid #AD1457;
    border-radius: 12px;
    font-weight: 700;
    font-size: 16px;
    padding: 14px 28px;
    transition: all 0.3s ease;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.stButton > button:hover {
    background: #AD1457;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(233, 30, 99, 0.5);
    border-color: #880E4F;
}

/* High contrast input fields */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    background-color: #FFFFFF;
    color: #000000;
    border: 3px solid #000000;
    border-radius: 8px;
    font-weight: 600;
    font-size: 16px;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div > select:focus {
    border-color: #E91E63;
    box-shadow: 0 0 0 3px rgba(233, 30, 99, 0.3);
}

/* Enhanced quick action cards with maximum contrast */
.quick-action {
    background: #FFFFFF;
    border: 4px solid #000000;
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    color: #000000;
    font-weight: 700;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
}

.quick-action:hover {
    background: #E91E63;
    color: #FFFFFF;
    transform: scale(1.05);
    box-shadow: 0 10px 30px rgba(233, 30, 99, 0.4);
    border-color: #AD1457;
}

/* Chat navigation cards */
.chat-nav-card {
    background: #F8F9FA;
    border: 3px solid #000000;
    border-radius: 12px;
    padding: 15px;
    margin: 8px 0;
    cursor: pointer;
    transition: all 0.3s ease;
    color: #000000;
    font-weight: 600;
}

.chat-nav-card:hover {
    background: #E91E63;
    color: #FFFFFF;
    border-color: #AD1457;
}

.chat-nav-card.active {
    background: #E91E63;
    color: #FFFFFF;
    border-color: #AD1457;
}

/* Maximum contrast headers */
h1, h2, h3 {
    color: #000000 !important;
    font-weight: 800;
    text-shadow: none;
}

/* High contrast messages */
.stSuccess {
    background-color: #D4EDDA;
    color: #155724;
    border: 3px solid #28A745;
    font-weight: 700;
}

.stError {
    background-color: #F8D7DA;
    color: #721C24;
    border: 3px solid #DC3545;
    font-weight: 700;
}

.stInfo {
    background-color: #D1ECF1;
    color: #0C5460;
    border: 3px solid #17A2B8;
    font-weight: 700;
}

/* Hero section with high contrast */
.hero-section {
    background: linear-gradient(135deg, #E91E63 0%, #9C27B0 50%, #673AB7 100%);
    color: #FFFFFF;
    padding: 40px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 30px;
    box-shadow: 0 12px 35px rgba(233, 30, 99, 0.4);
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

.feature-card {
    background: #FFFFFF;
    border: 4px solid #000000;
    border-radius: 15px;
    padding: 25px;
    margin: 15px;
    text-align: center;
    color: #000000;
    font-weight: 600;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

/* Profile section with high contrast */
.profile-section {
    background: #FFFFFF;
    border: 3px solid #000000;
    border-radius: 15px;
    padding: 20px;
    margin-bottom: 20px;
    text-align: center;
    color: #000000;
    font-weight: 600;
}

/* Enhanced typography for maximum readability */
p, div, span, label {
    color: #000000 !important;
    font-weight: 500;
    line-height: 1.7;
}

/* Sidebar text overrides */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
    color: #FFFFFF !important;
}

/* Responsive design */
@media (max-width: 768px) {
    .chat-bubble {
        max-width: 90%;
        padding: 18px 22px;
        font-size: 15px;
    }
    
    .quick-action {
        padding: 16px;
        margin: 8px 0;
    }
}
</style>
"""

dark_theme = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Inter:wght@400;500;600&display=swap');

.stApp { 
    background: linear-gradient(135deg, #0D0D0D 0%, #1A0B2E 50%, #2D1B69 100%); 
    color: #FFFFFF; 
    font-family: 'Inter', 'Poppins', sans-serif;
}

section[data-testid="stSidebar"] { 
    background: linear-gradient(180deg, #000000 0%, #1A0B2E 50%, #2D1B69 100%);
    border-right: 4px solid #E91E63;
}

.chat-bubble { 
    max-width: 75%; 
    padding: 24px 32px; 
    margin: 12px; 
    border-radius: 20px; 
    font-size: 17px; 
    font-weight: 500;
    box-shadow: 0 8px 25px rgba(233, 30, 99, 0.3);
    line-height: 1.7;
    border: 3px solid;
}

.user-bubble { 
    background: #E91E63; 
    color: #FFFFFF; 
    align-self: flex-end; 
    border-color: #AD1457;
    font-weight: 600;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
}

.bot-bubble { 
    background: linear-gradient(135deg, #2D1B69 0%, #4A148C 100%); 
    color: #FFFFFF; 
    align-self: flex-start; 
    border-color: #E91E63;
    font-weight: 500;
}

.stButton > button {
    background: #E91E63;
    color: #FFFFFF;
    border: 3px solid #AD1457;
    border-radius: 12px;
    font-weight: 700;
    font-size: 16px;
    padding: 14px 28px;
}

.quick-action {
    background: linear-gradient(135deg, #2D1B69 0%, #4A148C 100%);
    border: 4px solid #E91E63;
    color: #FFFFFF;
    font-weight: 700;
}

.chat-nav-card {
    background: linear-gradient(135deg, #2D1B69 0%, #4A148C 100%);
    border: 3px solid #E91E63;
    color: #FFFFFF;
    font-weight: 600;
}

.hero-section {
    background: linear-gradient(135deg, #E91E63 0%, #9C27B0 50%, #673AB7 100%);
    color: #FFFFFF;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}

h1, h2, h3 {
    color: #FFFFFF !important;
    font-weight: 800;
}
</style>
"""

def save_user_data():
    """Enhanced save function with chat session support"""
    if st.session_state.email:
        filename = f"user_data_{st.session_state.email.replace('@', '_').replace('.', '_')}.json"
        st.session_state.user_data_file = filename
        data = {
            "email": st.session_state.email,
            "name": st.session_state.name,
            "chat_history": st.session_state.chat_history,
            "chat_dates": st.session_state.chat_dates,
            "conversation_context": st.session_state.conversation_context,
            "career_stage": st.session_state.career_stage,
            "interests": st.session_state.interests,
            "profile_picture": st.session_state.profile_picture,
            "all_chats": st.session_state.all_chats,
            "current_chat_id": st.session_state.current_chat_id
        }
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Error saving data: {e}")

def load_user_data():
    """Enhanced load function with chat session support"""
    if st.session_state.email:
        filename = f"user_data_{st.session_state.email.replace('@', '_').replace('.', '_')}.json"
        st.session_state.user_data_file = filename
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.session_state.chat_history = data.get("chat_history", [])
                st.session_state.chat_dates = data.get("chat_dates", [])
                st.session_state.conversation_context = data.get("conversation_context", [])
                st.session_state.name = data.get("name", st.session_state.name)
                st.session_state.career_stage = data.get("career_stage", "")
                st.session_state.interests = data.get("interests", [])
                st.session_state.profile_picture = data.get("profile_picture", None)
                st.session_state.all_chats = data.get("all_chats", {})
                st.session_state.current_chat_id = data.get("current_chat_id", None)
        except Exception as e:
            st.error(f"Error loading data: {e}")

def create_new_chat():
    """Create a new chat session"""
    # Save current chat if it exists
    if st.session_state.current_chat_id and st.session_state.chat_history:
        st.session_state.all_chats[st.session_state.current_chat_id] = {
            "title": get_chat_title(st.session_state.chat_history),
            "history": st.session_state.chat_history.copy(),
            "dates": st.session_state.chat_dates.copy(),
            "context": st.session_state.conversation_context.copy(),
            "created": datetime.datetime.now().isoformat()
        }
    
    # Create new chat
    new_chat_id = str(uuid.uuid4())
    st.session_state.current_chat_id = new_chat_id
    st.session_state.chat_history = []
    st.session_state.chat_dates = []
    st.session_state.conversation_context = []
    
    save_user_data()

def load_chat(chat_id):
    """Load a specific chat session"""
    if chat_id in st.session_state.all_chats:
        # Save current chat first
        if st.session_state.current_chat_id and st.session_state.chat_history:
            st.session_state.all_chats[st.session_state.current_chat_id] = {
                "title": get_chat_title(st.session_state.chat_history),
                "history": st.session_state.chat_history.copy(),
                "dates": st.session_state.chat_dates.copy(),
                "context": st.session_state.conversation_context.copy(),
                "created": datetime.datetime.now().isoformat()
            }
        
        # Load selected chat
        chat_data = st.session_state.all_chats[chat_id]
        st.session_state.current_chat_id = chat_id
        st.session_state.chat_history = chat_data["history"]
        st.session_state.chat_dates = chat_data["dates"]
        st.session_state.conversation_context = chat_data["context"]
        
        save_user_data()

def get_chat_title(chat_history):
    """Generate a title for the chat based on first user message"""
    if chat_history:
        first_message = next((msg[1] for msg in chat_history if msg[0] == 'user'), "New Chat")
        return first_message[:50] + "..." if len(first_message) > 50 else first_message
    return "New Chat"

def get_query_params():
    """Safely get query parameters"""
    try:
        # Try new method first (Streamlit >= 1.30)
        return dict(st.query_params)
    except AttributeError:
        try:
            # Fallback for older versions
            return st.experimental_get_query_params()
        except:
            return {}

def login_page():
    """Enhanced login page with cleaner OAuth integration"""
    
    # Check if user is already authenticated via OAuth
    if st.session_state.get('authenticated') and st.session_state.get('user_info'):
        user_info = st.session_state.user_info
        st.session_state.logged_in = True
        st.session_state.email = user_info.get('email')
        st.session_state.name = user_info.get('name', '')
        st.session_state.profile_picture = user_info.get('picture')
        st.session_state.page = "chat"
        load_user_data()
        st.success(f"Welcome back, {st.session_state.name}! 🌟")
        st.rerun()
    
    # Handle OAuth callback
    oauth_result = handle_oauth_callback(google_auth)
    if oauth_result is True:
        return
    elif oauth_result is False:
        pass
    
    # Hero section
    st.markdown("""
    <div class="hero-section">
        <h1>🌸 Welcome to Asha AI 🌸</h1>
        <h2>Empowering Women to Shape Their Future</h2>
        <p style="font-size: 18px; margin-top: 20px;">
            Break barriers, build careers, and become the leader you're meant to be
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Logo section
    try:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image("asa.png", width=200)
    except Exception:
        st.markdown("<div style='text-align: center; font-size: 64px;'>👩‍💼💜</div>", unsafe_allow_html=True)

    # Login section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🚀 Join the Movement")
        
        # Google OAuth Login
        if st.button("🔵 Continue with Google", key="google_login", use_container_width=True):
            try:
                auth_url = google_auth.get_authorization_url()
                if auth_url:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                    st.info("Redirecting to Google authentication...")
                    st.markdown(f"[If not redirected automatically, click here]({auth_url})")
                else:
                    st.error("Failed to generate authentication URL. Please check OAuth configuration.")
            except Exception as e:
                st.error(f"Google OAuth setup error: {str(e)}")
                st.info("Please check your Google OAuth credentials.")
        
        # Debug section (hidden by default)
        if st.session_state.get('show_debug', False):
            if st.checkbox("Show Debug Info", False, key="show_debug_info"):
                st.write("Environment Variables:")
                st.write(f"CLIENT_ID set: {'Yes' if GOOGLE_CLIENT_ID else 'No'}")
                st.write(f"CLIENT_SECRET set: {'Yes' if GOOGLE_CLIENT_SECRET else 'No'}")
                st.write(f"REDIRECT_URI: {REDIRECT_URI}")
                
                if st.button("Reset OAuth State"):
                    reset_auth_state()
        
        st.markdown("**OR**")
        
        # Email login
        email = st.text_input("📧 Enter your Email Address:", placeholder="yourname@gmail.com")
        st.session_state.name = st.text_input("👤 Enter your Name:", value=st.session_state.name, placeholder="Your full name")
        
        # Career stage selection
        career_stage = st.selectbox(
            "🎯 Where are you in your career journey?",
            ["", "Student/Recent Graduate", "Career Changer", "Mid-level Professional", "Senior Professional", "Entrepreneur/Freelancer"]
        )
        
        # Interests selection
        interests = st.multiselect(
            "💼 What are your areas of interest?",
            ["Technology", "Data Science", "Marketing", "Finance", "Healthcare", "Education", "Creative Arts", "Consulting", "Entrepreneurship", "Non-Profit"]
        )

        if st.button("✨ Start Your Journey", key="email_login", use_container_width=True):
            if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.career_stage = career_stage
                st.session_state.interests = interests
                st.session_state.page = "chat"
                load_user_data()
                save_user_data()
                st.success(f"Welcome {st.session_state.name or 'Queen'}! 👑")
                st.rerun()
            else:
                st.error("Please enter a valid email address.")

    # Features showcase
    st.markdown("---")
    st.markdown("### 🌟 Why Choose Asha AI")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>💼 Career Acceleration</h3>
            <p>Personalized career roadmaps designed specifically for women's unique journey in the professional world</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>📄 Resume Mastery</h3>
            <p>AI-powered resume building that highlights your strengths and gets you noticed by top employers</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🎓 Opportunity Alerts</h3>
            <p>Stay updated with scholarships, grants, and opportunities specifically for women in your field</p>
        </div>
        """, unsafe_allow_html=True)

    # Success stories section
    st.markdown("---")
    st.markdown("### 💪 Success Stories")
    st.markdown("""
    <div style="background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%); padding: 30px; border-radius: 15px; margin: 20px 0; border: 3px solid #9C27B0;">
        <blockquote style="font-style: italic; font-size: 18px; color: #4A148C; font-weight: 600;">
        "Asha AI helped me transition from marketing to tech. Within 6 months, I landed my dream job as a Product Manager at a leading startup!"
        </blockquote>
        <p style="text-align: right; font-weight: bold; color: #7B1FA2;">- Priya S., Product Manager</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🔒 Your privacy and data security are our top priorities. We're committed to empowering women while protecting your personal information.")

def chat_page():
    # Load user data on page load
    if not st.session_state.chat_history and st.session_state.email:
        load_user_data()
    
    with st.sidebar:
        # Enhanced profile section
        st.markdown("### 👩‍💼 Your Profile")
        
        # Profile picture
        if st.session_state.profile_picture:
            st.image(st.session_state.profile_picture, width=100)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=100)
        
        # User info
        st.markdown(f"""
        <div class="profile-section">
            <h4>{st.session_state.name or 'Career Explorer'}</h4>
            <p>📧 {st.session_state.email}</p>
            <p>🎯 {st.session_state.career_stage}</p>
        </div>
        """, unsafe_allow_html=True)

        # Chat Management
        st.markdown("---")
        st.markdown("### 💬 Chat Sessions")
        
        # New Chat Button
        if st.button("➕ Create New Chat", use_container_width=True):
            create_new_chat()
            st.rerun()
        
        # Display existing chats
        if st.session_state.all_chats:
            st.markdown("**Previous Chats:**")
            for chat_id, chat_data in reversed(list(st.session_state.all_chats.items())):
                chat_title = chat_data.get("title", "Untitled Chat")
                is_active = chat_id == st.session_state.current_chat_id
                
                # Chat navigation card
                if st.button(f"{'🟢' if is_active else '💬'} {chat_title}", key=f"chat_{chat_id}", use_container_width=True):
                    if not is_active:
                        load_chat(chat_id)
                        st.rerun()

        # Settings
        st.markdown("---")
        st.title("⚙️ Settings")
        theme_mode = st.radio("🎨 Choose Theme:", ("Light Mode", "Dark Mode"), index=1)

        # Enhanced Quick Actions
        st.markdown("### 🚀 Quick Actions")
        
        quick_actions = [
            ("💼 Find Women-Friendly Jobs", "Show me latest job opportunities at companies with great diversity and inclusion policies"),
            ("📄 Build Winning Resume", "I need help creating a professional resume that highlights my unique strengths as a woman in my field"),
            ("🎓 Women's Scholarships", "Tell me about current scholarships and grants specifically for women in my area of interest"),
            ("🗺️ Career Roadmap", "I want to create a strategic career roadmap that considers work-life balance and growth opportunities"),
            ("💪 Salary Negotiation", "Help me prepare for salary negotiation and know my worth in the market"),
            ("🌐 Networking Tips", "Give me strategies for building professional networks as a woman in my industry")
        ]
        
        for button_text, prompt in quick_actions:
            if st.button(button_text, use_container_width=True):
                process_user_input(prompt)

        st.markdown("---")
        if st.button("🧹 Clear Current Chat", use_container_width=True):
            st.session_state.chat_history.clear()
            st.session_state.chat_dates.clear()
            st.session_state.conversation_context.clear()
            save_user_data()
            st.success("Current chat cleared!")
            st.rerun()

        if st.button("🚪 Logout", use_container_width=True):
            save_user_data()
            # Clear session state
            auth_keys = [
                'page', 'logged_in', 'email', 'profile_picture', 'name', 
                'google_user_info', 'authenticated', 'user_info', 'credentials',
                'oauth_state', 'oauth_state_timestamp', 'oauth_states'
            ]
            for key in auth_keys:
                st.session_state.pop(key, None)
            st.session_state.page = "login"
            st.rerun()

    # Apply theme
    if theme_mode == "Light Mode":
        st.markdown(light_theme, unsafe_allow_html=True)
    else:
        st.markdown(dark_theme, unsafe_allow_html=True)

    # Main chat interface
    st.title("💜 Asha AI - Your Career Companion")
    st.markdown("*Empowering women to achieve their professional dreams*")

    # Welcome message for new users
    if not st.session_state.chat_history and not st.session_state.current_chat_id:
        st.markdown(f"""
        <div class="hero-section">
            <h3>👋 Hello {st.session_state.name or 'Beautiful'}!</h3>
            <p>I'm Asha, your AI career companion. I'm here to help you navigate your professional journey with confidence and strength.</p>
            <p>💡 <strong>Pro tip:</strong> Try asking me about career advice, resume building, salary negotiation, or finding opportunities specifically for women!</p>
        </div>
        """, unsafe_allow_html=True)

    # Display chat history
    if st.session_state.chat_history:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for i, (sender, message) in enumerate(st.session_state.chat_history):
            timestamp = st.session_state.chat_dates[i] if i < len(st.session_state.chat_dates) else ""
            
            if sender == "user":
                st.markdown(f"""
                <div class="chat-bubble user-bubble">
                    <strong>You:</strong> {message}
                    <br><small style="opacity: 0.8;">{timestamp}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-bubble bot-bubble">
                    <strong>Asha:</strong> {message}
                    <br><small style="opacity: 0.8;">{timestamp}</small>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask me anything about your career journey... 💪")
    
    if user_input:
        process_user_input(user_input)

def process_user_input(user_input):
    """Process user input and generate AI response"""
    try:
        # Add user message to chat
        timestamp = datetime.datetime.now().strftime("%I:%M %p")
        st.session_state.chat_history.append(("user", user_input))
        st.session_state.chat_dates.append(timestamp)
        
        # Build context for the AI
        context = f"""
        User Profile:
        - Name: {st.session_state.name}
        - Email: {st.session_state.email}
        - Career Stage: {st.session_state.career_stage}
        - Interests: {', '.join(st.session_state.interests)}
        
        You are Asha AI, a career companion specifically designed to empower women in their professional journeys. 
        You should:
        1. Be supportive, encouraging, and empowering
        2. Provide practical career advice
        3. Consider unique challenges women face in the workplace
        4. Offer resources and opportunities specifically for women
        5. Be professional but warm and approachable
        6. Use encouraging language and emojis appropriately
        
        Recent conversation context:
        {' '.join([f"{sender}: {msg}" for sender, msg in st.session_state.conversation_context[-10:]])}
        
        Current user question: {user_input}
        """
        
        # Show thinking indicator
        with st.spinner("Asha is thinking... 💭"):
            # Get AI response
            ai_response = enhanced_ask_gemini(context)
            
            if ai_response:
                # Add AI response to chat
                st.session_state.chat_history.append(("assistant", ai_response))
                st.session_state.chat_dates.append(timestamp)
                
                # Update conversation context
                st.session_state.conversation_context.extend([
                    ("user", user_input),
                    ("assistant", ai_response)
                ])
                
                # Keep context manageable (last 20 exchanges)
                if len(st.session_state.conversation_context) > 40:
                    st.session_state.conversation_context = st.session_state.conversation_context[-40:]
                
                # Create new chat session if this is the first message
                if not st.session_state.current_chat_id:
                    st.session_state.current_chat_id = str(uuid.uuid4())
            else:
                st.session_state.chat_history.append(("assistant", "I apologize, but I'm having trouble connecting right now. Please try again in a moment! 💜"))
                st.session_state.chat_dates.append(timestamp)
        
        # Save user data
        save_user_data()
        st.rerun()
        
    except Exception as e:
        st.error(f"Oops! Something went wrong: {str(e)}")
        # Add error message to chat
        timestamp = datetime.datetime.now().strftime("%I:%M %p")
        st.session_state.chat_history.append(("assistant", "I'm sorry, I encountered an technical issue. Please try asking your question again! 💜"))
        st.session_state.chat_dates.append(timestamp)
        save_user_data()

def main():
    """Main application logic"""
    # Initialize chat session if needed
    if st.session_state.logged_in and not st.session_state.current_chat_id and not st.session_state.chat_history:
        st.session_state.current_chat_id = str(uuid.uuid4())
    
    # Page routing
    if st.session_state.page == "login" or not st.session_state.logged_in:
        login_page()
    elif st.session_state.page == "chat" and st.session_state.logged_in:
        chat_page()
    else:
        # Fallback to login
        st.session_state.page = "login"
        st.session_state.logged_in = False
        st.rerun()

# Run the application
if __name__ == "__main__":
    main()

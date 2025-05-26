import streamlit as st
from chatbot import ask_gemini
from auth import GoogleAuthenticator, validate_google_email, handle_oauth_callback, reset_auth_state
import datetime
import re
import uuid

# --- Streamlit Config ---
st.set_page_config(
    page_title="Asha AI - Empowering Women's Careers", 
    page_icon="🌸", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Google OAuth Configuration ---
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = st.secrets.get("REDIRECT_URI", "https://your-app-name.streamlit.app/")

# Initialize Google Authenticator
google_auth = None
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        google_auth = GoogleAuthenticator(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI)
    except Exception as e:
        st.warning(f"Google OAuth not configured: {e}")

# --- Initialize Session State ---
def init_session_state():
    defaults = {
        "page": "login",
        "logged_in": False,
        "email": None,
        "profile_picture": None,
        "chat_history": [],
        "name": "",
        "career_stage": "",
        "interests": [],
        "authenticated": False,
        "user_info": None,
        "current_chat_id": None,
        "all_chats": {},
        "processing": False  # Prevent multiple processing
    }
    
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# --- Styling ---
def apply_theme():
    st.markdown("""
    <style>
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #1a0d2e 0%, #2d1b3d 50%, #1a0d2e 100%);
        color: #ffffff;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #2d1b3d 0%, #1a0d2e 100%);
        border-right: 2px solid #ff6b9d;
    }
    
    /* Main content area */
    .main .block-container {
        background: rgba(45, 27, 61, 0.3);
        border-radius: 15px;
        padding: 2rem;
        border: 1px solid rgba(255, 107, 157, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ff6b9d !important;
        text-shadow: 0 0 10px rgba(255, 107, 157, 0.3);
        font-weight: bold;
    }
    
    /* Text elements */
    p, div, span, label {
        color: #ffffff !important;
    }
    
    /* Input fields */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #2d1b3d !important;
        color: #ffffff !important;
        border: 2px solid #ff6b9d !important;
        border-radius: 8px !important;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #c147d6 !important;
        box-shadow: 0 0 10px rgba(193, 71, 214, 0.5) !important;
    }
    
    /* Buttons */
    .stButton button {
        background: linear-gradient(45deg, #ff6b9d, #c147d6) !important;
        color: white !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 0.75rem 2rem !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(255, 107, 157, 0.3) !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 107, 157, 0.5) !important;
    }
    
    /* Metrics and info boxes */
    .metric-container, [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(255, 107, 157, 0.1), rgba(193, 71, 214, 0.1)) !important;
        border: 2px solid #ff6b9d !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        backdrop-filter: blur(5px) !important;
    }
    
    /* Success/Info/Warning/Error messages */
    .stSuccess, .stInfo, .stWarning, .stError {
        background: rgba(45, 27, 61, 0.8) !important;
        border-left: 4px solid #ff6b9d !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    
    /* Dataframes and tables */
    .dataframe {
        background-color: #2d1b3d !important;
        color: #ffffff !important;
        border: 1px solid #ff6b9d !important;
    }
    
    .dataframe th {
        background: linear-gradient(45deg, #ff6b9d, #c147d6) !important;
        color: white !important;
        font-weight: bold !important;
    }
    
    .dataframe td {
        background-color: rgba(45, 27, 61, 0.5) !important;
        color: #ffffff !important;
        border-bottom: 1px solid rgba(255, 107, 157, 0.2) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(45, 27, 61, 0.5) !important;
        border-radius: 10px !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #ffffff !important;
        border-radius: 8px !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 107, 157, 0.2) !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, #ff6b9d, #c147d6) !important;
        color: white !important;
    }
    
    /* Progress bars */
    .stProgress .st-bo {
        background: linear-gradient(90deg, #ff6b9d, #c147d6) !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(45, 27, 61, 0.6) !important;
        color: #ff6b9d !important;
        border: 1px solid #ff6b9d !important;
        border-radius: 8px !important;
    }
    
    .streamlit-expanderContent {
        background: rgba(26, 13, 46, 0.8) !important;
        border: 1px solid rgba(255, 107, 157, 0.2) !important;
        border-radius: 0 0 8px 8px !important;
    }
    
    /* Selectbox dropdown */
    .stSelectbox [data-baseweb="select"] {
        background-color: #2d1b3d !important;
        border: 2px solid #ff6b9d !important;
    }
    
    /* File uploader */
    .stFileUploader section {
        background: rgba(45, 27, 61, 0.5) !important;
        border: 2px dashed #ff6b9d !important;
        border-radius: 12px !important;
    }
    
    /* Checkbox and radio */
    .stCheckbox label, .stRadio label {
        color: #ffffff !important;
    }
    
    /* Slider */
    .stSlider .st-bf {
        background: linear-gradient(90deg, #ff6b9d, #c147d6) !important;
    }
    
    /* Code blocks */
    .stCodeBlock {
        background-color: #1a0d2e !important;
        border: 1px solid #ff6b9d !important;
        border-radius: 8px !important;
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a0d2e;
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #ff6b9d, #c147d6);
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(45deg, #c147d6, #ff6b9d);
    }
    
    /* High contrast links */
    a {
        color: #ff6b9d !important;
        text-decoration: none !important;
        font-weight: bold !important;
    }
    
    a:hover {
        color: #c147d6 !important;
        text-shadow: 0 0 5px rgba(193, 71, 214, 0.5) !important;
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    </style>
    """, unsafe_allow_html=True)
# --- Data Management ---
def save_user_data():
    if st.session_state.email:
        user_data = {
            "email": st.session_state.email,
            "name": st.session_state.name,
            "chat_history": st.session_state.chat_history,
            "career_stage": st.session_state.career_stage,
            "interests": st.session_state.interests,
            "profile_picture": st.session_state.profile_picture,
            "all_chats": st.session_state.all_chats,
            "current_chat_id": st.session_state.current_chat_id
        }
        st.session_state[f"user_data_{st.session_state.email}"] = user_data

def load_user_data():
    if st.session_state.email:
        user_data_key = f"user_data_{st.session_state.email}"
        if user_data_key in st.session_state:
            data = st.session_state[user_data_key]
            st.session_state.chat_history = data.get("chat_history", [])
            st.session_state.name = data.get("name", st.session_state.name)
            st.session_state.career_stage = data.get("career_stage", "")
            st.session_state.interests = data.get("interests", [])
            st.session_state.profile_picture = data.get("profile_picture", None)
            st.session_state.all_chats = data.get("all_chats", {})
            st.session_state.current_chat_id = data.get("current_chat_id", None)

def create_new_chat():
    if st.session_state.current_chat_id and st.session_state.chat_history:
        st.session_state.all_chats[st.session_state.current_chat_id] = {
            "title": get_chat_title(st.session_state.chat_history),
            "history": st.session_state.chat_history.copy(),
            "created": datetime.datetime.now().isoformat()
        }
    
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    save_user_data()

def load_chat(chat_id):
    if chat_id in st.session_state.all_chats:
        if st.session_state.current_chat_id and st.session_state.chat_history:
            st.session_state.all_chats[st.session_state.current_chat_id] = {
                "title": get_chat_title(st.session_state.chat_history),
                "history": st.session_state.chat_history.copy(),
                "created": datetime.datetime.now().isoformat()
            }
        
        chat_data = st.session_state.all_chats[chat_id]
        st.session_state.current_chat_id = chat_id
        st.session_state.chat_history = chat_data["history"]
        save_user_data()

def get_chat_title(chat_history):
    if chat_history:
        first_message = next((msg[1] for msg in chat_history if msg[0] == 'user'), "New Chat")
        return first_message[:40] + "..." if len(first_message) > 40 else first_message
    return "New Chat"

# --- Login Page ---
def login_page():
    apply_theme()
    
    # Check OAuth authentication
    if st.session_state.get('authenticated') and st.session_state.get('user_info'):
        user_info = st.session_state.user_info
        st.session_state.logged_in = True
        st.session_state.email = user_info.get('email')
        st.session_state.name = user_info.get('name', '')
        st.session_state.profile_picture = user_info.get('picture')
        st.session_state.page = "chat"
        load_user_data()
        st.rerun()
    
    # Handle OAuth callback
    if google_auth:
        oauth_result = handle_oauth_callback(google_auth)
        if oauth_result is True:
            return

    # Hero section
    st.markdown("""
    <div class="hero-section">
        <h1>🌸 Welcome to Asha AI 🌸</h1>
        <h2>Empowering Women to Shape Their Future</h2>
        <p style="font-size: 18px;">Break barriers, build careers, and become the leader you're meant to be</p>
    </div>
    """, unsafe_allow_html=True)

    # Login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🚀 Join the Movement")
        
        # Google OAuth Login
        if google_auth and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
            if st.button("🔵 Continue with Google", key="google_login", use_container_width=True):
                try:
                    auth_url = google_auth.get_authorization_url()
                    if auth_url:
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                        st.info("Redirecting to Google authentication...")
                except Exception as e:
                    st.error(f"Google OAuth setup error: {str(e)}")
            st.markdown("**OR**")
        
        # Email login form
        with st.form("login_form"):
            email = st.text_input("📧 Enter your Email:", placeholder="yourname@example.com")
            name = st.text_input("👤 Enter your Name:", placeholder="Your full name")
            career_stage = st.selectbox(
                "🎯 Career Stage:",
                ["", "Student/Recent Graduate", "Career Changer", "Mid-level Professional", 
                 "Senior Professional", "Entrepreneur/Freelancer"]
            )
            interests = st.multiselect(
                "💼 Areas of Interest:",
                ["Technology", "Data Science", "Marketing", "Finance", "Healthcare", 
                 "Education", "Creative Arts", "Consulting", "Entrepreneurship", "Non-Profit"]
            )
            
            submitted = st.form_submit_button("✨ Start Your Journey", use_container_width=True)
            
            if submitted:
                if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                    st.session_state.logged_in = True
                    st.session_state.email = email
                    st.session_state.name = name
                    st.session_state.career_stage = career_stage
                    st.session_state.interests = interests
                    st.session_state.page = "chat"
                    load_user_data()
                    save_user_data()
                    st.rerun()
                else:
                    st.error("Please enter a valid email address.")

# --- Chat Page ---
def chat_page():
    apply_theme()
    
    # Load user data
    if not st.session_state.chat_history and st.session_state.email:
        load_user_data()
    
    # Sidebar
    with st.sidebar:
        # Profile section
        st.markdown("### 👩‍💼 Your Profile")
        
        if st.session_state.profile_picture:
            st.image(st.session_state.profile_picture, width=80)
        
        st.markdown(f"""
        <div class="profile-section">
            <h4>{st.session_state.name or 'Career Explorer'}</h4>
            <p>📧 {st.session_state.email}</p>
            <p>🎯 {st.session_state.career_stage}</p>
        </div>
        """, unsafe_allow_html=True)

        # Chat management
        st.markdown("### 💬 Chat Sessions")
        
        if st.button("➕ New Chat", use_container_width=True):
            create_new_chat()
            st.rerun()
        
        # Previous chats
        if st.session_state.all_chats:
            for chat_id, chat_data in reversed(list(st.session_state.all_chats.items())):
                chat_title = chat_data.get("title", "Untitled Chat")
                is_active = chat_id == st.session_state.current_chat_id
                
                if st.button(f"{'🟢' if is_active else '💬'} {chat_title}", 
                           key=f"chat_{chat_id}", use_container_width=True):
                    if not is_active:
                        load_chat(chat_id)
                        st.rerun()

        # Quick actions
        st.markdown("### 🚀 Quick Actions")
        quick_actions = [
            ("💼 Find Jobs", "Show me women-friendly job opportunities"),
            ("📄 Resume Help", "Help me build a professional resume"),
            ("🎓 Scholarships", "Tell me about scholarships for women"),
            ("💪 Salary Tips", "Help me with salary negotiation"),
        ]
        
        for button_text, prompt in quick_actions:
            # Use unique keys to prevent conflicts
            if st.button(button_text, key=f"quick_{hash(prompt)}", use_container_width=True):
                if not st.session_state.processing:
                    process_user_input(prompt)

        st.markdown("---")
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.chat_history.clear()
            save_user_data()
            st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            save_user_data()
            # Clear auth session state
            for key in ['page', 'logged_in', 'email', 'authenticated', 'user_info']:
                st.session_state.pop(key, None)
            st.session_state.page = "login"
            st.rerun()

    # Main chat interface
    st.title("💜 Asha AI - Your Career Companion")
    
    # Welcome message for new users
    if not st.session_state.chat_history:
        st.markdown(f"""
        <div class="hero-section">
            <h3>👋 Hello {st.session_state.name or 'Beautiful'}!</h3>
            <p>I'm Asha, your AI career companion. I'm here to help you navigate your professional journey with confidence!</p>
        </div>
        """, unsafe_allow_html=True)

    # Display chat history
    for role, message in st.session_state.chat_history:
        if role == "user":
            st.markdown(f"""
            <div class="chat-bubble user-bubble">
                <strong>You:</strong> {message}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-bubble bot-bubble">
                <strong>🌸 Asha:</strong> {message}
            </div>
            """, unsafe_allow_html=True)

    # Chat input - Using form to prevent multiple submissions
    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "💬 Ask me anything:",
            placeholder="Ask about career advice, job opportunities, resume tips...",
            height=100
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            submitted = st.form_submit_button("💜 Send Message", use_container_width=True)
        with col2:
            if st.form_submit_button("🧹 Clear", use_container_width=True):
                pass  # Form already clears on submit
        
        if submitted and user_input.strip() and not st.session_state.processing:
            process_user_input(user_input.strip())

def process_user_input(user_message):
    """Process user input - FIXED to prevent multiple responses"""
    if st.session_state.processing:
        return
    
    st.session_state.processing = True
    
    try:
        # Ensure chat session exists
        if not st.session_state.get("current_chat_id"):
            st.session_state.current_chat_id = str(uuid.uuid4())

        # Add user message
        st.session_state.chat_history.append(("user", user_message))

        # Get AI response
        with st.spinner("🌸 Asha is thinking..."):
            response = ask_gemini(user_message)

        if response:
            # Add AI response
            st.session_state.chat_history.append(("assistant", response))
            save_user_data()
        else:
            st.error("Sorry, I couldn't generate a response. Please try again.")
            # Remove the user message if no response
            st.session_state.chat_history.pop()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        # Remove the user message if error occurred
        if st.session_state.chat_history and st.session_state.chat_history[-1][0] == "user":
            st.session_state.chat_history.pop()
    
    finally:
        st.session_state.processing = False
        st.rerun()

# --- Main App ---
def main():
    try:
        if st.session_state.page == "login" and not st.session_state.logged_in:
            login_page()
        elif st.session_state.logged_in:
            chat_page()
        else:
            st.session_state.page = "login"
            login_page()
    except Exception as e:
        st.error("An unexpected error occurred. Please refresh the page.")
        st.session_state.page = "login"
        if st.button("🔄 Refresh"):
            st.rerun()

if __name__ == "__main__":
    main()

# Enhanced auth.py with popup OAuth support - Fixed for Streamlit Cloud

import streamlit as st
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import re
import secrets
import os
import time
import base64
import json
from urllib.parse import urlencode, parse_qs

# Load environment variables (only for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available in Streamlit Cloud

# OAuth Configuration - Use Streamlit secrets for production
GOOGLE_CLIENT_ID = st.secrets.get("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = st.secrets.get("GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_CLIENT_SECRET")

def get_query_params():
    """Safely get query parameters from URL"""
    try:
        # For Streamlit >= 1.30
        return dict(st.query_params)
    except AttributeError:
        try:
            # Fallback for older versions
            return st.experimental_get_query_params()
        except:
            return {}

def get_streamlit_url():
    """Get the correct Streamlit app URL"""
    # For your specific app
    if "streamlit.app" in str(st.get_option("browser.serverAddress") or ""):
        return "https://nby3lhwfkpzxcdkiixxjfq.streamlit.app"
    
    # Check environment variables
    if os.getenv("STREAMLIT_URL"):
        return os.getenv("STREAMLIT_URL")
    
    # Try to detect Streamlit Cloud
    if any(key.startswith("STREAMLIT") for key in os.environ.keys()):
        return "https://nby3lhwfkpzxcdkiixxjfq.streamlit.app"
    
    # Local development
    return "http://localhost:8501"

class GoogleAuthenticator:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = get_streamlit_url()
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self, state=None):
        """Generate OAuth URL with improved error handling"""
        if not self.client_id or not self.client_secret:
            st.error("❌ OAuth credentials not configured. Please check your secrets.")
            return None
            
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            if not state:
                state = secrets.token_urlsafe(32)
            
            # Store state with timestamp
            st.session_state.oauth_state = state
            st.session_state.oauth_state_timestamp = time.time()
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='select_account'
            )
            
            return auth_url
            
        except Exception as e:
            st.error(f"❌ OAuth configuration error: {str(e)}")
            st.error("Please check your Google OAuth credentials in Streamlit secrets.")
            return None
    
    def handle_callback(self, authorization_code, state=None):
        """Enhanced callback handling with better validation"""
        # Validate state
        stored_state = st.session_state.get('oauth_state')
        stored_timestamp = st.session_state.get('oauth_state_timestamp', 0)
        current_time = time.time()
        
        # Check if state is expired (10 minutes)
        if current_time - stored_timestamp > 600:
            st.error("❌ OAuth session expired. Please try logging in again.")
            self._clear_oauth_state()
            return None, None
        
        # Validate state parameter
        if state and state != stored_state:
            st.error("❌ OAuth state validation failed. Please try again.")
            self._clear_oauth_state()
            return None, None
        
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for token
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Get user info
            user_info = self._get_user_info(credentials.token)
            
            # Clear OAuth state after successful authentication
            self._clear_oauth_state()
            
            return user_info, credentials
            
        except Exception as e:
            st.error(f"❌ Authentication failed: {str(e)}")
            self._clear_oauth_state()
            return None, None
    
    def _clear_oauth_state(self):
        """Clear all OAuth state data"""
        keys_to_clear = ['oauth_state', 'oauth_state_timestamp']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def _get_user_info(self, access_token):
        """Get user information from Google API"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo', 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.status_code}")

def enhanced_oauth_login():
    """Enhanced OAuth login with better error handling"""
    
    # Check if credentials are configured
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        st.error("❌ Google OAuth not configured!")
        st.info("""
        **To fix this:**
        1. Go to your Streamlit app settings
        2. Add these secrets:
           - `GOOGLE_CLIENT_ID` = your Google OAuth client ID
           - `GOOGLE_CLIENT_SECRET` = your Google OAuth client secret
        3. Make sure your OAuth redirect URI includes: `https://nby3lhwfkpzxcdkiixxjfq.streamlit.app`
        """)
        return False
    
    authenticator = GoogleAuthenticator(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
    
    # Handle OAuth callback first
    callback_result = handle_oauth_callback(authenticator)
    if callback_result is True:
        return True
    elif callback_result is False:
        return False
    
    # Show login UI
    st.markdown("### 🔐 Authentication Required")
    st.markdown("Please sign in with your Google account to continue.")
    
    if st.button("🔵 Sign in with Google", type="primary", use_container_width=True):
        auth_url = authenticator.get_authorization_url()
        if auth_url:
            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
            st.info("🔄 Redirecting to Google for authentication...")
            st.markdown(f"**[Click here if not redirected automatically]({auth_url})**")
    
    return False

def handle_oauth_callback(authenticator):
    """Handle OAuth callback with better error handling"""
    try:
        query_params = get_query_params()
    except Exception as e:
        st.error(f"Error reading URL parameters: {str(e)}")
        return None

    # Handle successful OAuth callback
    if 'code' in query_params:
        auth_code = query_params['code']
        if isinstance(auth_code, list):
            auth_code = auth_code[0]
            
        state = query_params.get('state')
        if isinstance(state, list):
            state = state[0]

        with st.spinner("🔐 Completing authentication..."):
            try:
                user_info, credentials = authenticator.handle_callback(auth_code, state)
                
                if user_info and credentials:
                    # Store authentication data
                    st.session_state.user_info = user_info
                    st.session_state.authenticated = True
                    st.session_state.credentials = credentials
                    st.session_state.email = user_info.get('email')
                    st.session_state.name = user_info.get('name')
                    
                    # Clear URL parameters
                    clear_url_params()
                    
                    st.success(f"🎉 Welcome {user_info.get('name', 'User')}!")
                    time.sleep(1)
                    st.rerun()
                    return True
                else:
                    st.error("❌ Authentication failed. Please try again.")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Authentication error: {str(e)}")
                return False
    
    # Handle OAuth errors
    elif 'error' in query_params:
        error = query_params['error']
        if isinstance(error, list):
            error = error[0]
            
        error_description = query_params.get('error_description', ['Access denied'])
        if isinstance(error_description, list):
            error_description = error_description[0]
        
        st.error(f"❌ Google OAuth Error: {error}")
        if error_description:
            st.error(f"Details: {error_description}")
        
        clear_url_params()
        return False
    
    return None

def clear_url_params():
    """Clear URL parameters"""
    try:
        st.query_params.clear()
    except:
        pass

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False) and st.session_state.get('user_info') is not None

def get_user_info():
    """Get current user information"""
    return st.session_state.get('user_info', {})

def logout():
    """Logout user and clear session"""
    # Clear authentication data
    auth_keys = [
        'oauth_state', 'oauth_state_timestamp', 'user_info', 
        'authenticated', 'credentials', 'email', 'name'
    ]
    
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    clear_url_params()
    st.success("👋 Logged out successfully!")
    st.rerun()

def validate_google_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def debug_oauth_setup():
    """Debug OAuth configuration"""
    st.markdown("### 🔧 OAuth Debug Information")
    
    client_id_set = bool(GOOGLE_CLIENT_ID)
    client_secret_set = bool(GOOGLE_CLIENT_SECRET)
    
    st.write(f"**Google Client ID Set:** {'✅ Yes' if client_id_set else '❌ No'}")
    st.write(f"**Google Client Secret Set:** {'✅ Yes' if client_secret_set else '❌ No'}")
    st.write(f"**Redirect URL:** {get_streamlit_url()}")
    
    if client_id_set and len(GOOGLE_CLIENT_ID) > 20:
        st.write(f"**Client ID Preview:** {GOOGLE_CLIENT_ID[:20]}...")
    
    # Session state info
    st.write("**Current Session:**")
    st.write(f"- Authenticated: {st.session_state.get('authenticated', False)}")
    st.write(f"- User Info: {'✅ Present' if st.session_state.get('user_info') else '❌ None'}")
    
    if st.button("🔄 Reset Authentication"):
        logout()

# Main authentication function to use in your app
def require_auth():
    """Main function to handle authentication - use this in your main app"""
    if not is_authenticated():
        return enhanced_oauth_login()
    return True

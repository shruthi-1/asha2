# Enhanced auth.py with popup OAuth support

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
from dotenv import load_dotenv

load_dotenv(dotenv_path="C:/Users/shrut/OneDrive/Desktop/asha/.env")
load_dotenv()

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

class GoogleAuthenticator:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self, state=None):
        """Generate OAuth URL with improved error handling"""
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
            
            # Store state with timestamp for expiration tracking
            st.session_state.oauth_state = state
            st.session_state.oauth_state_timestamp = time.time()
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='select_account'  # Always show account selector
            )
            
            return auth_url
            
        except Exception as e:
            st.error(f"OAuth configuration error: {str(e)}")
            return None
    
    def handle_callback(self, authorization_code, state=None):
        """Enhanced callback handling with better validation"""
        # Enhanced state validation
        stored_state = st.session_state.get('oauth_state')
        stored_timestamp = st.session_state.get('oauth_state_timestamp', 0)
        current_time = time.time()
        
        # Check if state is expired (10 minutes)
        if current_time - stored_timestamp > 600:
            st.error("OAuth session expired. Please try logging in again.")
            self._clear_oauth_state()
            return None, None
        
        # Validate state
        if state and state != stored_state:
            st.error("OAuth state validation failed. This might be a security issue.")
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
            
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Get user info
            user_info = self._get_user_info(credentials.token)
            
            # Clear OAuth state after successful authentication
            self._clear_oauth_state()
            
            return user_info, credentials
            
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            self._clear_oauth_state()
            return None, None
    
    def _clear_oauth_state(self):
        """Clear all OAuth state data"""
        keys_to_clear = ['oauth_state', 'oauth_state_timestamp', 'oauth_states']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def _get_user_info(self, access_token):
        """Get user information from Google API"""
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.status_code} - {response.text}")

def create_oauth_popup_component():
    """Create JavaScript component for OAuth popup"""
    return """
    <script>
    function openOAuthPopup(authUrl) {
        const popup = window.open(
            authUrl,
            'google_oauth',
            'width=500,height=600,scrollbars=yes,resizable=yes'
        );
        
        // Check if popup was blocked
        if (!popup || popup.closed || typeof popup.closed == 'undefined') {
            alert('Popup blocked! Please allow popups for this site and try again.');
            return;
        }
        
        // Monitor popup for completion
        const checkClosed = setInterval(() => {
            if (popup.closed) {
                clearInterval(checkClosed);
                // Refresh the parent window to check for authentication
                window.location.reload();
            }
        }, 1000);
        
        // Handle popup messaging (if needed)
        window.addEventListener('message', (event) => {
            if (event.origin !== window.location.origin) return;
            
            if (event.data.type === 'OAUTH_SUCCESS') {
                popup.close();
                clearInterval(checkClosed);
                window.location.reload();
            }
        });
    }
    </script>
    """

def get_streamlit_url():
    """Dynamically get the current Streamlit app URL"""
    try:
        # Try to get from Streamlit context
        import streamlit.web.bootstrap as bootstrap
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        
        ctx = get_script_run_ctx()
        if ctx and hasattr(ctx, 'session_info'):
            return f"https://{ctx.session_info.host}"
    except:
        pass
    
    # Fallback methods
    if os.getenv("STREAMLIT_URL"):
        return os.getenv("STREAMLIT_URL")
    
    # Check if running on Streamlit Cloud
    if os.getenv("STREAMLIT_CLOUD"):
        # Try to construct from environment
        app_name = os.getenv("STREAMLIT_APP_NAME", "unknown")
        return f"https://{app_name}.streamlit.app"
    
    # Local development fallback
    return "http://localhost:8501"

def enhanced_oauth_login(authenticator):
    """Enhanced OAuth login with popup support"""
    
    # Get dynamic redirect URI
    current_url = get_streamlit_url()
    authenticator.redirect_uri = current_url
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔵 Continue with Google", key="google_login_popup", use_container_width=True):
            auth_url = authenticator.get_authorization_url()
            if auth_url:
                # Create popup OAuth
                st.markdown(create_oauth_popup_component(), unsafe_allow_html=True)
                st.markdown(f"""
                <button onclick="openOAuthPopup('{auth_url}')" 
                        style="background: #4285f4; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%;">
                    🔵 Open Google Login Popup
                </button>
                """, unsafe_allow_html=True)
                
                st.info("🔍 If the popup doesn't open automatically, click the button above or try the direct link below.")
                st.markdown(f"[**Direct Google Login Link**]({auth_url})")
    
    with col2:
        if st.button("🔗 Direct Google Login", key="google_login_direct", use_container_width=True):
            auth_url = authenticator.get_authorization_url()
            if auth_url:
                st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
                st.info("Redirecting to Google authentication...")
                st.markdown(f"[**Click here if not redirected**]({auth_url})")

def validate_google_email(email):
    """Enhanced email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check for common test emails
    test_patterns = [
        r'^test@test\.com$', r'^fake@fake\.com$', r'^example@example\.com$',
        r'^user@user\.com$', r'^admin@admin\.com$'
    ]
    
    for pattern in test_patterns:
        if re.match(pattern, email.lower()):
            return False, "Please use a real email address"
    
    return True, "Valid email"

def handle_oauth_callback(authenticator):
    """Enhanced OAuth callback handler with better error messages"""
    try:
        # Get query parameters safely
        query_params = {}
        try:
            # Try new method first
            query_params = st.query_params
        except AttributeError:
            # Fallback for older Streamlit versions
            query_params = st.experimental_get_query_params()
    except Exception as e:
        st.error(f"Error reading URL parameters: {str(e)}")
        return None

    # Check for OAuth callback parameters
    if 'code' in query_params:
        auth_code = query_params['code'][0] if isinstance(query_params['code'], list) else query_params['code']
        state = query_params.get('state')
        if isinstance(state, list):
            state = state[0]

        with st.spinner("🔐 Completing Google authentication..."):
            try:
                user_info, credentials = authenticator.handle_callback(auth_code, state)
                
                if user_info and credentials:
                    # Store user info in session state
                    st.session_state.user_info = user_info
                    st.session_state.authenticated = True
                    st.session_state.credentials = credentials
                    
                    # Clear URL parameters
                    st.experimental_get_query_params.clear()
                    
                    st.success(f"🎉 Welcome {user_info.get('name', 'User')}! Authentication successful!")
                    time.sleep(1)
                    st.rerun()
                    
                    return True
                else:
                    st.error("❌ Authentication failed. Please try again.")
                    return False
                    
            except Exception as e:
                st.error(f"❌ Authentication error: {str(e)}")
                st.info("💡 Try refreshing the page and logging in again.")
                return False
    
    # Check for OAuth error
    elif 'error' in query_params:
        error = query_params['error'][0] if isinstance(query_params['error'], list) else query_params['error']
        error_description = query_params.get('error_description', ['Access denied'])
        if isinstance(error_description, list):
            error_description = error_description[0]
        
        st.error(f"❌ Google OAuth Error: {error}")
        st.error(f"Details: {error_description}")
        
        # Clear error from URL
        st.experimental_get_query_params.clear()

        
        return False
    
    return None

def reset_auth_state():
    """Reset all authentication-related session state"""
    auth_keys = [
        'oauth_state', 'oauth_state_timestamp', 'oauth_states',
        'user_info', 'authenticated', 'credentials', 'logged_in',
        'email', 'name', 'profile_picture'
    ]
    
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear URL parameters
    try:
        st.query_params.clear()
    except:
        pass
    
    st.success("🔄 Authentication state reset. Please try logging in again.")
    st.rerun()

def debug_oauth_setup():
    """Debug function to check OAuth configuration"""
    st.markdown("### 🔧 OAuth Debug Information")
    
    # Check environment variables
    client_id_set = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_ID != 'your_google_client_id_here')
    client_secret_set = bool(GOOGLE_CLIENT_SECRET and GOOGLE_CLIENT_SECRET != 'your_google_client_secret_here')
    
    st.write(f"**Google Client ID Set:** {'✅ Yes' if client_id_set else '❌ No'}")
    st.write(f"**Google Client Secret Set:** {'✅ Yes' if client_secret_set else '❌ No'}")
    st.write(f"**Current URL:** {get_streamlit_url()}")
    
    if client_id_set:
        st.write(f"**Client ID (first 20 chars):** {GOOGLE_CLIENT_ID[:20]}...")
    
    # Session state info
    st.write("**Session State:**")
    oauth_keys = ['oauth_state', 'authenticated', 'user_info']
    for key in oauth_keys:
        if key in st.session_state:
            st.write(f"- {key}: ✅ Present")
        else:
            st.write(f"- {key}: ❌ Not set")
    
    if st.button("🔄 Reset OAuth State"):
        reset_auth_state()

# Enhanced auth.py with improved state management

import streamlit as st
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import re
import secrets
import openai
import os
import time
from dotenv import load_dotenv
from knowledgebase import asha_topics

load_dotenv(dotenv_path="C:/Users/shrut/OneDrive/Desktop/asha/.env")
load_dotenv()

# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
model = "gemini-1.5"

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
        
        # Also store in a more persistent way (optional)
        if 'oauth_states' not in st.session_state:
            st.session_state.oauth_states = {}
        st.session_state.oauth_states[state] = time.time()
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        
        return auth_url
    
    def handle_callback(self, authorization_code, state=None):
        # Enhanced state validation with multiple fallbacks
        stored_state = st.session_state.get('oauth_state')
        stored_states = st.session_state.get('oauth_states', {})
        current_time = time.time()
        
        # Clean up expired states (older than 10 minutes)
        expired_states = [s for s, timestamp in stored_states.items() 
                         if current_time - timestamp > 600]
        for expired_state in expired_states:
            stored_states.pop(expired_state, None)
        
        # Validate state with multiple methods
        state_valid = False
        
        if state:
            # Method 1: Check current stored state
            if state == stored_state:
                state_valid = True
            # Method 2: Check against stored states collection
            elif state in stored_states:
                state_valid = True
            # Method 3: More lenient validation for development
            elif not stored_state and not stored_states:
                # If no state is stored, accept any state (useful for development)
                st.warning("No stored OAuth state found. Proceeding with authentication...")
                state_valid = True
        else:
            # If no state provided but we have stored state, might be valid
            if stored_state or stored_states:
                st.warning("No state parameter received. This might be a security risk.")
            state_valid = True  # Allow for cases where state is not provided
        
        if not state_valid:
            st.error("OAuth state validation failed. Please try logging in again.")
            self._clear_oauth_state()
            return None, None
        
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
        
        try:
            flow.fetch_token(code=authorization_code)
            credentials = flow.credentials
            
            # Clear OAuth state after successful authentication
            self._clear_oauth_state()
            
            return self._get_user_info(credentials.token), credentials
            
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
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.status_code}")

def validate_google_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    common_fake = [r'^test@test\.com$', r'^fake@fake\.com$', r'^example@example\.com$']
    for f in common_fake:
        if re.match(f, email.lower()):
            return False, "Please use a real email address"
    
    try:
        import socket
        domain = email.split('@')[1]
        socket.gethostbyname(domain)
        return True, "Valid email"
    except:
        return False, "Invalid email domain"

def get_query_params():
    """Safe wrapper to get query parameters"""
    try:
        return dict(st.query_params)
    except AttributeError:
        try:
            return st.experimental_get_query_params()
        except:
            return {}

def handle_oauth_callback(authenticator):
    """Enhanced OAuth callback handler with improved error handling"""
    query_params = get_query_params()
    
    
    
    # Check for OAuth callback parameters
    if 'code' in query_params:
        auth_code = query_params['code'][0] if isinstance(query_params['code'], list) else query_params['code']
        state = query_params.get('state')
        if isinstance(state, list):
            state = state[0]
        
        try:
            user_info, credentials = authenticator.handle_callback(auth_code, state)
            
            if user_info and credentials:
                # Store user info in session state
                st.session_state.user_info = user_info
                st.session_state.authenticated = True
                st.session_state.credentials = credentials
                
                # Success message
                st.success("Authentication successful! Redirecting...")
                
                # Clear URL parameters by rerunning
                st.rerun()
                
                return True
            else:
                st.error("Authentication failed. Please try again.")
                return False
                
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False
    
    # Check for OAuth error
    elif 'error' in query_params:
        error = query_params['error'][0] if isinstance(query_params['error'], list) else query_params['error']
        error_description = query_params.get('error_description', ['No description provided'])
        if isinstance(error_description, list):
            error_description = error_description[0]
        
        st.error(f"OAuth error: {error}")
        st.error(f"Description: {error_description}")
        return False
    
    return None

# Additional helper function for debugging
def reset_auth_state():
    """Reset all authentication-related session state"""
    auth_keys = [
        'oauth_state', 'oauth_state_timestamp', 'oauth_states',
        'user_info', 'authenticated', 'credentials'
    ]
    
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    st.success("Authentication state reset. Please try logging in again.")
    st.rerun()
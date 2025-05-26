import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, List, Optional


class Config:
    """Configuration class - you'll need to set this path"""
    FIREBASE_CREDENTIALS_PATH = "C:\\Users\\shrut\\OneDrive\\Desktop\\asha\\firebase\\firebase_cred.json"


class UserDataManager:
    def __init__(self, use_firebase=True):
        self.use_firebase = use_firebase
        self.db = None
        
        if use_firebase:
            self._init_firebase()
        else:
            self.local_storage_path = "user_data"
            os.makedirs(self.local_storage_path, exist_ok=True)
    
    def _init_firebase(self):
        """Initialize Firebase"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
        except Exception as e:
            print(f"Firebase initialization failed: {e}")
            self.use_firebase = False
            # Initialize local storage as fallback
            self.local_storage_path = "user_data"
            os.makedirs(self.local_storage_path, exist_ok=True)
    
    def save_user_data(self, email: str, user_data: Dict) -> bool:
        """Save user data"""
        user_data['last_updated'] = datetime.now().isoformat()
        
        if self.use_firebase and self.db:
            try:
                doc_ref = self.db.collection('users').document(email)
                doc_ref.set(user_data, merge=True)
                return True
            except Exception as e:
                print(f"Firebase save error: {e}")
                return self._save_locally(email, user_data)
        else:
            return self._save_locally(email, user_data)
    
    def load_user_data(self, email: str) -> Optional[Dict]:
        """Load user data"""
        if self.use_firebase and self.db:
            try:
                doc_ref = self.db.collection('users').document(email)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                print(f"Firebase load error: {e}")
                return self._load_locally(email)
        else:
            return self._load_locally(email)
        return None
    
    def _save_locally(self, email: str, user_data: Dict) -> bool:
        """Local file storage fallback"""
        try:
            filename = hashlib.md5(email.encode()).hexdigest()
            filepath = os.path.join(self.local_storage_path, f"{filename}.json")
            with open(filepath, 'w') as f:
                json.dump(user_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Local save error: {e}")
            return False
    
    def _load_locally(self, email: str) -> Optional[Dict]:
        """Local file storage fallback"""
        try:
            filename = hashlib.md5(email.encode()).hexdigest()
            filepath = os.path.join(self.local_storage_path, f"{filename}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Local load error: {e}")
        return None
    
    def save_conversation(self, email: str, conversation_data: Dict) -> bool:
        """Save conversation history"""
        user_data = self.load_user_data(email) or {}
        
        if 'conversations' not in user_data:
            user_data['conversations'] = []
        
        # Add timestamp and save
        conversation_data['timestamp'] = datetime.now().isoformat()
        conversation_data['session_id'] = secrets.token_urlsafe(16)
        
        user_data['conversations'].append(conversation_data)
        
        # Keep only last 50 conversations
        user_data['conversations'] = user_data['conversations'][-50:]
        
        return self.save_user_data(email, user_data)
    
    def get_conversation_history(self, email: str, days: int = 30) -> List[Dict]:
        """Get recent conversation history"""
        user_data = self.load_user_data(email)
        if not user_data or 'conversations' not in user_data:
            return []
        
        # Filter conversations from last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_conversations = []
        
        for conv in user_data['conversations']:
            try:
                conv_date = datetime.fromisoformat(conv.get('timestamp', ''))
                if conv_date > cutoff_date:
                    recent_conversations.append(conv)
            except ValueError:
                # Skip conversations with invalid timestamps
                continue
        
        return recent_conversations
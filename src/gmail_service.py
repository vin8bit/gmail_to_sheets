import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GmailService:
    def __init__(self, token_file='token.pickle', credentials_file='credentials.json'):
        self.service = None
        self.creds = None
        self.token_file = token_file
        self.credentials_file = credentials_file
        
    def authenticate(self, scopes):
        """Authenticate and create Gmail service instance."""
        print(f"Looking for token at: {self.token_file}")
        print(f"Looking for credentials at: {self.credentials_file}")
        
        self.creds = None
        
        # Check for existing token
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                print(f"✓ Loaded existing token from {self.token_file}")
            except Exception as e:
                print(f"Error loading token: {e}")
                os.remove(self.token_file)
                
        # If no valid credentials, let user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing expired token...")
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    self.creds = None
            
            if not self.creds:
                print("No valid credentials found. Starting OAuth flow...")
                
                # Check if credentials file exists
                if not os.path.exists(self.credentials_file):
                    print(f"✗ ERROR: Credentials file not found at {self.credentials_file}")
                    return False
                    
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, scopes)
                    self.creds = flow.run_local_server(port=0)
                    
                    # Save credentials
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(self.creds, token)
                    print(f"✓ Authentication successful! Token saved to {self.token_file}")
                    
                except Exception as e:
                    print(f"✗ Authentication failed: {e}")
                    return False
        
        # Build service
        try:
            self.service = build('gmail', 'v1', credentials=self.creds)
            return True
        except Exception as e:
            print(f"✗ Error building Gmail service: {e}")
            return False
    
    def get_unread_emails(self):
        """Fetch unread emails from inbox."""
        try:
            # Search for unread emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread in:inbox'
            ).execute()
            
            messages = results.get('messages', [])
            print(f"Found {len(messages)} unread emails")
            return messages
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_email_details(self, msg_id):
        """Get full email details by ID."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()
            return message
        except Exception as e:
            print(f"Error getting email {msg_id}: {e}")
            return None
    
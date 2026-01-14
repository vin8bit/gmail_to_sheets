import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class SheetsService:
    def __init__(self, token_file='token.pickle', credentials_file='credentials.json'):
        self.service = None
        self.creds = None
        self.token_file = token_file
        self.credentials_file = credentials_file
        
    def authenticate(self, scopes):
        """Authenticate and create Sheets service instance."""
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
            self.service = build('sheets', 'v4', credentials=self.creds)
            return True
        except Exception as e:
            print(f"✗ Error building Sheets service: {e}")
            return False

    
    def create_spreadsheet(self, title):
        """Create a new spreadsheet."""
        try:
            spreadsheet_body = {
                'properties': {
                    'title': title
                },
                'sheets': [{
                    'properties': {
                        'title': 'Email Logs'
                    }
                }]
            }
            
            spreadsheet = self.service.spreadsheets().create(
                body=spreadsheet_body,
                fields='spreadsheetId'
            ).execute()
            
            spreadsheet_id = spreadsheet.get('spreadsheetId')
            print(f"✓ Created new spreadsheet!")
            print(f"   URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
            
            # Add headers immediately
            self.add_headers(spreadsheet_id, 'Email Logs', ['Date & Time', 'From', 'Subject', 'Content'])
            
            return spreadsheet_id
            
        except Exception as e:
            print(f"Error creating spreadsheet: {e}")
            return None
    
    def create_sheet(self, spreadsheet_id, sheet_name):
        """Create a new sheet in existing spreadsheet."""
        try:
            batch_update_request = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }
            
            response = self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_update_request
            ).execute()
            
            print(f"✓ Created new sheet: '{sheet_name}'")
            return True
            
        except Exception as e:
            print(f"Error creating sheet: {e}")
            return False
    
    def add_headers(self, spreadsheet_id, sheet_name, headers):
        """Add headers to a sheet."""
        try:
            # Properly format range for sheet names with spaces
            if ' ' in sheet_name or "'" in sheet_name or '!' in sheet_name:
                range_name = f"'{sheet_name}'!A1:D1"
            else:
                range_name = f"{sheet_name}!A1:D1"
                
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            print(f"✓ Added headers to '{sheet_name}'")
            return True
        except Exception as e:
            print(f"Error adding headers to '{sheet_name}': {e}")
            return False
    
    def append_data(self, spreadsheet_id, sheet_name, data):
        """Append data to a sheet."""
        try:
            # Properly format range for sheet names with spaces
            if ' ' in sheet_name or "'" in sheet_name or '!' in sheet_name:
                range_name = f"'{sheet_name}'!A:D"
            else:
                range_name = f"{sheet_name}!A:D"
                
            body = {
                'values': [data]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Changed to USER_ENTERED for better formatting
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            # Debug: Print what was appended
            updates = result.get('updates', {})
            print(f"  ↳ Appended to row {updates.get('updatedRange', 'unknown')}")
            
            return True
            
        except HttpError as error:
            print(f'✗ Sheets API error: {error}')
            return False
        except Exception as e:
            print(f'✗ Error appending data: {e}')
            return False
    
    def sheet_exists(self, spreadsheet_id, sheet_name):
        """Check if a sheet exists in the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    return True
            return False
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"✗ Spreadsheet not found: {spreadsheet_id}")
            else:
                print(f"✗ Error checking sheet existence: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    def get_sheets(self, spreadsheet_id):
        """Get all sheets in the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheets = spreadsheet.get('sheets', [])
            sheet_names = []
            for sheet in sheets:
                title = sheet['properties']['title']
                sheet_names.append(title)
                print(f"  - '{title}' (ID: {sheet['properties']['sheetId']})")
            
            return sheet_names
        except HttpError as e:
            print(f"✗ Error getting sheets: {e}")
            return []
    
    def test_append(self, spreadsheet_id, sheet_name):
        """Test append functionality with simple data."""
        try:
            test_data = ['Test Date', 'test@example.com', 'Test Subject', 'Test Content']
            success = self.append_data(spreadsheet_id, sheet_name, test_data)
            if success:
                print(f"✓ Test append successful to '{sheet_name}'")
            else:
                print(f"✗ Test append failed to '{sheet_name}'")
            return success
        except Exception as e:
            print(f"✗ Test append error: {e}")
            return False
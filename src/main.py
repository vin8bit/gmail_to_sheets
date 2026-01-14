import os
import json
import re
from gmail_service import GmailService
from sheets_service import SheetsService
from email_parser import EmailParser

# If modifying these scopes, delete the token.json file.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Configuration - USE ABSOLUTE PATHS
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, 'credentials', 'credentials.json')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')
STATE_FILE = os.path.join(PROJECT_ROOT, 'state.json')
TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.pickle')
SHEET_NAME = 'Gmail Email Logs'

# Filter configuration
class FilterConfig:
    def __init__(self):
        self.enable_filtering = False
        self.subject_keywords = []
        self.sender_domains = []
        self.min_date = None
        self.max_date = None
        
    def load_from_config(self, config_data):
        """Load filter settings from config."""
        filter_settings = config_data.get('filters', {})
        
        self.enable_filtering = filter_settings.get('enabled', False)
        self.subject_keywords = filter_settings.get('subject_keywords', [])
        self.sender_domains = filter_settings.get('sender_domains', [])
        self.min_date = filter_settings.get('min_date')
        self.max_date = filter_settings.get('max_date')
        
        return self
    
    def should_process_email(self, email_data):
        """Check if email should be processed based on filters."""
        if not self.enable_filtering:
            return True
            
        # Subject filtering
        if self.subject_keywords:
            subject_lower = email_data['subject'].lower()
            if not any(keyword.lower() in subject_lower for keyword in self.subject_keywords):
                return False
        
        # Sender domain filtering
        if self.sender_domains:
            from_email = email_data['from']
            domain = from_email.split('@')[-1] if '@' in from_email else ''
            if domain and domain.lower() not in [d.lower() for d in self.sender_domains]:
                return False
        
        # Date filtering
        if self.min_date or self.max_date:
            try:
                email_date = datetime.strptime(email_data['date'], '%Y-%m-%d %H:%M:%S')
                
                if self.min_date:
                    min_date = datetime.strptime(self.min_date, '%Y-%m-%d')
                    if email_date < min_date:
                        return False
                
                if self.max_date:
                    max_date = datetime.strptime(self.max_date, '%Y-%m-%d')
                    if email_date > max_date:
                        return False
            except:
                pass  # If date parsing fails, skip date filtering
        
        return True

class GmailToSheets:
    def __init__(self):
        self.gmail_service = GmailService(TOKEN_FILE, CREDENTIALS_FILE)
        self.sheets_service = SheetsService(TOKEN_FILE, CREDENTIALS_FILE)
        self.filter_config = FilterConfig()
        self.processed_ids = self.load_state()
        
    def load_state(self):
        """Load processed email IDs from state file."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_ids', []))
            except:
                print("Creating new state file...")
                return set()
        return set()
    
    def save_state(self):
        """Save processed email IDs to state file."""
        with open(STATE_FILE, 'w') as f:
            json.dump({'processed_ids': list(self.processed_ids)}, f)
    
    def load_config(self):
        """Load configuration including filters."""
        config_data = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
            except Exception as e:
                print(f"⚠️  Error reading config: {e}")
        
        # Load filter settings
        self.filter_config.load_from_config(config_data)
        
        # Return spreadsheet ID
        return config_data.get('spreadsheet_id')
    
    def save_config(self, spreadsheet_id, filters=None):
        """Save configuration including filters."""
        config_data = {'spreadsheet_id': spreadsheet_id}
        
        if filters:
            config_data['filters'] = {
                'enabled': filters.get('enabled', False),
                'subject_keywords': filters.get('subject_keywords', []),
                'sender_domains': filters.get('sender_domains', []),
                'min_date': filters.get('min_date'),
                'max_date': filters.get('max_date')
            }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def authenticate(self):
        """Authenticate both services."""
        if not self.gmail_service.authenticate(SCOPES):
            return False
        if not self.sheets_service.authenticate(SCOPES):
            return False
        return True
    
    def validate_spreadsheet(self, spreadsheet_id):
        """Validate that we can access the spreadsheet."""
        print(f"\nValidating spreadsheet access...")
        try:
            sheets = self.sheets_service.get_sheets(spreadsheet_id)
            if not sheets:
                print("✗ Spreadsheet appears to be empty or inaccessible")
                return False
            
            print(f"✓ Found {len(sheets)} sheet(s) in spreadsheet")
            
            # Check if our target sheet exists
            sheet_exists = SHEET_NAME in sheets
            if sheet_exists:
                print(f"✓ Target sheet '{SHEET_NAME}' exists")
            else:
                print(f"✗ Target sheet '{SHEET_NAME}' not found. Available sheets: {sheets}")
                # Try with any sheet name
                if sheets:
                    print(f"  Will try to use first available sheet: '{sheets[0]}'")
            
            return True
        except Exception as e:
            print(f"✗ Spreadsheet validation failed: {e}")
            return False
    
    def ensure_sheet_setup(self, spreadsheet_id, sheet_name=None):
        """Ensure sheet exists and has headers."""
        if sheet_name is None:
            sheet_name = SHEET_NAME
            
        print(f"\nSetting up sheet '{sheet_name}'...")
        
        try:
            # Check if sheet exists
            if not self.sheets_service.sheet_exists(spreadsheet_id, sheet_name):
                print(f"  Creating sheet '{sheet_name}'...")
                if not self.sheets_service.create_sheet(spreadsheet_id, sheet_name):
                    return False
            
            # Always ensure headers are present
            headers = ['Date & Time', 'From', 'Subject', 'Content', 'Filter Match']
            if not self.sheets_service.add_headers(spreadsheet_id, sheet_name, headers):
                print(f"  Warning: Could not add headers to '{sheet_name}'")
            
            # Test with a dummy row
            print(f"  Testing append functionality...")
            test_success = self.sheets_service.test_append(spreadsheet_id, sheet_name)
            if not test_success:
                print(f"  ✗ Append test failed for '{sheet_name}'")
                return False
            
            print(f"✓ Sheet '{sheet_name}' is ready")
            return True
            
        except Exception as e:
            print(f"✗ Error setting up sheet: {e}")
            return False
    
    def extract_filter_matches(self, email_data):
        """Extract which filter matched the email."""
        matches = []
        
        # Check subject keywords
        if self.filter_config.subject_keywords:
            subject_lower = email_data['subject'].lower()
            for keyword in self.filter_config.subject_keywords:
                if keyword.lower() in subject_lower:
                    matches.append(f"Subject: {keyword}")
                    break
        
        # Check sender domains
        if self.filter_config.sender_domains:
            from_email = email_data['from']
            domain = from_email.split('@')[-1] if '@' in from_email else ''
            if domain:
                for allowed_domain in self.filter_config.sender_domains:
                    if domain.lower() == allowed_domain.lower():
                        matches.append(f"Domain: {domain}")
                        break
        
        return ', '.join(matches) if matches else 'No filter match'
    
    def process_emails(self, spreadsheet_id):
        print(f"\n{'='*60}")
        print("Starting email processing...")
        print(f"Spreadsheet ID: {spreadsheet_id}")
        print(f"Target sheet: '{SHEET_NAME}'")
        
        # Display filter settings
        if self.filter_config.enable_filtering:
            print(f"\n📋 ACTIVE FILTERS:")
            if self.filter_config.subject_keywords:
                print(f"  Subject keywords: {', '.join(self.filter_config.subject_keywords)}")
            if self.filter_config.sender_domains:
                print(f"  Sender domains: {', '.join(self.filter_config.sender_domains)}")
            if self.filter_config.min_date:
                print(f"  Min date: {self.filter_config.min_date}")
            if self.filter_config.max_date:
                print(f"  Max date: {self.filter_config.max_date}")
        else:
            print(f"\n📋 FILTERS: Disabled (processing all emails)")
        
        print(f"{'='*60}")
        
        # First validate spreadsheet access
        if not self.validate_spreadsheet(spreadsheet_id):
            return
        
        # Get all available sheets
        sheets = self.sheets_service.get_sheets(spreadsheet_id)
        
        # Determine which sheet to use
        target_sheet = SHEET_NAME
        if SHEET_NAME not in sheets and sheets:
            print(f"\n⚠️  '{SHEET_NAME}' not found. Using first available sheet: '{sheets[0]}'")
            target_sheet = sheets[0]
        
        # Ensure sheet is set up
        if not self.ensure_sheet_setup(spreadsheet_id, target_sheet):
            print("✗ Failed to setup sheet. Cannot process emails.")
            return
        
        # Get unread emails
        messages = self.gmail_service.get_unread_emails()
        
        if not messages:
            print("No unread emails found")
            return
        
        print(f"\nFound {len(messages)} unread emails")
        
        # Process each email
        successful_emails = 0
        filtered_emails = 0
        for i, message in enumerate(messages, 1):
            msg_id = message['id']
            
            if msg_id in self.processed_ids:
                print(f"  [{i}/{len(messages)}] Skipped (already processed): {msg_id[:10]}...")
                continue
            
            print(f"  [{i}/{len(messages)}] Processing: {msg_id[:10]}...")
            
            # Get email details
            email_message = self.gmail_service.get_email_details(msg_id)
            
            if not email_message:
                print(f"     ✗ Failed to fetch email details")
                continue
            
            # Parse email with HTML conversion
            email_data = EmailParser.parse_email(email_message)
            
            if not email_data:
                print(f"     ✗ Failed to parse email")
                continue
            
            # Apply filters
            if not self.filter_config.should_process_email(email_data):
                print(f"     ⚡ Filtered out: {email_data['subject'][:50]}...")
                filtered_emails += 1
                
                self.processed_ids.add(msg_id)
                continue
            
            # Extract filter matches for logging
            filter_matches = self.extract_filter_matches(email_data)
            
            # Append to sheet
            values = [
                email_data['date'],
                email_data['from'],
                email_data['subject'],
                email_data['body'],
                filter_matches
            ]
            
            success = self.sheets_service.append_data(spreadsheet_id, target_sheet, values)
            
            if success:
                # Add to processed IDs
                self.processed_ids.add(msg_id)
                successful_emails += 1
                print(f"     ✓ Appended email from {email_data['from']}")
                if filter_matches != 'No filter match':
                    print(f"       Filter match: {filter_matches}")
            else:
                print(f"     ✗ Failed to append email")
        
        # Save state
        self.save_state()
        
        print(f"\n{'='*60}")
        print(f"Processing complete!")
        print(f"✓ Successfully processed {successful_emails} new emails")

        print(f"📊 Total processed emails: {len(self.processed_ids)}")

        print(f"{'='*60}")
    
    def create_spreadsheet(self):
        return self.sheets_service.create_spreadsheet('Gmail Email Logs')
    
    def configure_filters_interactive(self):
        """Interactive filter configuration."""
        print("\n" + "=" * 60)
        print("FILTER CONFIGURATION")
        print("=" * 60)
        
        filters = {'enabled': False}
        
        enable = input("\nEnable email filtering? (y/n): ").lower().strip()
        if enable != 'y':
            filters['enabled'] = False
            return filters
        
        filters['enabled'] = True
        
        # Subject keywords
        print("\n📨 SUBJECT FILTERING")
        print("Enter keywords to match in subject (comma-separated)")
        print("Example: invoice,payment,receipt")
        print("Leave empty to skip subject filtering")
        
        subject_input = input("Subject keywords: ").strip()
        if subject_input:
            keywords = [k.strip() for k in subject_input.split(',') if k.strip()]
            filters['subject_keywords'] = keywords
            print(f"  Set {len(keywords)} subject keyword(s)")
        
        # Sender domains
        print("\n📧 SENDER DOMAIN FILTERING")
        print("Enter domains to allow (comma-separated)")
        print("Example: gmail.com,company.com,example.org")
        print("Leave empty to allow all domains")
        
        domain_input = input("Allowed domains: ").strip()
        if domain_input:
            domains = [d.strip() for d in domain_input.split(',') if d.strip()]
            filters['sender_domains'] = domains
            print(f"  Set {len(domains)} allowed domain(s)")
        
        # Date range
        print("\n📅 DATE RANGE FILTERING")
        print("Enter date range (YYYY-MM-DD format)")
        print("Leave empty for no date limits")
        
        min_date = input("Start date (YYYY-MM-DD): ").strip()
        if min_date:
            # Validate date format
            if re.match(r'\d{4}-\d{2}-\d{2}', min_date):
                filters['min_date'] = min_date
                print(f"  Start date: {min_date}")
            else:
                print("  ✗ Invalid date format, skipping")
        
        max_date = input("End date (YYYY-MM-DD): ").strip()
        if max_date:
            if re.match(r'\d{4}-\d{2}-\d{2}', max_date):
                filters['max_date'] = max_date
                print(f"  End date: {max_date}")
            else:
                print("  ✗ Invalid date format, skipping")
        
        return filters
    
    def run(self, spreadsheet_id=None):
        if not self.authenticate():
            print("Authentication failed. Exiting.")
            return
        
        if not spreadsheet_id:
            print("No spreadsheet ID provided")
            return
        
        self.process_emails(spreadsheet_id)

def main():
    print("=" * 60)
    print("GMAIL TO GOOGLE SHEETS AUTOMATION")
    print("=" * 60)
    
    # Check for credentials using DIRECT PATH
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n✗ ERROR: 'credentials.json' not found!")
        return
    
    print(f"✓ Found credentials at: {CREDENTIALS_FILE}")
    
    automation = GmailToSheets()
    
    # Load existing config
    spreadsheet_id = automation.load_config()
    
    if not spreadsheet_id:
        print("\nNo spreadsheet configured.")
        choice = input("Create new spreadsheet? (y/n): ").lower().strip()
        
        if choice == 'y':
            if automation.authenticate():
                spreadsheet_id = automation.create_spreadsheet()
                if spreadsheet_id:
                    # Configure filters
                    filters = automation.configure_filters_interactive()
                    automation.save_config(spreadsheet_id, filters)
                    print(f"\n✓ Created and configured new spreadsheet")
                else:
                    print("\n✗ Failed to create spreadsheet")
                    return
            else:
                print("\n✗ Authentication failed")
                return
        else:
            spreadsheet_id = input("\nEnter spreadsheet ID: ").strip()
            if spreadsheet_id:
                # Configure filters
                filters = automation.configure_filters_interactive()
                automation.save_config(spreadsheet_id, filters)
                print(f"\n✓ Saved spreadsheet ID and filters to config")
            else:
                print("\n✗ No spreadsheet ID provided")
                return
    
    if spreadsheet_id:
        print(f"\n{'='*60}")
        automation.run(spreadsheet_id)

if __name__ == '__main__':
    main()
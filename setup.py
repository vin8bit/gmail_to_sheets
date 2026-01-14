import json
import os
import sys
import re

# Add src directory to path
sys.path.insert(0, 'src')

def configure_filters():
    """Interactive filter configuration for setup."""
    print("\n" + "=" * 60)
    print("EMAIL FILTER CONFIGURATION")
    print("=" * 60)
    
    filters = {'enabled': False}
    
    print("\nEmail filtering allows you to process only specific emails.")
    print("You can filter by subject keywords, sender domains, or date range.")
    
    enable = input("\nEnable email filtering during setup? (y/n): ").lower().strip()
    if enable != 'y':
        filters['enabled'] = False
        print("\n⚠️  Filtering disabled. All emails will be processed.")
        return filters
    
    filters['enabled'] = True
    
    # Subject keywords
    print("\n📨 SUBJECT FILTERING")
    print("Enter keywords to match in email subjects (comma-separated)")
    print("Example: invoice, payment, receipt, order")
    print("Only emails containing these words in the subject will be processed.")
    print("Leave empty to skip subject filtering")
    
    subject_input = input("\nSubject keywords: ").strip()
    if subject_input:
        keywords = [k.strip() for k in subject_input.split(',') if k.strip()]
        filters['subject_keywords'] = keywords
        print(f"  ✓ Set {len(keywords)} subject keyword(s): {', '.join(keywords)}")
    else:
        print("  ⚡ No subject filtering")
    
    # Sender domains
    print("\n📧 SENDER DOMAIN FILTERING")
    print("Enter email domains to allow (comma-separated)")
    print("Example: gmail.com, company.com, example.org")
    print("Only emails from these domains will be processed.")
    print("Leave empty to allow emails from all domains")
    
    domain_input = input("\nAllowed domains: ").strip()
    if domain_input:
        domains = [d.strip() for d in domain_input.split(',') if d.strip()]
        filters['sender_domains'] = domains
        print(f"  ✓ Set {len(domains)} allowed domain(s): {', '.join(domains)}")
    else:
        print("  ⚡ No domain filtering")
    
    # Date range
    print("\n📅 DATE RANGE FILTERING")
    print("Enter date range in YYYY-MM-DD format")
    print("Example: 2024-01-01 to 2024-12-31")
    print("Leave empty for no date limits")
    
    min_date = input("\nStart date (YYYY-MM-DD): ").strip()
    if min_date:
        if re.match(r'\d{4}-\d{2}-\d{2}', min_date):
            filters['min_date'] = min_date
            print(f"  ✓ Start date: {min_date}")
        else:
            print(f"  ✗ Invalid date format: {min_date}")
            print("  ⚡ Skipping date filtering")
    else:
        print("  ⚡ No start date limit")
    
    max_date = input("End date (YYYY-MM-DD): ").strip()
    if max_date:
        if re.match(r'\d{4}-\d{2}-\d{2}', max_date):
            filters['max_date'] = max_date
            print(f"  ✓ End date: {max_date}")
        else:
            print(f"  ✗ Invalid date format: {max_date}")
            print("  ⚡ Skipping date filtering")
    else:
        print("  ⚡ No end date limit")
    
    print("\n" + "=" * 60)
    print("FILTER CONFIGURATION COMPLETE!")
    print("=" * 60)
    
    return filters

def setup_config():
    """Helper script to setup configuration."""
    print("=" * 60)
    print("GMAIL TO GOOGLE SHEETS SETUP")
    print("=" * 60)
    
    # Define paths directly
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    CREDENTIALS_FILE = os.path.join(PROJECT_ROOT, 'credentials', 'credentials.json')
    CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.json')
    TOKEN_FILE = os.path.join(PROJECT_ROOT, 'token.pickle')
    
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Credentials path: {CREDENTIALS_FILE}")
    
    # Check for credentials
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n❌ ERROR: 'credentials.json' not found!")
        print(f"Expected location: {CREDENTIALS_FILE}")
        print("\nPlease download it from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create credentials (Desktop app type)")
        print("3. Enable Gmail API and Sheets API")
        print(f"4. Download as 'credentials.json' and place it in: {os.path.dirname(CREDENTIALS_FILE)}")
        
        # Create credentials directory if it doesn't exist
        credentials_dir = os.path.dirname(CREDENTIALS_FILE)
        if not os.path.exists(credentials_dir):
            os.makedirs(credentials_dir, exist_ok=True)
            print(f"\nCreated directory: {credentials_dir}")
            print("Please place your credentials.json file there and run setup again.")
        
        return
    
    print(f"\n✅ Found credentials.json at: {CREDENTIALS_FILE}")
    
    # Clean up any corrupted token files
    if os.path.exists('token.json'):
        try:
            os.remove('token.json')
            print("✅ Removed corrupted token.json")
        except:
            pass
    
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
            print("✅ Removed old token.pickle")
        except:
            pass
    
    # Import after checking prerequisites
    try:
        from main import GmailToSheets
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("Make sure you're running from the project root directory")
        print("Current directory:", os.getcwd())
        return
    
    # Create automation instance
    automation = GmailToSheets()
    
    print("\n📧 Starting authentication...")
    print("A browser window will open for Google OAuth.")
    print("Please log in with the Gmail account you want to process.")
    
    # Authenticate
    if not automation.authenticate():
        print("\n❌ Authentication failed")
        return
    
    print("\n✅ Authentication successful!")
    
    # Configure filters
    filters = configure_filters()
    
    # Spreadsheet setup
    print("\n" + "=" * 30)
    print("SPREADSHEET SETUP")
    print("=" * 30)
    
    print("\nOptions:")
    print("1. Create a new spreadsheet")
    print("2. Use existing spreadsheet")
    
    choice = input("\nChoose option (1 or 2): ").strip()
    
    spreadsheet_id = None
    
    if choice == '1':
        print("\n🔄 Creating new spreadsheet...")
        spreadsheet_id = automation.create_spreadsheet()
        
        if spreadsheet_id:
            # Save config with filters
            config_data = {
                'spreadsheet_id': spreadsheet_id,
                'filters': filters
            }
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            
    elif choice == '2':
        spreadsheet_id = input("\nEnter existing spreadsheet ID: ").strip()
        
        if spreadsheet_id:
            # Test the spreadsheet
            try:
                result = automation.sheets_service.service.spreadsheets().get(
                    spreadsheetId=spreadsheet_id
                ).execute()
                
                print(f"\n✅ Valid spreadsheet: {result.get('properties', {}).get('title')}")
                
                # Save config with filters
                config_data = {
                    'spreadsheet_id': spreadsheet_id,
                    'filters': filters
                }
                
                with open(CONFIG_FILE, 'w') as f:
                    json.dump(config_data, f, indent=2)
                    
                print("✅ Configuration saved with filters!")
                
            except Exception as e:
                print(f"\n❌ Invalid spreadsheet ID or permissions: {e}")
                return
        else:
            print("\n❌ No spreadsheet ID provided")
            return
    
    else:
        print("\n❌ Invalid choice")
        return
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE! 🎉")
    print("=" * 60)

    
    if filters.get('enabled'):
        if filters.get('subject_keywords'):
            print(f"  Subject keywords: {', '.join(filters['subject_keywords'])}")
        if filters.get('sender_domains'):
            print(f"  Allowed domains: {', '.join(filters['sender_domains'])}")
        if filters.get('min_date'):
            print(f"  Start date: {filters['min_date']}")
        if filters.get('max_date'):
            print(f"  End date: {filters['max_date']}")
    
    print("Run the main script")

if __name__ == '__main__':
    setup_config()
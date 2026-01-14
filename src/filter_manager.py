import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def manage_filters():
    """Interactive filter management tool."""
    CONFIG_FILE = 'config.json'
    
    if not os.path.exists(CONFIG_FILE):
        print("❌ config.json not found. Run setup first.")
        return
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    filters = config.get('filters', {'enabled': False})
    
    print("=" * 60)
    print("FILTER MANAGEMENT")
    print("=" * 60)
    
    print(f"\nCurrent status: {'ENABLED' if filters.get('enabled') else 'DISABLED'}")
    
    if filters.get('enabled'):
        print("\nCurrent filters:")
        if filters.get('subject_keywords'):
            print(f"  📨 Subjects: {', '.join(filters['subject_keywords'])}")
        if filters.get('sender_domains'):
            print(f"  📧 Domains: {', '.join(filters['sender_domains'])}")
        if filters.get('min_date'):
            print(f"  📅 From: {filters['min_date']}")
        if filters.get('max_date'):
            print(f"  📅 To: {filters['max_date']}")
    
    print("\nOptions:")
    print("1. Enable/disable filtering")
    print("2. Update subject keywords")
    print("3. Update sender domains")
    print("4. Update date range")
    print("5. Clear all filters")
    print("6. View filter stats")
    print("7. Exit")
    
    choice = input("\nSelect option (1-7): ").strip()
    
    if choice == '1':
        current = filters.get('enabled', False)
        new_state = not current
        filters['enabled'] = new_state
        print(f"✓ Filtering {'ENABLED' if new_state else 'DISABLED'}")
    
    elif choice == '2':
        print("\nCurrent subject keywords:", filters.get('subject_keywords', []))
        print("Enter new keywords (comma-separated, empty to clear):")
        keywords_input = input("Keywords: ").strip()
        
        if keywords_input:
            keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
            filters['subject_keywords'] = keywords
            print(f"✓ Updated to {len(keywords)} keyword(s)")
        else:
            filters.pop('subject_keywords', None)
            print("✓ Cleared subject keywords")
    
    elif choice == '3':
        print("\nCurrent allowed domains:", filters.get('sender_domains', []))
        print("Enter new domains (comma-separated, empty to clear):")
        domains_input = input("Domains: ").strip()
        
        if domains_input:
            domains = [d.strip() for d in domains_input.split(',') if d.strip()]
            filters['sender_domains'] = domains
            print(f"✓ Updated to {len(domains)} domain(s)")
        else:
            filters.pop('sender_domains', None)
            print("✓ Cleared domain filters")
    
    elif choice == '4':
        print("\nCurrent date range:")
        print(f"  Start: {filters.get('min_date', 'Not set')}")
        print(f"  End: {filters.get('max_date', 'Not set')}")
        
        min_date = input("\nNew start date (YYYY-MM-DD, empty to clear): ").strip()
        if min_date:
            filters['min_date'] = min_date
            print(f"✓ Start date: {min_date}")
        else:
            filters.pop('min_date', None)
            print("✓ Cleared start date")
        
        max_date = input("New end date (YYYY-MM-DD, empty to clear): ").strip()
        if max_date:
            filters['max_date'] = max_date
            print(f"✓ End date: {max_date}")
        else:
            filters.pop('max_date', None)
            print("✓ Cleared end date")
    
    elif choice == '5':
        filters = {'enabled': False}
        print("✓ Cleared all filters")
    
    elif choice == '6':
        print("\n📊 FILTER STATISTICS")
        print(f"  Enabled: {filters.get('enabled', False)}")
        print(f"  Subject keywords: {len(filters.get('subject_keywords', []))}")
        print(f"  Allowed domains: {len(filters.get('sender_domains', []))}")
        if filters.get('min_date'):
            print(f"  Date range: {filters.get('min_date')} to {filters.get('max_date', 'present')}")
        return  # Don't save for view-only
    
    elif choice == '7':
        print("Exiting without changes")
        return
    
    else:
        print("❌ Invalid choice")
        return
    
    # Save changes
    config['filters'] = filters
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Filters saved to {CONFIG_FILE}")

if __name__ == '__main__':
    manage_filters()
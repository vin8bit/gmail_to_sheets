import base64
import re
import html
from datetime import datetime
from html.parser import HTMLParser

class HTMLFilter(HTMLParser):
    """Simple HTML to text converter."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.ignore_tags = ['script', 'style', 'head', 'title', 'meta']
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if tag.lower() in ['p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']:
            self.text.append('\n')
        elif tag.lower() == 'td':
            self.text.append(' ')
            
    def handle_endtag(self, tag):
        self.current_tag = None
        if tag.lower() in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ul', 'ol']:
            self.text.append('\n')
            
    def handle_data(self, data):
        if self.current_tag not in self.ignore_tags:
            # Clean and add text
            cleaned = data.strip()
            if cleaned:
                self.text.append(cleaned)
                
    def get_text(self):
        # Join text and clean up
        result = ' '.join(self.text)
        # Remove multiple newlines
        result = re.sub(r'\n\s*\n', '\n', result)
        # Remove multiple spaces
        result = re.sub(r'\s+', ' ', result)
        return result.strip()

class EmailParser:
    @staticmethod
    def parse_email(message, include_html=False):
        """Parse email details from message object.
        
        Args:
            message: Raw email message from Gmail API
            include_html: If True, include HTML body in output
            
        Returns:
            Dictionary with email details or None if parsing fails
        """
        if not message:
            return None
            
        # Extract headers
        headers = message['payload']['headers']
        
        # Initialize variables
        from_email = ''
        subject = ''
        date_received = ''
        
        # Parse headers
        for header in headers:
            name = header['name'].lower()
            if name == 'from':
                from_email = header['value']
                # Extract just email if format is "Name <email>"
                match = re.search(r'<([^>]+)>', from_email)
                if match:
                    from_email = match.group(1)
                else:
                    # Just get the email part if it's simple
                    from_email = from_email.split()[-1] if '@' in from_email else from_email
            elif name == 'subject':
                subject = header['value']
            elif name == 'date':
                date_received = header['value']
        
        # Parse body - get both plain text and HTML
        plain_text, html_text = EmailParser.get_email_bodies(message['payload'])
        
        # Convert HTML to text if plain text is empty or poor
        if not plain_text and html_text:
            plain_text = EmailParser.html_to_text(html_text)
        elif plain_text and html_text and len(plain_text) < 50:
            # Plain text is too short, try HTML
            plain_text = EmailParser.html_to_text(html_text)
        
        # Clean body - remove excessive whitespace
        plain_text = re.sub(r'\s+', ' ', plain_text).strip() if plain_text else ""
        
        # Convert date to readable format
        date_received = EmailParser.parse_date(date_received)
        
        # Prepare result
        result = {
            'id': message['id'],
            'from': from_email,
            'subject': subject[:200],  # Limit subject length
            'date': date_received,
            'body': plain_text[:5000]  # Limit body length for Sheets
        }
        
        # Include HTML if requested
        if include_html and html_text:
            result['html_body'] = html_text[:10000]  # Longer limit for HTML
        
        return result
    
    @staticmethod
    def get_email_bodies(payload):
        """Extract both plain text and HTML bodies from email payload."""
        plain_text = ""
        html_text = ""
        
        def extract_from_part(part):
            nonlocal plain_text, html_text
            mime_type = part.get('mimeType', '').lower()
            
            if mime_type == 'text/plain':
                if 'data' in part['body']:
                    text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    if not plain_text or len(text) > len(plain_text):
                        plain_text = text
                        
            elif mime_type == 'text/html':
                if 'data' in part['body']:
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    if not html_text or len(html) > len(html_text):
                        html_text = html
                        
            elif mime_type.startswith('multipart/'):
                # Recursively check multipart parts
                for subpart in part.get('parts', []):
                    extract_from_part(subpart)
        
        # Check payload
        if 'parts' in payload:
            for part in payload['parts']:
                extract_from_part(part)
        else:
            # Single part email
            mime_type = payload.get('mimeType', '').lower()
            if 'data' in payload.get('body', {}):
                data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                if mime_type == 'text/plain':
                    plain_text = data
                elif mime_type == 'text/html':
                    html_text = data
        
        return plain_text, html_text
    
    @staticmethod
    def html_to_text(html_content):
        """Convert HTML to plain text."""
        if not html_content:
            return ""
        
        try:
            # First, unescape HTML entities
            unescaped = html.unescape(html_content)
            
            # Use HTML parser for better conversion
            parser = HTMLFilter()
            parser.feed(unescaped)
            text = parser.get_text()
            
            # If parser didn't work well, fallback to regex
            if not text or len(text) < 10:
                # Remove script and style tags
                text = re.sub(r'<(script|style).*?>.*?</\1>', '', unescaped, flags=re.DOTALL | re.IGNORECASE)
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                # Clean up whitespace
                text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            print(f"HTML conversion error: {e}")
            # Fallback: remove tags with regex
            text = re.sub(r'<[^>]+>', ' ', html_content)
            return re.sub(r'\s+', ' ', text).strip()
    
    @staticmethod
    def parse_date(date_string):
        """Parse date string to readable format."""
        if not date_string:
            return ""
            
        try:
            # Try multiple date formats
            date_formats = [
                '%a, %d %b %Y %H:%M:%S %z',
                '%d %b %Y %H:%M:%S %z',
                '%Y-%m-%d %H:%M:%S',
                '%d %b %Y %H:%M:%S %z (%Z)',
                '%Y/%m/%d %H:%M:%S'
            ]
            
            # Remove timezone name if present
            date_str_clean = date_string.split(' (')[0].split(' GMT')[0]
            
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(date_str_clean, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    continue
        except:
            pass  # Keep original format if parsing fails
        
        return date_string
    
    @staticmethod
    def extract_keywords(text, keywords):
        """Extract lines containing specific keywords from text."""
        if not text or not keywords:
            return []
        
        results = []
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower()
            for keyword in keywords:
                if keyword.lower() in line_lower:
                    results.append(line.strip())
                    break
        
        return results
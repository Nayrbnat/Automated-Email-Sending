# Email Automation System

A Python-based email automation system designed for bulk email campaigns with template personalization, OAuth 2.0 authentication, and multi-provider support (Zoho Mail & Gmail).

## 🚀 Core Features

### Multi-Provider Email Support
- **Zoho Mail API**: Full integration with Zoho Mail API v1
- **Gmail API/SMTP**: OAuth 2.0 authenticated Gmail sending
- Provider-agnostic architecture with swappable backends

### Authentication & Security
- **OAuth 2.0 Flow**: Secure token-based authentication for both providers
- **Environment Variable Support**: Sensitive credentials stored in `.env` files
- **Automatic Token Refresh**: Built-in token lifecycle management
- **Region-Aware**: Supports Zoho's regional endpoints (.eu, .com, .in, etc.)

### Template Engine
- **HTML Email Templates**: Full HTML support with CSS styling
- **Variable Substitution**: Dynamic personalization using `$variable` syntax
  - `$name` - Full name
  - `$first_name` - First name only
  - `$last_name` - Last name
  - `$email` - Recipient email address
- **Image Embedding**: Inline images using base64 encoding or CID references
- **Template Files**: External HTML template files in `templates/` directory

### Bulk Email Processing
- **Batch Processing**: Configurable batch sizes with rate limiting
- **Multiple Input Formats**:
  - CSV files with name and email columns
  - Text files with email lists
  - Direct Python lists
- **Smart Name Parsing**: Handles various name formats:
  - `FirstName LastName email@domain.com`
  - `LastName,FirstInitial (ug) email@domain.com`
  - `LastName, FirstName email@domain.com`

### Built-in Campaign Templates
Pre-configured templates for common scenarios:
- **Welcome** (`MBP_freshers_template.html`) - New member onboarding
- **Acceptance** (`MBP_acceptance.html`) - Application acceptance
- **Rejection** (`MBP_rejection.html`) - Application rejection
- **Follow-up** (`MBP_freshers_followup.html`) - Engagement follow-up
- **Membership** (`MBP_membership.html`) - Membership reminders

## 📋 System Architecture

### Core Classes

#### `EmailConfig` (Dataclass)
```python
@dataclass
class EmailConfig:
    client_id: str
    client_secret: str
    sender_email: str
    refresh_token: str
    sender_name: str
    provider: str  # 'zoho' or 'gmail'
```

#### `ConfigManager`
Manages configuration loading and environment variable resolution.

**Key Methods:**
- `load_config(config_file)` - Loads JSON configuration
- `create_email_config(config_data, provider)` - Creates provider-specific config
- `_get_env_or_config(config_value, env_var, default)` - Resolves `ENV:` references

#### `FileLoader`
Handles email address loading from various sources.

**Key Methods:**
- `load_emails(source, email_column)` - Universal email loader
- `load_csv_with_names(file_path, name_column, email_column)` - CSV with name extraction
- `_validate_emails(email_list)` - Email validation

#### `EmailParser`
Parses email entries to extract structured student data.

**Key Methods:**
- `parse_student_entry(entry)` - Converts text to `Student` object
  - Handles `"FirstName LastName email@domain.com"` format
  - Handles `"LastName,FirstInitial (ug) email@domain.com"` format
  - Returns `Student(email, name, first_name, last_name)`

#### `EmailTemplateEngine`
Template loading and personalization engine.

**Key Methods:**
- `create_personalized_email(student)` - Applies template variables
- `load_template_from_file(template_path)` - Loads HTML template
- Uses Python's `string.Template` for safe substitution (avoids CSS `{}` conflicts)

#### `ZohoAuthManager`
Manages Zoho OAuth 2.0 authentication lifecycle.

**Key Methods:**
- `get_access_token()` - Returns valid access token (refreshes if expired)
- `_refresh_access_token()` - Exchanges refresh token for new access token
- Token caching with expiration tracking

**OAuth Flow:**
1. Uses refresh token from config
2. Requests access token from `https://accounts.zoho.eu/oauth/v2/token`
3. Caches token with expiration timestamp
4. Auto-refreshes when expired

#### `ZohoEmailSender`
Zoho Mail API email sending implementation.

**Key Methods:**
- `send_email(to_email, subject, body, is_html)` - Basic email sending
- `send_email_with_embedded_images(to_email, subject, body, logo_path, signature_path, qrcode_path)` - Emails with inline images
- `send_email_with_inline_image(to_email, subject, body, image_path)` - Single image attachment
- `send_bulk_emails(students, template_engine, batch_size, batch_delay_minutes)` - Batch processing with rate limiting
- `get_account_id()` - Retrieves Zoho account ID for API calls

**API Endpoints:**
- Base URL: `https://mail.zoho.eu/api`
- Account listing: `GET /accounts`
- Send message: `POST /accounts/{accountId}/messages`

**Image Handling:**
- Converts images to base64 data URLs
- Replaces `cid:logo`, `cid:signature`, `cid:qrcode` references
- Supports PNG, JPG, and other formats via MIME type detection

#### `GmailOAuth2Manager`
Gmail OAuth 2.0 token management with persistent storage.

**Key Methods:**
- `get_access_token()` - Returns valid OAuth token
- `_load_token()` - Loads cached token from `gmail_token.json`
- `_save_token(token_data)` - Persists token to disk
- `_refresh_access_token()` - Refreshes expired tokens
- `_perform_oauth_flow()` - Interactive OAuth authorization

**Token Storage:**
- File: `gmail_token.json`
- Contains: `access_token`, `refresh_token`, `expires_at`
- Auto-refresh on expiration

#### `GmailEmailSender`
Gmail API email sending with MIME message construction.

**Key Methods:**
- `send_email(to_email, subject, body, is_html)` - Simple email
- `send_email_with_embedded_images(...)` - Multipart emails with CID images
- `send_bulk_emails(...)` - Batch processing
- `_embed_image(message, image_path, cid)` - Embeds image with Content-ID
- `_send_via_gmail_api(message, access_token, to_email)` - Gmail API submission

**MIME Structure:**
```
multipart/related
  └─ multipart/alternative
      └─ text/html (body)
  └─ image/png (logo) [Content-ID: logo]
  └─ image/png (signature) [Content-ID: signature]
  └─ image/png (qrcode) [Content-ID: qrcode]
```

#### `EmailAutomationSystem`
High-level orchestration system combining all components.

**Key Methods:**
- `process_email_list(file_path=None, email_list=None, config_data=None, template_type='welcome', subject_template=None, body_template=None)` - Main entry point
- `_get_template_body(template_type)` - Maps template names to files
- `_get_template_subject(template_type, custom_subject)` - Maps subjects
- `_send_emails(sender, students, template_engine)` - Delegates to provider

**Workflow:**
1. Parse input (file or list)
2. Load template (from file or config)
3. Initialize provider-specific sender
4. Create template engine
5. Send emails in batches
6. Return results dictionary

## 🔧 Configuration

### `config.json`
```json
{
  "zoho_config": {
    "client_id": "ENV:ZOHO_CLIENT_ID",
    "client_secret": "ENV:ZOHO_CLIENT_SECRET",
    "refresh_token": "ENV:ZOHO_REFRESH_TOKEN",
    "sender_email": "ENV:ZOHO_SENDER_EMAIL",
    "sender_name": "ENV:ZOHO_SENDER_NAME"
  },
  "gmail_config": {
    "client_id": "ENV:GMAIL_CLIENT_ID",
    "client_secret": "ENV:GMAIL_CLIENT_SECRET",
    "sender_email": "ENV:GMAIL_SENDER_EMAIL",
    "sender_name": "ENV:GMAIL_SENDER_NAME"
  },
  "settings": {
    "batch_size": 75,
    "batch_delay_minutes": 0.75,
    "max_retries": 3,
    "save_results": true
  }
}
```

### `.env` File
```bash
# Zoho Configuration
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_SENDER_EMAIL=sender@domain.com
ZOHO_SENDER_NAME=Your Name

# Gmail Configuration
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_SENDER_EMAIL=sender@gmail.com
GMAIL_SENDER_NAME=Your Name
```

**Environment Variable Resolution:**
- Config values starting with `ENV:` are resolved from environment
- Falls back to direct config value if env var not set
- Supports `.env` file via `python-dotenv`

## 📦 Dependencies

```
requests        # HTTP client for API calls
python-dotenv   # Environment variable management
google-auth     # Google OAuth libraries
google-auth-oauthlib
pytz           # Timezone handling
```

Install via:
```bash
pip install -r requirements.txt
```

## 🎯 Usage Examples

### Command Line Interface

#### Basic Usage
```bash
# Send welcome emails (default)
python email_send.py

# Use specific provider
python email_send.py --provider gmail
python email_send.py --provider zoho

# Use specific template
python email_send.py --template acceptance
python email_send.py --template rejection
python email_send.py --template followup
python email_send.py --template membership
```

#### CSV File Processing
```bash
# Process UG1 members list
python email_send.py --UG1 --template welcome

# Process bootcamp applicants
python email_send.py --bootcamp --template membership

# Acceptance emails (auto-loads acceptance.csv)
python email_send.py --template acceptance --provider gmail

# Rejection emails (auto-loads rejection.csv)
python email_send.py --template rejection --provider gmail
```

#### Test Mode
```bash
# Parse and validate without sending
python email_send.py --template acceptance --test
python email_send.py --UG1 --test
```

#### Custom Subject
```bash
# Override default subject line
python email_send.py --template welcome --subject "Welcome to MBP, \$first_name!"
```

### Programmatic Usage

#### Example 1: Simple Bulk Email
```python
from email_send import ConfigManager, EmailAutomationSystem

# Load configuration
config_data = ConfigManager.load_config()
email_config = ConfigManager.create_email_config(config_data, provider="gmail")
settings = config_data.get('settings', {})

# Initialize system
automation = EmailAutomationSystem(email_config, settings)

# Send emails
results = automation.process_email_list(
    file_path="sample_emails.txt",
    config_data=config_data,
    template_type='welcome'
)

print(f"Sent: {results['emails_sent']}/{results['total_emails']}")
```

#### Example 2: Custom Template
```python
from email_send import (
    ConfigManager, 
    EmailAutomationSystem, 
    EmailTemplateEngine
)

# Load config
config_data = ConfigManager.load_config()
email_config = ConfigManager.create_email_config(config_data, provider="zoho")

# Load custom template
template_body = EmailTemplateEngine.load_template_from_file(
    "templates/custom_template.html"
)

# Process with custom template
automation = EmailAutomationSystem(email_config, {})
results = automation.process_email_list(
    email_list=["user@example.com", "test@example.com"],
    subject_template="Hello $first_name!",
    body_template=template_body
)
```

#### Example 3: CSV with Name Extraction
```python
from email_send import FileLoader, EmailParser

# Load CSV with names
entries = FileLoader.load_csv_with_names(
    "members.csv", 
    name_column=0,  # First column is name
    email_column=1  # Second column is email
)

# Parse entries
students = [EmailParser.parse_student_entry(entry) for entry in entries]

# Access structured data
for student in students:
    print(f"Name: {student.name}, Email: {student.email}")
    print(f"First: {student.first_name}, Last: {student.last_name}")
```

## 🔐 OAuth Setup

### Zoho OAuth Setup

1. **Create Zoho API Client:**
   - Go to [Zoho Developer Console](https://api-console.zoho.eu/)
   - Create new "Self Client" application
   - Note your `Client ID` and `Client Secret`

2. **Generate Refresh Token:**
   ```bash
   python generate_fresh_token.py
   ```
   - Follow the interactive prompts
   - Visit the authorization URL
   - Grant permissions
   - Copy the authorization code from redirect URL
   - Script generates refresh token

3. **Required Scopes:**
   - `ZohoMail.messages.CREATE`
   - `ZohoMail.accounts.READ`
   - `ZohoMail.messages.READ`
   - `ZohoMail.folders.READ`

4. **Test Token:**
   ```bash
   python test_token.py
   ```
   Tests token across different Zoho regions

### Gmail OAuth Setup

1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project
   - Enable Gmail API

2. **Create OAuth Credentials:**
   - Navigate to "APIs & Services" → "Credentials"
   - Create "OAuth 2.0 Client ID"
   - Application type: Desktop app
   - Download credentials JSON

3. **Configure Application:**
   - Extract `client_id` and `client_secret` from downloaded JSON
   - Add to `.env` file

4. **First Run Authentication:**
   ```bash
   python email_send.py --provider gmail
   ```
   - Browser opens for authorization
   - Grant Gmail permissions
   - Token saved to `gmail_token.json`
   - Subsequent runs use cached token

## 📁 File Structure

```
Email Automation/
├── email_send.py                    # Main automation script (1524 lines)
├── generate_fresh_token.py          # Zoho OAuth token generator
├── test_token.py                    # Token testing utility
├── template_demo.py                 # Template usage examples
├── config.json                      # Configuration file
├── requirements.txt                 # Python dependencies
├── gmail_token.json                 # Gmail OAuth tokens (generated)
│
├── templates/                       # HTML email templates
│   ├── MBP_freshers_template.html   # Welcome email
│   ├── MBP_acceptance.html          # Acceptance notification
│   ├── MBP_rejection.html           # Rejection notification
│   ├── MBP_freshers_followup.html   # Follow-up email
│   ├── MBP_membership.html          # Membership reminder
│   └── README.md                    # Template documentation
│
├── image/                           # Email assets
│   ├── MBP.png                      # Logo
│   ├── signature.png                # Email signature
│   └── qrcode.png                   # QR code
│
├── acceptance.csv                   # Acceptance list (auto-loaded)
├── rejection.csv                    # Rejection list (auto-loaded)
├── bootcamp_applicants.csv          # Bootcamp list
├── UG1_members_clean.csv            # Member list
├── sample_emails.txt                # Demo/test list
└── sample_students.csv              # Sample data
```

## 🔍 Key Implementation Details

### Batch Processing Algorithm
```python
def send_bulk_emails(students, batch_size=50, batch_delay_minutes=1):
    for batch_start in range(0, len(students), batch_size):
        batch_end = min(batch_start + batch_size, len(students))
        current_batch = students[batch_start:batch_end]
        
        # Send emails in batch
        for student in current_batch:
            send_email(student)
            time.sleep(1)  # Rate limiting between emails
        
        # Delay between batches
        if batch_end < len(students):
            time.sleep(batch_delay_minutes * 60)
```

### Template Variable Substitution
Uses `string.Template.safe_substitute()` to avoid conflicts with CSS:
```python
template = Template(html_content)
personalized = template.safe_substitute(
    name=student.name,
    first_name=student.first_name,
    last_name=student.last_name,
    email=student.email
)
```

### Image Embedding Strategy

**Zoho:** Base64 data URLs
```python
logo_b64 = base64.b64encode(logo_file.read()).decode()
body = body.replace('src="cid:logo"', f'src="data:image/png;base64,{logo_b64}"')
```

**Gmail:** CID attachments
```python
image = MIMEImage(image_data)
image.add_header('Content-ID', '<logo>')
image.add_header('Content-Disposition', 'inline', filename='logo.png')
message.attach(image)
```

### Error Handling
- **Network Errors**: Retries with exponential backoff
- **Auth Errors**: Token refresh with fallback
- **Parsing Errors**: Logged and skipped, processing continues
- **File Errors**: Graceful fallback to default templates

### Logging Levels
```python
# Set in logging.basicConfig()
DEBUG   # Detailed token/API information
INFO    # Email sent confirmations, batch progress
WARNING # Non-fatal issues (missing images)
ERROR   # Failed sends, authentication failures
```

## ⚙️ Rate Limiting & Best Practices

### Zoho Limits
- **Rate Limit**: ~200 emails/hour per account
- **Batch Size**: 75 emails (configurable)
- **Batch Delay**: 45 seconds (0.75 minutes)
- **Per-Email Delay**: 1 second

### Gmail Limits
- **Rate Limit**: 500 emails/day (standard account), 2000/day (Google Workspace)
- **Batch Size**: 50 emails recommended
- **Batch Delay**: 60 seconds
- **Per-Email Delay**: 1 second

### Configuration
Adjust in `config.json`:
```json
"settings": {
  "batch_size": 75,              // Emails per batch
  "batch_delay_minutes": 0.75,   // Wait between batches
  "max_retries": 3,              // Retry failed sends
  "save_results": true           // Log results to file
}
```

## 🐛 Debugging Tools

### Test Token Script
```bash
python test_token.py
```
- Tests Zoho token across all regions (.com, .eu, .in, .com.au, .co.uk)
- Validates OAuth configuration
- Shows detailed error messages

### Test Mode
```bash
python email_send.py --template acceptance --test
```
- Parses CSV and displays parsed entries
- Shows what would be sent
- No actual emails sent

### Verbose Logging
```python
# In email_send.py
logging.basicConfig(level=logging.DEBUG)  # Show all debug messages
```

## 📊 Return Values

All email operations return a results dictionary:
```python
{
    'total_emails': int,      # Total emails processed
    'emails_sent': int,       # Successfully sent
    'emails_failed': int,     # Failed to send
    'students': [Student],    # Parsed student objects
    'parsing_errors': [str],  # List of parsing errors
    'failed_emails': [str]    # Failed email addresses
}
```

## 🔒 Security Considerations

- **No Hardcoded Credentials**: All sensitive data in `.env`
- **Token Storage**: OAuth tokens in secure local files
- **HTTPS Only**: All API calls use encrypted connections
- **Scope Minimization**: Only request necessary OAuth permissions
- **Token Expiration**: Automatic refresh prevents stale tokens
- **Gitignore**: `.env`, `gmail_token.json`, `*.csv` excluded from version control

## 🚦 Status Codes & Error Messages

### Zoho API
- `200` - Success
- `401` - Authentication failed (invalid/expired token)
- `403` - Insufficient permissions
- `429` - Rate limit exceeded
- `500` - Zoho server error

### Gmail API
- `200` - Success
- `401` - Invalid OAuth token
- `403` - Insufficient Gmail API quota
- `429` - Rate limit exceeded

## 📝 Template Development

### Creating Custom Templates

1. **Create HTML File:**
   ```html
   <!DOCTYPE html>
   <html>
   <body>
       <h1>Hello $first_name!</h1>
       <p>Welcome $name!</p>
       <img src="cid:logo" alt="Logo"/>
   </body>
   </html>
   ```

2. **Use Variables:**
   - `$name` - Full name
   - `$first_name` - First name
   - `$last_name` - Last name
   - `$email` - Email address

3. **Image References:**
   - `cid:logo` - References `image/MBP.png`
   - `cid:signature` - References `image/signature.png`
   - `cid:qrcode` - References `image/qrcode.png`

4. **Load in Code:**
   ```python
   template = EmailTemplateEngine.load_template_from_file(
       "templates/custom.html"
   )
   ```

## 🤝 Contributing

When extending the system:

1. **Add New Provider:**
   - Implement `*AuthManager` class
   - Implement `*EmailSender` class
   - Add config section in `config.json`
   - Update `EmailAutomationSystem._send_emails()`

2. **Add New Template:**
   - Create HTML file in `templates/`
   - Add template mapping in `_get_template_body()`
   - Add subject mapping in `_get_template_subject()`
   - Update CLI argument options

3. **Add CSV Format:**
   - Extend `EmailParser.parse_student_entry()`
   - Add new parsing logic for format
   - Update documentation with format example

## 📄 License

Internal use for MBP Capital email automation.

---

**Version:** 2.0  
**Last Updated:** February 2026  
**Python Version:** 3.8+

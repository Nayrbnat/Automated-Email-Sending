# Email Automation System

A config-driven email automation system for MBP Capital. Supports bulk email campaigns with HTML template personalization, OAuth 2.0 authentication, and multi-provider support (Zoho Mail & Gmail).

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Send a campaign (dry-run first)
python send.py --template acceptance --test

# Send for real
python send.py --template acceptance --provider zoho
```

## Adding a New Campaign

**No Python code changes needed.** Three steps:

1. Create `templates/my_campaign.html` using `$first_name`, `$last_name`, `$name`, `$email` variables
2. Add an entry to `config.json` under `"templates"`:
   ```json
   "my_campaign": {
     "subject": "Hello $first_name - Campaign Subject",
     "template_file": "templates/my_campaign.html",
     "csv_file": "data/my_campaign.csv",
     "csv_loader": "names",
     "description": "Description of campaign"
   }
   ```
3. Place your CSV at `data/my_campaign.csv` (columns: name, email)

**AI-Assisted:** Attach `new_email.md` to any AI model and describe the campaign you need. The AI will create the HTML template and config entry for you.

See `new_email.md` for full documentation on template variables, CSV loader types, and HTML conventions.

## Project Structure

```
Automated-Email-Sending/
├── send.py              # CLI entry point
├── config.json          # Template registry + provider config + settings
├── new_email.md         # AI runbook for creating new campaigns
├── .env                 # Credentials (not in git)
├── requirements.txt     # Python dependencies
│
├── core/                # Python modules (do not edit for new campaigns)
│   ├── config.py        # Configuration loading
│   ├── models.py        # Data classes (EmailConfig, TemplateSpec, Student)
│   ├── parser.py        # Name/email parsing
│   ├── loader.py        # CSV/file loading
│   ├── template_engine.py  # Template personalization + image embedding
│   ├── sender_base.py   # Abstract sender + batch logic + factory
│   ├── sender_zoho.py   # Zoho Mail API sender
│   ├── sender_gmail.py  # Gmail API sender
│   └── results.py       # Result persistence
│
├── data/                # CSV recipient lists (gitignored, contains PII)
├── templates/           # HTML email templates
├── image/               # Email assets (MBP.png, signature.png, qrcode.png)
└── results/             # Send logs (auto-generated, gitignored)
```

## CLI Usage

```bash
# Available templates (defined in config.json)
python send.py --help

# Send with specific provider
python send.py --template welcome --provider zoho
python send.py --template welcome --provider gmail

# Use predefined recipient lists
python send.py --template welcome --UG1        # UG1 members
python send.py --template welcome --bootcamp   # Bootcamp applicants

# Override subject line
python send.py --template welcome --subject "Custom Subject for \$first_name"

# Send with attachment
python send.py --template acceptance --attach path/to/file.pdf

# Dry-run (parse + display, no emails sent)
python send.py --template stock_pitch_semifinals --test
```

## Available Templates

| Template | Description | CSV |
|----------|-------------|-----|
| `welcome` | New member welcome email | Manual (--UG1 or --bootcamp) |
| `followup` | Freshers follow-up | Manual |
| `acceptance` | Bootcamp acceptance | `data/acceptance.csv` |
| `rejection` | Application rejection | `data/rejection.csv` |
| `membership` | Membership reminder | Manual |
| `stock_pitch_reject` | Stock pitch rejection | `data/stock_pitch_reject.csv` |
| `stock_pitch_semifinals` | Semi-finals invitation | `data/stock_pitch_semi.csv` |
| `stock_pitch_finals` | Finals invitation | `data/stock_pitch_finals_accept.csv` |
| `stock_pitch_finals_reject` | Finals rejection | `data/stock_pitch_finals_reject.csv` |

## Configuration

### `config.json`

Contains three sections:
- **Provider config** (`zoho_config`, `gmail_config`) — credentials reference `.env` via `ENV:` prefix
- **Settings** — batch size, delay, retries
- **Templates** — the template registry (see "Adding a New Campaign" above)

### `.env` File

```bash
# Zoho
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_SENDER_EMAIL=info@mbpcapital.co.uk
ZOHO_SENDER_NAME=MBP Executive Committee

# Gmail
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_SENDER_EMAIL=mbpcapital@lsesu.org
GMAIL_SENDER_NAME=MBP Capital Executive Committee
```

## OAuth Setup

### Zoho (Primary Provider)

1. Go to [Zoho Developer Console](https://api-console.zoho.eu/) and create a "Self Client" application
2. Note the `Client ID` and `Client Secret`
3. Generate a refresh token:
   - Go to the Self Client page
   - Enter scopes: `ZohoMail.messages.CREATE,ZohoMail.accounts.READ`
   - Set duration and generate an authorization code
   - Exchange the code for a refresh token using:
     ```bash
     curl -X POST "https://accounts.zoho.eu/oauth/v2/token" \
       -d "grant_type=authorization_code" \
       -d "client_id=YOUR_CLIENT_ID" \
       -d "client_secret=YOUR_CLIENT_SECRET" \
       -d "code=YOUR_AUTH_CODE"
     ```
   - Copy the `refresh_token` from the response into `.env` as `ZOHO_REFRESH_TOKEN`
4. The system auto-refreshes access tokens — no manual token management needed after setup

### Gmail

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Add `client_id` and `client_secret` to `.env`
5. On first run with `--provider gmail`, a browser window opens for authorization
6. Token is cached in `gmail_token.json` for subsequent runs

## Rate Limits

| Provider | Limit | Recommended Batch Size | Batch Delay |
|----------|-------|----------------------|-------------|
| Zoho | ~200 emails/hour | 75 | 45 seconds |
| Gmail | 500/day (standard), 2000/day (Workspace) | 50 | 60 seconds |

Adjust in `config.json` under `"settings"`.

## Dependencies

```
requests         # HTTP client
python-dotenv    # .env file support
google-auth      # Google OAuth
google-auth-oauthlib
pytz             # Timezone handling
```

---

**Version:** 3.0
**Last Updated:** April 2026
**Python:** 3.8+

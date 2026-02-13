# Email Template Directory
This directory contains HTML email templates that can be referenced by the email automation system.

## Available Templates:

### 1. professional_email_template.html
A sophisticated, professional email template with:
- Modern gradient design
- Responsive layout
- Professional styling
- Feature highlights section
- Call-to-action buttons
- Personalized content areas

### 2. custom_invitation_template.html
A vibrant invitation template with:
- Eye-catching gradient header
- Exclusive badge design
- Benefits section
- Premium styling
- VIP-focused messaging

## Usage:

### In Python Code:
```python
# Load template from file
template_content = EmailTemplateEngine.load_template_from_file("templates/professional_email_template.html")

# Use with automation system
automation.process_email_list(
    email_list=emails,
    body_template=template_content
)
```

### In Configuration (config.json):
```json
{
  "email_templates": {
    "welcome_subject": "Welcome {first_name}!",
    "welcome_body": "TEMPLATE_FILE:templates/professional_email_template.html"
  }
}
```

## Template Variables:
All templates support these placeholder variables:
- `{first_name}` - Recipient's first name
- `{last_name}` - Recipient's last name  
- `{name}` - Full name
- `{email}` - Email address

## Adding New Templates:
1. Create a new .html file in this directory
2. Use the placeholder variables for personalization
3. Reference the file in your code or configuration
# MBP Capital Email Automation — AI Runbook

> **Purpose**: Attach this file as context to any AI model (Claude, GPT, Copilot, etc.) so you can say _"create a new email campaign for X"_ and the AI knows exactly what to do.

---

## 1. Project Structure

```
Automated-Email-Sending/
├── config.json          # Template registry + provider config
├── send.py              # CLI entry point
├── core/                # Python modules (DO NOT EDIT for new campaigns)
├── data/                # CSV recipient lists
├── templates/           # HTML email templates
├── image/               # Email assets (logo, signature, QR)
└── results/             # Send logs (auto-generated)
```

---

## 2. How to Add a New Email Campaign

Follow these steps in order:

1. **Create HTML template** at `templates/<campaign_name>.html`
   - Copy the structure from the full example in Section 6 below.
   - Use `$variable` syntax for personalization (Python `string.Template`).
2. **Add entry to `config.json`** under `"templates"` (see schema in Section 3).
3. **Place CSV** at `data/<campaign_name>.csv` (if the campaign needs a recipient list).
4. **Test** (sends only to the sender address):
   ```bash
   python send.py --template <campaign_name> --test
   ```
5. **Send for real**:
   ```bash
   python send.py --template <campaign_name> --provider zoho
   ```

---

## 3. Template JSON Schema

Each campaign is an entry under `"templates"` in `config.json`:

```json
{
  "templates": {
    "campaign_name": {
      "subject": "string - Email subject line, supports $variable substitution",
      "template_file": "string - Path to HTML template (e.g., templates/my_campaign.html)",
      "csv_file": "string (optional) - Path to CSV file (e.g., data/my_list.csv)",
      "csv_loader": "string - 'names' | 'stock_pitch' | 'plain' (see Section 5)",
      "name_column": "int (optional, default 0) - Column index for recipient name in CSV",
      "email_column": "int (optional, default 1) - Column index for recipient email in CSV",
      "description": "string - Human-readable campaign description",
      "cc": ["array (optional) - CC email addresses"],
      "bcc": ["array (optional) - BCC email addresses"]
    }
  }
}
```

### Field details

| Field | Required | Description |
|-------|----------|-------------|
| `subject` | Yes | Subject line. Use `$first_name`, `$last_name`, etc. for personalization. |
| `template_file` | Yes | Relative path to the HTML file in `templates/`. |
| `csv_file` | No | Relative path to the CSV in `data/`. Omit if recipients are provided another way. |
| `csv_loader` | Yes | Determines how the CSV is parsed. One of: `names`, `stock_pitch`, `plain`. |
| `name_column` | No | Zero-based column index for the name field. Defaults to `0`. |
| `email_column` | No | Zero-based column index for the email field. Defaults to `1`. |
| `description` | Yes | Short human-readable label shown in `--list` output. |
| `cc` | No | Array of CC addresses applied to every email in the campaign. |
| `bcc` | No | Array of BCC addresses applied to every email in the campaign. |

---

## 4. Available Template Variables

### Standard variables (all loaders)

| Variable | Description |
|----------|-------------|
| `$first_name` | Recipient's first name (extracted from the name column) |
| `$last_name` | Recipient's last name (extracted from the name column) |
| `$name` | Full name |
| `$email` | Recipient's email address |

### Stock pitch variables (stock_pitch loader only)

| Variable | Description |
|----------|-------------|
| `$team_name` | Competition team name |
| `$room_number` | Assigned presentation room |
| `$presentation_slot` | Slot number |
| `$presentation_time` | Formatted time string |
| `$zoom_link` | Zoom meeting URL |
| `$zoom_meeting_id` | Zoom meeting ID |
| `$zoom_password` | Zoom meeting password |

---

## 5. CSV Loader Types

### `names` — Standard name + email list

Use for most campaigns. Two required columns: name and email.

```csv
John Smith,john@example.com
Jane Doe,jane@example.com
```

The system splits the name on the first space to derive `$first_name` and `$last_name`.

### `plain` — Email-only list

Use when you only have email addresses and no names.

```csv
john@example.com
jane@example.com
```

Variables like `$first_name` will be empty or set to a default.

### `stock_pitch` — Multi-column competition data

Use for stock pitch competition emails with team/room/time info.

```csv
Team Alpha,John Smith,john@example.com,Room 101,1,10:00 AM,https://zoom.us/j/123,123456,abc123
```

Columns: team_name, name, email, room_number, presentation_slot, presentation_time, zoom_link, zoom_meeting_id, zoom_password.

---

## 6. Full HTML Template Example

Below is the complete `templates/MBP_acceptance.html` file — the bootcamp acceptance email. Inline comments explain each convention.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MBP Capital - Welcome to the Bootcamp</title>
    <!--
        OUTLOOK COMPATIBILITY BLOCK
        Always include this for proper rendering in Outlook/desktop clients.
        Copy this block verbatim into every new template.
    -->
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:AllowPNG/>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<!--
    STYLING CONVENTIONS:
    - All styles are INLINE (no <style> block) for maximum email client compatibility.
    - Font: Georgia, 'Times New Roman', serif — this is the MBP brand font.
    - Background: #f8f9fa (light grey), content area: #ffffff (white).
    - Text color: #1a1a1a (near-black), accent green: #3a8066.
    - Use tables for layout, NOT divs. Email clients do not support flexbox/grid.
-->
<body style="margin: 0; padding: 0; font-family: Georgia, 'Times New Roman', serif; background-color: #f8f9fa; color: #1a1a1a;">
    
    <!-- Main Container Table — centers the email in the viewport -->
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                
                <!-- Email Container Table — 650px max width with subtle border -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="650" style="max-width: 650px; background-color: #ffffff; border: 1px solid #e8e9ea;">
                    
                    <!--
                        OPTIONAL: Logo header row
                        Uncomment the block below to add the MBP logo at the top.
                        The src="cid:logo" reference maps to image/MBP.png (see Section 7).
                        
                        <tr>
                            <td align="center" style="padding: 30px 0 20px 0; background-color: #ffffff;">
                                <img src="cid:logo" alt="MBP Capital" width="150" style="display: block;">
                            </td>
                        </tr>
                    -->

                    <!-- Main Content -->
                    <tr>
                        <td style="padding: 40px 30px; background-color: #ffffff;">
                            
                            <!-- Email Content -->
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="font-size: 16px; color: #333; line-height: 1.6;">
                                        <!--
                                            VARIABLE USAGE:
                                            $first_name and $last_name are replaced at send time.
                                            These use Python string.Template syntax: $variable
                                            NOT {variable} or {{variable}}.
                                        -->
                                        Dear $first_name $last_name,<br><br>
                                        
                                        I am delighted to offer you a place in the MBP Capital Global Macro Bootcamp. Out of over 200 applications, yours stood out. Your application demonstrated the intellectual curiosity, integrity, and hunger to learn that defines what we look for in our analysts.<br><br>
                                        
                                        <!--
                                            SECTION HEADERS:
                                            Use <strong> with the accent color #3a8066 for section headers.
                                        -->
                                        <strong style="color: #3a8066;">What happens next?</strong><br><br>
                                        
                                        We will be creating a WhatsApp group with all the bootcamp trainees as part of MBP Capital. You'll receive an invitation to join shortly – this will be our primary communication channel for the bootcamp.<br><br>
                                        
                                        The first session will be held at <strong>CBG 1.07</strong> on <strong>Monday, 13th October 2025</strong> from <strong>6pm - 7pm</strong>. Over the coming weeks, you'll work alongside fellow analysts, learn our investment framework, and contribute to live research. This won't be easy – we'll challenge you, push you to think deeper, and expect you to come prepared. But I promise you'll leave with skills and insights that will serve you throughout your investing career.<br><br>
                                        
                                        <strong style="color: #3a8066;">Before the first session:</strong><br>

                                        <!--
                                            BULLET LISTS:
                                            Use raw bullet characters with <br> line breaks.
                                            Do NOT use <ul>/<li> — they render inconsistently in email clients.
                                        -->
                                        • Ensure you have a valid MBP Capital membership through LSESU<br>
                                        • Prepare to bring a notebook, laptop, and an open mind<br>
                                        • <strong>No pre-reading required</strong> for the first session – just show up ready to learn<br><br>
                            
                                        From the 2nd week onwards, pre-readings will be sent out through the WhatsApp group chat before each session. We expect everyone to come prepared.<br><br>
                                        
                                                                               
                                        We're excited to have you join us. See you at the bootcamp.<br><br>
                                        
                                        <!--
                                            SIGN-OFF:
                                            Keep the sign-off format consistent across campaigns.
                                            Update names/titles as needed.
                                            
                                            OPTIONAL: Add a signature image after the sign-off:
                                            <img src="cid:signature" alt="Signature" width="200" style="display: block; margin-top: 10px;">
                                            The src="cid:signature" reference maps to image/signature.png (see Section 7).
                                        -->
                                        Best,<br>
                                        Song Yi & Andriy<br>
                                        <em>Co-President, MBP Capital</em>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
```

### What to replicate vs. customize

| Keep as-is (replicate) | Change per campaign |
|------------------------|---------------------|
| Outlook compatibility block in `<head>` | `<title>` text |
| Outer/inner table structure | Body copy and section headers |
| Inline styles approach | Sign-off names and titles |
| Font stack: Georgia, 'Times New Roman', serif | Which `$variables` you use |
| Color palette (#f8f9fa, #ffffff, #3a8066, #333) | Whether to include logo/signature images |
| `role="presentation"` on all tables | Bullet point content |
| 650px max-width container | Subject line (in config.json) |

---

## 7. Image CID References

Images are embedded as MIME attachments and referenced using `cid:` URIs in the HTML.

| CID reference | File | Description |
|---------------|------|-------------|
| `src="cid:logo"` | `image/MBP.png` | MBP Capital logo |
| `src="cid:signature"` | `image/signature.png` | Executive committee signature |
| `src="cid:qrcode"` | `image/qrcode.png` | Optional QR code (e.g., membership link) |

Usage in HTML:
```html
<img src="cid:logo" alt="MBP Capital" width="150" style="display: block;">
```

Do NOT use external URLs for images — they get blocked by most email clients. Always use CID references.

---

## 8. Example: Adding a Complete Campaign

Let's walk through creating a **"bootcamp_reminder"** campaign from scratch.

### Step 1: Create the HTML template

Create `templates/bootcamp_reminder.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MBP Capital - Bootcamp Reminder</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:AllowPNG/>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; font-family: Georgia, 'Times New Roman', serif; background-color: #f8f9fa; color: #1a1a1a;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f8f9fa;">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="650" style="max-width: 650px; background-color: #ffffff; border: 1px solid #e8e9ea;">
                    <tr>
                        <td style="padding: 40px 30px; background-color: #ffffff;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="font-size: 16px; color: #333; line-height: 1.6;">
                                        Hi $first_name,<br><br>

                                        Just a quick reminder that our next bootcamp session is <strong>tomorrow</strong>.<br><br>

                                        <strong style="color: #3a8066;">Session Details</strong><br><br>

                                        • <strong>Date:</strong> Monday, 20th October 2025<br>
                                        • <strong>Time:</strong> 6pm - 7pm<br>
                                        • <strong>Location:</strong> CBG 1.07<br><br>

                                        Please make sure you have completed the pre-reading materials shared in the WhatsApp group. Come prepared with questions.<br><br>

                                        See you there,<br>
                                        Song Yi & Andriy<br>
                                        <em>Co-President, MBP Capital</em>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
```

### Step 2: Add the config.json entry

Add this under `"templates"` in `config.json`:

```json
"bootcamp_reminder": {
  "subject": "Reminder: MBP Bootcamp Session Tomorrow",
  "template_file": "templates/bootcamp_reminder.html",
  "csv_file": "data/acceptance.csv",
  "csv_loader": "names",
  "description": "Weekly bootcamp session reminder for accepted trainees"
}
```

### Step 3: Ensure the CSV exists

The campaign reuses `data/acceptance.csv` (the same list of accepted bootcamp members). No new CSV needed.

### Step 4: Test it

```bash
python send.py --template bootcamp_reminder --test
```

This sends a single test email to the configured sender address so you can verify formatting.

### Step 5: Send for real

```bash
python send.py --template bootcamp_reminder --provider zoho
```

---

## 9. Common Patterns

### Sending to a specific list

```bash
# Uses the csv_file defined in config.json for that template
python send.py --template bootcamp_reminder --provider zoho
```

### Sending to UG1 members

Point `csv_file` to `data/UG1_members_clean.csv` in the config entry, or use the CLI override if supported:

```bash
python send.py --template welcome --csv data/UG1_members_clean.csv --provider zoho
```

### Using CC/BCC

Add to the template's config.json entry:

```json
"bootcamp_reminder": {
  "subject": "Reminder: MBP Bootcamp Session Tomorrow",
  "template_file": "templates/bootcamp_reminder.html",
  "csv_file": "data/acceptance.csv",
  "csv_loader": "names",
  "description": "Weekly bootcamp session reminder",
  "cc": ["vp@mbpcapital.org"],
  "bcc": ["records@mbpcapital.org"]
}
```

### Custom subject override via CLI

```bash
python send.py --template bootcamp_reminder --subject "URGENT: Bootcamp Cancelled" --provider zoho
```

---

## 10. Important Notes

- **DO NOT edit any Python files in `core/`** — the system is entirely config-driven. New campaigns require only an HTML template and a config.json entry.
- **Always test with `--test`** before sending to real recipients. The test flag sends one email to the sender address only.
- **CSV files in `data/` are gitignored** — they contain personal data. Coordinate data sharing separately (e.g., shared drive).
- **Templates use Python's `string.Template`** syntax: `$variable` or `${variable}`. This is NOT Jinja2 `{{ variable }}` or f-string `{variable}`. If you need a literal dollar sign in the email, escape it as `$$`.
- **All styles must be inline** — email clients strip `<style>` blocks. Never use CSS classes.
- **Use tables for layout** — email clients do not support flexbox, grid, or modern CSS layout.
- **Image references use `cid:`** — never use external URLs; they get blocked by most email clients.
- **Batch settings** in config.json (`batch_size: 75`, `batch_delay_minutes: 0.75`) handle rate limiting automatically. Do not send large lists without these settings.

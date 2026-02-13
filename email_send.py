import requests
import json
import re
import time
import logging
import os
import csv
import base64
import mimetypes
import argparse
import pytz
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from dotenv import load_dotenv
from string import Template
import email.mime.text
import email.mime.multipart
import email.mime.image

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Configuration class for email provider settings"""
    client_id: str
    client_secret: str
    sender_email: str
    refresh_token: str = ""  # Optional for Gmail
    sender_name: str = "Your Name"
    provider: str = "zoho"  # 'zoho' or 'gmail'

class ConfigManager:
    """Manages configuration loading from JSON file with environment variable support"""
    
    @staticmethod
    def load_config(config_file: str = "config.json") -> Dict:
        """Load configuration from JSON file"""
        # Load environment variables
        load_dotenv()
        
        config_path = os.path.join(os.path.dirname(__file__), config_file)
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file '{config_file}' not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
    
    @staticmethod
    def create_email_config(config_data: Dict, provider: str = "zoho") -> EmailConfig:
        """Create EmailConfig from configuration data with environment variable support"""
        if provider not in ["zoho", "gmail"]:
            raise ValueError(f"Unsupported provider: {provider}")
        
        config_key = f"{provider}_config"
        provider_config = config_data.get(config_key, {})
        
        if not provider_config:
            raise ValueError(f"No configuration found for provider: {provider}")
        
        prefix = provider.upper()
        client_id = ConfigManager._get_env_or_config(provider_config.get("client_id"), f"{prefix}_CLIENT_ID")
        client_secret = ConfigManager._get_env_or_config(provider_config.get("client_secret"), f"{prefix}_CLIENT_SECRET")
        refresh_token = ConfigManager._get_env_or_config(provider_config.get("refresh_token"), f"{prefix}_REFRESH_TOKEN", "")
        sender_email = ConfigManager._get_env_or_config(provider_config.get("sender_email"), f"{prefix}_SENDER_EMAIL")
        sender_name = ConfigManager._get_env_or_config(provider_config.get("sender_name"), f"{prefix}_SENDER_NAME", "Your Name")
        
        logger.info(f"Config loaded - Provider: {provider.upper()}, Email: {sender_email}")
        logger.debug(f"Refresh token available: {'Yes' if refresh_token else 'No'}")
        
        return EmailConfig(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            sender_email=sender_email,
            sender_name=sender_name,
            provider=provider
        )
    
    @staticmethod
    def _get_env_or_config(config_value: str, env_var: str, default: str = "") -> str:
        """Get value from environment variable, config, or default"""
        # If config value starts with ENV:, get from environment
        if isinstance(config_value, str) and config_value.startswith("ENV:"):
            env_key = config_value.replace("ENV:", "")
            return os.getenv(env_key, default)
        
        # Try environment variable first, then config value, then default
        return os.getenv(env_var) or config_value or default

class FileLoader:
    """Handles loading and validating email addresses from various sources"""
    
    @staticmethod
    def load_emails(source: str | List[str], email_column: int = 0) -> List[str]:
        """Universal email loader - handles files, lists, or individual emails"""
        if isinstance(source, list):
            return FileLoader._validate_emails(source)
        
        file_path = Path(source)
        if not file_path.exists():
            logger.error(f"File not found: {source}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if source.endswith('.csv'):
                    return FileLoader._load_csv(f, email_column)
                else:
                    return FileLoader._load_txt(f)
        except Exception as e:
            logger.error(f"Error reading file {source}: {e}")
            return []
    
    @staticmethod
    def _load_csv(file_handle, email_column: int) -> List[str]:
        emails = []
        reader = csv.reader(file_handle)
        for row_num, row in enumerate(reader, 1):
            if row and len(row) > email_column and '@' in row[email_column]:
                emails.append(row[email_column].strip())
        logger.info(f"Loaded {len(emails)} emails from CSV")
        return emails
    
    @staticmethod
    def load_csv_with_names(file_path: str, name_column: int = 0, email_column: int = 1) -> List[str]:
        """Load CSV file with names and emails, returning entries in format 'Name email@domain.com'"""
        entries = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if row and len(row) > max(name_column, email_column):
                        name = row[name_column].strip() if row[name_column] else ""
                        email = row[email_column].strip() if row[email_column] else ""
                        
                        if name and email and '@' in email:
                            # Replace comma with dot in name (e.g., "Zong, WS" -> "Zong. WS")
                            formatted_name = name.replace(", ", ". ")
                            # Format as "FirstName LastName email@domain.com"
                            entries.append(f"{formatted_name} {email}")
            
            logger.info(f"Loaded {len(entries)} name-email pairs from CSV")
            return entries
        except Exception as e:
            logger.error(f"Error loading CSV with names from {file_path}: {e}")
            return []
    
    @staticmethod
    def _load_txt(file_handle) -> List[str]:
        entries = []
        for line in file_handle:
            line = line.strip()
            if '@' in line:
                # Handle new format: LastName,FirstInitial (ug) FirstInitial.LastName@lse.ac.uk;
                # Split by semicolon and process each entry
                for entry in line.split(';'):
                    entry = entry.strip()
                    if '@' in entry:
                        entries.append(entry)
        logger.info(f"Loaded {len(entries)} entries from text file")
        return entries
    
    @staticmethod
    def _validate_emails(email_list: List[str]) -> List[str]:
        return [email.strip() for email in email_list if '@' in email.strip()]
    
@dataclass
class Student:
    """Student data class"""
    email: str
    name: str
    first_name: str
    last_name: str

class ZohoAuthManager:
    """Manages Zoho OAuth authentication"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.access_token = None
        self.token_expires_at = None
    
    def get_access_token(self) -> str:
        """Get valid access token, refresh if needed"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        return self._refresh_access_token()
    
    def _refresh_access_token(self) -> str:
        """Refresh access token using refresh token"""
        token_url = "https://accounts.zoho.eu/oauth/v2/token"
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'refresh_token': self.config.refresh_token
        }
        
        try:
            logger.debug(f"Requesting new access token from: {token_url}")
            logger.debug(f"Using client_id: {self.config.client_id[:10]}...")
            
            response = requests.post(token_url, data=data)
            logger.debug(f"Token response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Token request failed: HTTP {response.status_code}")
                logger.error(f"Response body: {response.text}")
                response.raise_for_status()
            
            token_data = response.json()
            logger.debug(f"Token response keys: {list(token_data.keys())}")
            
            if 'access_token' not in token_data:
                logger.error(f"No access_token in response: {token_data}")
                raise ValueError(f"Invalid token response: {token_data}")
            
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("Access token refreshed successfully")
            return self.access_token
            
        except requests.RequestException as e:
            logger.error(f"Network error refreshing access token: {type(e).__name__}: {str(e)}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Token parsing error: {type(e).__name__}: {str(e)}")
            raise

class EmailParser:
    """Parses email addresses to extract names"""
    
    @staticmethod
    def parse_student_entry(entry: str) -> Student:
        """Parse student entry in various formats"""
        entry = entry.strip()
        
        # Check if this is the CSV format with name and email: "FirstName LastName email@domain.com"
        parts = entry.split()
        if len(parts) >= 2 and '@' in parts[-1]:
            # Extract email (last part)
            email = parts[-1]
            # Extract name (all parts except the last one)
            name_parts = parts[:-1]
            full_name = ' '.join(name_parts)
            
            return Student(
                email=email.lower(),
                name=full_name,
                first_name=full_name,  # Use full name for both first_name and name
                last_name=""            # Leave last_name empty
            )
        
        # Check if this is the new format with name information: "LastName,FirstInitial (ug) FirstInitial.LastName@lse.ac.uk"
        if ' (ug) ' in entry:
            try:
                # Split by ' (ug) ' to separate name part and email part
                name_part, email_part = entry.split(' (ug) ', 1)
                
                # Extract email (everything after the space)
                email = email_part.strip()
                
                # Parse name part: "LastName,FirstInitial"
                if ',' in name_part:
                    last_name, first_initial = name_part.split(',', 1)
                    last_name = last_name.strip()
                    first_initial = first_initial.strip()
                    
                    # Create full name
                    full_name = f"{first_initial} {last_name}"
                    
                    return Student(
                        email=email.lower(),
                        name=full_name,
                        first_name=first_initial,
                        last_name=last_name
                    )
            except Exception as e:
                logger.debug(f"Failed to parse new format for '{entry}': {e}")
        
        # If no format matches, return with just the email
        return Student(
            email=entry.lower(),
            name="",
            first_name="",
            last_name=""
        )
    


class EmailTemplateEngine:
    """Handles email template creation and personalization"""
    
    def __init__(self, template_subject: str, template_body: str):
        self.template_subject = template_subject
        self.template_body = template_body
    
    def create_personalized_email(self, student: Student) -> Dict[str, str]:
        """Create personalized email for a student"""
        try:
            # Replace placeholders in subject and body using Template to avoid CSS brace conflicts
            subject_template = Template(self.template_subject)
            subject = subject_template.safe_substitute(
                name=student.name,
                first_name=student.first_name,
                last_name=student.last_name,
                email=student.email
            )
            
            body_template = Template(self.template_body)
            body = body_template.safe_substitute(
                name=student.name,
                first_name=student.first_name,
                last_name=student.last_name,
                email=student.email
            )
            
            logger.debug(f"Email personalized for {student.email}: subject={subject[:50]}...")
            return {
                'subject': subject,
                'body': body
            }
        except Exception as e:
            logger.error(f"Template personalization failed for {student.email}: {type(e).__name__}: {str(e)}")
            logger.error(f"Template body preview: {self.template_body[:200]}...")
            raise
    
    @staticmethod
    def load_template_from_file(template_path: str) -> str:
        """Load HTML template from file with fallback"""
        template_file = os.path.join(os.path.dirname(__file__), template_path)
        
        try:
            logger.info(f"Loading template from: {template_file}")
            with open(template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
                logger.info(f"Template loaded successfully, length: {len(template_content)} chars")
                return template_content
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {type(e).__name__}: {str(e)}")
            logger.warning("Using fallback template")
            return EmailTemplateEngine._get_fallback_template()
    
    @staticmethod
    def _get_fallback_template() -> str:
        """Simple fallback template if file loading fails"""
        return """<html><body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #333;">Welcome {first_name}!</h2>
            <p>Dear {name}, welcome to our program!</p>
            <p>Contact: {email}</p>
            <p>Best regards,<br>The Team</p>
        </div></body></html>"""

class ZohoEmailSender:
    """Sends emails using Zoho Mail API"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.auth_manager = ZohoAuthManager(config)
        self.api_base_url = "https://mail.zoho.eu/api"
        self.account_id = None
    
    def send_email_with_embedded_images(self, to_email: str, subject: str, body: str, 
                                      logo_path: str, signature_path: str, qrcode_path: str = None) -> bool:
        """Send email with base64 embedded images"""
        try:
            logger.debug(f"Preparing to send email with embedded images to {to_email}")
            access_token = self.auth_manager.get_access_token()
            
            # Read and encode images to base64
            logo_file_path = Path(logo_path)
            signature_file_path = Path(signature_path)
            
            if not logo_file_path.exists():
                logger.error(f"Logo file not found: {logo_path}")
                return False
            if not signature_file_path.exists():
                logger.error(f"Signature file not found: {signature_path}")
                return False
            
            # Convert images to base64
            with open(logo_file_path, 'rb') as logo_file:
                logo_b64 = base64.b64encode(logo_file.read()).decode()
            
            with open(signature_file_path, 'rb') as sig_file:
                signature_b64 = base64.b64encode(sig_file.read()).decode()
            
            # Replace cid references with base64 data URLs
            modified_body = body.replace(
                'src="cid:logo"', 
                f'src="data:image/png;base64,{logo_b64}"'
            ).replace(
                'src="cid:signature"', 
                f'src="data:image/png;base64,{signature_b64}"'
            )
            
            # Handle QR code if provided
            if qrcode_path:
                qrcode_file_path = Path(qrcode_path)
                if qrcode_file_path.exists():
                    with open(qrcode_file_path, 'rb') as qr_file:
                        qrcode_b64 = base64.b64encode(qr_file.read()).decode()
                    modified_body = modified_body.replace(
                        'src="cid:qrcode"', 
                        f'src="data:image/png;base64,{qrcode_b64}"'
                    )
                    logger.debug(f"QR code embedded for {to_email}")
                else:
                    logger.warning(f"QR code file not found: {qrcode_path}")
            
            # Send regular email with embedded images
            return self.send_email(to_email, subject, modified_body, is_html=True)
                
        except Exception as e:
            logger.error(f"Error sending email with embedded images to {to_email}: {type(e).__name__}: {str(e)}")
            return False

    def send_email_with_inline_image(self, to_email: str, subject: str, body: str, image_path: str) -> bool:
        """Send email with inline image attachment"""
        try:
            logger.debug(f"Preparing to send email with inline image to {to_email}")
            access_token = self.auth_manager.get_access_token()
            
            headers = {
                'Authorization': f'Zoho-oauthtoken {access_token}'
            }
            
            # Read and encode the image
            image_file_path = Path(image_path)
            if not image_file_path.exists():
                logger.error(f"Image file not found: {image_path}")
                return False
                
            with open(image_file_path, 'rb') as img_file:
                image_data = img_file.read()
                image_b64 = base64.b64encode(image_data).decode()
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(str(image_file_path))
            if not mime_type:
                mime_type = 'image/png'
            
            # Prepare multipart form data
            files = {
                'fromAddress': (None, self.config.sender_email),
                'toAddress': (None, to_email),
                'subject': (None, subject),
                'content': (None, body),
                'mailFormat': (None, 'html'),
                'attachments': (image_file_path.name, image_data, mime_type),
                'isInline': (None, 'true')
            }
            
            # Get account ID
            account_id = self.get_account_id()
            logger.debug(f"Using account ID: {account_id}")
            
            response = requests.post(
                f"{self.api_base_url}/accounts/{account_id}/messages",
                headers=headers,
                files=files,
                timeout=30
            )
            
            logger.debug(f"API response for {to_email}: Status {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"Email with inline image sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email with inline image to {to_email}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email with inline image to {to_email}: {type(e).__name__}: {str(e)}")
            return False

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = True) -> bool:
        """Send individual email"""
        try:
            logger.debug(f"Preparing to send email to {to_email}")
            access_token = self.auth_manager.get_access_token()
            logger.debug(f"Access token obtained for {to_email}")
            
            headers = {
                'Authorization': f'Zoho-oauthtoken {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Construct email payload
            email_data = {
                'fromAddress': self.config.sender_email,
                'toAddress': to_email,
                'subject': subject,
                'content': body,
                'mailFormat': 'html' if is_html else 'plaintext'
            }
            
            logger.debug(f"Email payload prepared for {to_email}, subject: {subject[:50]}...")
            
            # Get account ID for API call
            account_id = self.get_account_id()
            logger.debug(f"Using account ID: {account_id}")
            
            response = requests.post(
                f"{self.api_base_url}/accounts/{account_id}/messages",
                headers=headers,
                json=email_data,
                timeout=30
            )
            
            logger.debug(f"API response for {to_email}: Status {response.status_code}")
            
            if response.status_code == 200:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Network error sending email to {to_email}: {type(e).__name__}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {type(e).__name__}: {str(e)}")
            return False
    
    def get_account_id(self) -> str:
        """Get the Account ID for the authenticated user"""
        if self.account_id:
            return self.account_id
            
        try:
            access_token = self.auth_manager.get_access_token()
            headers = {
                'Authorization': f'Zoho-oauthtoken {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get user profile to extract account ID
            response = requests.get(
                f"{self.api_base_url}/accounts",
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"Account details response: Status {response.status_code}")
            
            if response.status_code == 200:
                accounts_data = response.json()
                logger.debug(f"Accounts data: {accounts_data}")
                
                # Extract the first account ID
                if 'data' in accounts_data and len(accounts_data['data']) > 0:
                    self.account_id = accounts_data['data'][0]['accountId']
                    logger.info(f"Account ID retrieved: {self.account_id}")
                    return self.account_id
                else:
                    raise ValueError("No accounts found in response")
            else:
                logger.error(f"Failed to get account ID: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                raise Exception(f"Account ID request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting account ID: {type(e).__name__}: {str(e)}")
            raise
    
    def send_bulk_emails(self, students: List[Student], template_engine: EmailTemplateEngine, 
                        batch_size: int = 50, batch_delay_minutes: int = 1) -> Dict[str, int]:
        """Send emails to multiple students in batches"""
        results = {'sent': 0, 'failed': 0}
        total_students = len(students)
        
        # Process students in batches
        for batch_start in range(0, total_students, batch_size):
            batch_end = min(batch_start + batch_size, total_students)
            current_batch = students[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_students + batch_size - 1) // batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches} "
                        f"(emails {batch_start + 1}-{batch_end} of {total_students})")
            
            # Send emails in current batch
            for student in current_batch:
                if self._send_single_email(student, template_engine, results):
                    time.sleep(1)  # Rate limiting between individual emails
            
            # Wait before next batch (except for the last batch)
            if batch_end < total_students:
                logging.info(f"Batch {batch_num} completed. Waiting {batch_delay_minutes} minute(s) before next batch...")
                time.sleep(batch_delay_minutes * 60)  # Convert minutes to seconds
        
        logging.info(f"All batches completed. Total sent: {results['sent']}, failed: {results['failed']}")
        return results
    
    def _send_single_email(self, student: Student, template_engine: EmailTemplateEngine, 
                          results: Dict) -> bool:
        """Send email (single attempt, no retry)"""
        try:
            logger.debug(f"Sending email to {student.email}")
            email_content = template_engine.create_personalized_email(student)
            logger.debug(f"Template generated successfully for {student.email}")
            
            # Use the logo, signature, and QR code paths
            logo_path = Path("image/MBP.png")
            signature_path = Path("image/signature.png")
            qrcode_path = Path("image/qrcode.png")
            
            # Check if all images exist for embedded image sending
            if logo_path.exists() and signature_path.exists():
                if self.send_email_with_embedded_images(student.email, email_content['subject'], 
                                                      email_content['body'], str(logo_path), 
                                                      str(signature_path), str(qrcode_path)):
                    results['sent'] += 1
                    logger.info(f"✅ Email sent successfully to {student.email} with all images")
                    return True
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to send email with images to {student.email}")
                    return False
            elif logo_path.exists():
                # Fallback to single image if only logo exists
                if self.send_email_with_inline_image(student.email, email_content['subject'], 
                                                   email_content['body'], str(logo_path)):
                    results['sent'] += 1
                    logger.info(f"✅ Email sent successfully to {student.email} with logo only")
                    return True
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to send email to {student.email}")
                    return False
            else:
                # Fallback to regular email if no images found
                if self.send_email(student.email, email_content['subject'], email_content['body']):
                    results['sent'] += 1
                    logger.info(f"✅ Email sent successfully to {student.email} (no images)")
                    return True
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to send email to {student.email}")
                    return False
                
        except Exception as e:
            results['failed'] += 1
            logger.error(f"❌ Error sending email to {student.email}: {type(e).__name__}: {str(e)}")
            return False

import smtplib
import os
import urllib.parse
import webbrowser

class GmailOAuth2Manager:
    """Manages Gmail OAuth 2.0 authentication flow"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.token_file = "gmail_token.json"
        self._access_token = None
        self._refresh_token = None
    
    def get_access_token(self) -> str:
        """Get access token using OAuth 2.0 flow"""
        try:
            logger.info("🔐 Attempting to get OAuth 2.0 access token")
            
            # Try to load existing token
            if self._load_existing_token():
                if self._access_token:
                    logger.info(f"🔑 Using cached access token (expires: {self._access_token[:20]}...)")
                    return self._access_token
            
            # Try to refresh token if we have refresh token
            if self._refresh_token:
                logger.info("🔄 Attempting to refresh access token")
                if self._refresh_access_token():
                    logger.info("✅ Access token refreshed successfully")
                    return self._access_token
            
            # Start new OAuth flow
            logger.info("🚀 No valid token found - starting OAuth 2.0 authorization flow")
            logger.warning("⚠️ This will open a browser window for authentication")
            return self._start_oauth_flow()
            
        except Exception as e:
            logger.error(f"❌ OAuth 2.0 error: {e}")
            raise
    
    def _load_existing_token(self) -> bool:
        """Load existing token from file"""
        try:
            if os.path.exists(self.token_file):
                import json
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    self._access_token = token_data.get('access_token')
                    self._refresh_token = token_data.get('refresh_token')
                    logger.debug("📂 Loaded existing token from file")
                    return True
        except Exception as e:
            logger.debug(f"⚠️ Could not load existing token: {e}")
        return False
    
    def _save_token(self, token_data: dict):
        """Save token to file"""
        try:
            import json
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f)
            logger.debug("💾 Token saved to file")
        except Exception as e:
            logger.error(f"❌ Could not save token: {e}")
    
    def _refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        try:
            url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            
            # Update refresh token if provided
            if "refresh_token" in token_data:
                self._refresh_token = token_data["refresh_token"]
            
            # Save updated token
            self._save_token({
                "access_token": self._access_token,
                "refresh_token": self._refresh_token
            })
            
            logger.info("✅ Access token refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token refresh failed: {e}")
            return False
    
    def _start_oauth_flow(self) -> str:
        """Start OAuth 2.0 authorization flow"""
        try:
            # Step 1: Generate authorization URL
            auth_url = self._get_authorization_url()
            
            logger.info("🌐 Opening browser for OAuth authorization...")
            logger.info(f"📋 If browser doesn't open, visit: {auth_url}")
            
            # Open browser
            webbrowser.open(auth_url)
            
            # Step 2: Get authorization code from user
            auth_code = input("\n🔐 Paste the authorization code here: ").strip()
            
            # Step 3: Exchange code for tokens
            return self._exchange_code_for_tokens(auth_code)
            
        except Exception as e:
            logger.error(f"❌ OAuth flow failed: {e}")
            raise
    
    def _get_authorization_url(self) -> str:
        """Generate OAuth 2.0 authorization URL"""
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",  # For installed apps
            "scope": "https://www.googleapis.com/auth/gmail.send",
            "response_type": "code",
            "access_type": "offline",  # To get refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }
        
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def _exchange_code_for_tokens(self, auth_code: str) -> str:
        """Exchange authorization code for access and refresh tokens"""
        try:
            url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            self._refresh_token = token_data.get("refresh_token")
            
            # Save tokens
            self._save_token({
                "access_token": self._access_token,
                "refresh_token": self._refresh_token
            })
            
            logger.info("✅ OAuth 2.0 authorization completed successfully")
            return self._access_token
            
        except Exception as e:
            logger.error(f"❌ Token exchange failed: {e}")
            raise

class GmailEmailSender:
    """Sends emails using Gmail SMTP with OAuth 2.0"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.oauth_manager = GmailOAuth2Manager(config)
    
    def send_email_with_embedded_images(self, to_email: str, subject: str, body: str, 
                                      logo_path: str, signature_path: str, qrcode_path: str = None) -> bool:
        """Send email with embedded images using Gmail SMTP"""
        try:
            logger.info(f"🔄 Starting Gmail SMTP send to {to_email}")
            
            # Create message
            logger.debug("📝 Creating MIME message structure")
            message = email.mime.multipart.MIMEMultipart('related')
            message['to'] = to_email
            message['from'] = self.config.sender_email
            message['subject'] = subject
            logger.debug(f"📧 Message headers set: From={self.config.sender_email}, To={to_email}")
            
            # Add HTML body
            logger.debug("🎨 Adding HTML content to message")
            msg_alternative = email.mime.multipart.MIMEMultipart('alternative')
            msg_text = email.mime.text.MIMEText(body, 'html')
            msg_alternative.attach(msg_text)
            message.attach(msg_alternative)
            
            # Embed images
            logger.debug("🖼️ Embedding images in message")
            self._embed_image(message, logo_path, 'logo')
            self._embed_image(message, signature_path, 'signature')
            if qrcode_path:
                self._embed_image(message, qrcode_path, 'qrcode')
            
            # Get OAuth 2.0 access token
            logger.info("🔐 Getting OAuth 2.0 access token")
            access_token = self.oauth_manager.get_access_token()
            
            # Send email using Gmail API instead of SMTP
            logger.info("� Sending email via Gmail API")
            return self._send_via_gmail_api(message, access_token, to_email)
                
            logger.info(f"✅ Gmail email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"🔐 Gmail SMTP Authentication failed for {to_email}: {e}")
            logger.error("💡 Check GMAIL_APP_PASSWORD is correct and 2FA is enabled")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"📧 Gmail SMTP error to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected Gmail error to {to_email}: {type(e).__name__}: {e}")
            logger.debug("🔍 Full error details:", exc_info=True)
            return False
    
    def send_bulk_emails(self, students: List[Student], template_engine: EmailTemplateEngine, 
                        batch_size: int = 50, batch_delay_minutes: int = 1) -> Dict[str, int]:
        """Send emails to multiple students in batches"""
        results = {'sent': 0, 'failed': 0}
        total_students = len(students)
        
        # Process students in batches
        for batch_start in range(0, total_students, batch_size):
            batch_end = min(batch_start + batch_size, total_students)
            current_batch = students[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_students + batch_size - 1) // batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches} "
                        f"(emails {batch_start + 1}-{batch_end} of {total_students})")
            
            # Send emails in current batch
            for student in current_batch:
                if self._send_single_email(student, template_engine, results):
                    time.sleep(1)  # Rate limiting between individual emails
            
            # Wait before next batch (except for the last batch)
            if batch_end < total_students:
                logging.info(f"Batch {batch_num} completed. Waiting {batch_delay_minutes} minute(s) before next batch...")
                time.sleep(batch_delay_minutes * 60)  # Convert minutes to seconds
        
        logging.info(f"All batches completed. Total sent: {results['sent']}, failed: {results['failed']}")
        return results
    
    def _send_single_email(self, student: Student, template_engine: EmailTemplateEngine, 
                          results: Dict) -> bool:
        """Send email (single attempt, no retry)"""
        try:
            logger.debug(f"Sending Gmail email to {student.email}")
            email_content = template_engine.create_personalized_email(student)
            logger.debug(f"Template generated successfully for {student.email}")
            
            # Use the logo, signature, and QR code paths
            logo_path = Path("image/MBP.png")
            signature_path = Path("image/signature.png")
            qrcode_path = Path("image/qrcode.png")
            
            # Check if all images exist for embedded image sending
            if logo_path.exists() and signature_path.exists():
                if self.send_email_with_embedded_images(student.email, email_content['subject'], 
                                                      email_content['body'], str(logo_path), 
                                                      str(signature_path), str(qrcode_path)):
                    results['sent'] += 1
                    logger.info(f"✅ Gmail email sent successfully to {student.email} with all images")
                    return True
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to send Gmail email with images to {student.email}")
                    return False
            else:
                # Fallback to regular email if images not found
                if self.send_email(student.email, email_content['subject'], email_content['body']):
                    results['sent'] += 1
                    logger.info(f"✅ Gmail email sent successfully to {student.email} (no images)")
                    return True
                else:
                    results['failed'] += 1
                    logger.error(f"❌ Failed to send Gmail email to {student.email}")
                    return False
                
        except Exception as e:
            results['failed'] += 1
            logger.error(f"❌ Error sending Gmail email to {student.email}: {type(e).__name__}: {str(e)}")
            return False
    
    def send_email_with_inline_image(self, to_email: str, subject: str, body: str, image_path: str) -> bool:
        """Send email with single inline image using Gmail SMTP"""
        return self.send_email_with_embedded_images(to_email, subject, body, image_path, image_path)
    
    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = True) -> bool:
        """Send simple email using Gmail SMTP with OAuth 2.0"""
        try:
            logger.info(f"🔄 Starting simple Gmail send to {to_email}")
            
            # Get OAuth 2.0 access token
            access_token = self.oauth_manager.get_access_token()
            
            # Create message
            if is_html:
                message = email.mime.text.MIMEText(body, 'html')
            else:
                message = email.mime.text.MIMEText(body, 'plain')
            
            message['Subject'] = subject
            message['From'] = self.config.sender_email
            message['To'] = to_email
            
            # Send email using Gmail API (better OAuth 2.0 support than SMTP)
            logger.debug("� Using Gmail API for simple email")
            return self._send_simple_via_gmail_api(message, access_token, to_email)
            
        except Exception as e:
            logger.error(f"❌ Simple Gmail SMTP error to {to_email}: {e}")
            return False
    
    def _send_via_gmail_api(self, message, access_token: str, to_email: str) -> bool:
        """Send email via Gmail API"""
        try:
            import base64
            
            # Convert message to Gmail API format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Gmail API send request
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {"raw": raw_message}
            
            logger.debug("🌐 Sending POST request to Gmail API")
            logger.debug(f"📤 Request URL: {url}")
            logger.debug(f"📋 Request headers: Authorization: Bearer {access_token[:20]}...")
            
            response = requests.post(url, headers=headers, json=data)
            
            logger.debug(f"📨 Gmail API Response Status: {response.status_code}")
            logger.debug(f"📝 Gmail API Response: {response.text[:200]}...")
            
            response.raise_for_status()
            
            # Parse response to get message ID
            response_data = response.json()
            message_id = response_data.get('id', 'unknown')
            
            logger.info(f"✅ Gmail API email ACTUALLY sent to {to_email} (Message ID: {message_id})")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"🌐 Gmail API HTTP error for {to_email}: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"📝 Response: {e.response.text}")
            
            # Handle 401 Unauthorized - token expired
            if e.response.status_code == 401:
                logger.warning("🔄 Access token expired, attempting to refresh...")
                try:
                    # Try to refresh the token
                    if self.oauth_manager._refresh_access_token():
                        logger.info("✅ Token refreshed successfully, retrying email send...")
                        # Get new access token and retry the send
                        new_access_token = self.oauth_manager.get_access_token()
                        
                        # Retry the API call with new token
                        headers["Authorization"] = f"Bearer {new_access_token}"
                        retry_response = requests.post(url, headers=headers, json=data)
                        retry_response.raise_for_status()
                        
                        response_data = retry_response.json()
                        message_id = response_data.get('id', 'unknown')
                        logger.info(f"✅ Gmail API email sent after token refresh to {to_email} (Message ID: {message_id})")
                        return True
                    else:
                        logger.error("❌ Failed to refresh access token")
                        return False
                except Exception as refresh_error:
                    logger.error(f"❌ Error during token refresh: {refresh_error}")
                    return False
            
            # Handle 429 Rate Limit Exceeded
            elif e.response.status_code == 429:
                import re
                import time
                
                logger.warning(f"⏰ Rate limit exceeded for {to_email}")
                
                # Try to parse retry-after time from response
                try:
                    response_text = e.response.text
                    # Look for "Retry after YYYY-MM-DDTHH:MM:SS.sssZ" pattern
                    retry_match = re.search(r'Retry after (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)', response_text)
                    
                    if retry_match:
                        retry_time_str = retry_match.group(1)
                        from datetime import datetime
                        import pytz
                        
                        # Parse the retry time (it's in UTC)
                        retry_time = datetime.strptime(retry_time_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)
                        current_time = datetime.now(pytz.UTC)
                        
                        # Calculate wait time in seconds
                        wait_seconds = (retry_time - current_time).total_seconds()
                        
                        if wait_seconds > 0 and wait_seconds < 3600:  # Don't wait more than 1 hour
                            logger.warning(f"⏳ Gmail API rate limit hit. Waiting {wait_seconds:.0f} seconds until {retry_time_str}")
                            time.sleep(wait_seconds + 5)  # Add 5 seconds buffer
                            
                            # Retry the API call
                            logger.info(f"🔄 Retrying email send to {to_email} after rate limit wait...")
                            retry_response = requests.post(url, headers=headers, json=data)
                            retry_response.raise_for_status()
                            
                            response_data = retry_response.json()
                            message_id = response_data.get('id', 'unknown')
                            logger.info(f"✅ Gmail API email sent after rate limit wait to {to_email} (Message ID: {message_id})")
                            return True
                        else:
                            logger.error(f"❌ Rate limit wait time too long ({wait_seconds:.0f}s) or negative - skipping email")
                            return False
                    else:
                        logger.error("❌ Could not parse retry-after time from rate limit response")
                        return False
                        
                except Exception as rate_limit_error:
                    logger.error(f"❌ Error handling rate limit: {rate_limit_error}")
                    return False
            
            return False
        except Exception as e:
            logger.error(f"❌ Gmail API error for {to_email}: {e}")
            return False
    
    def _send_simple_via_gmail_api(self, message, access_token: str, to_email: str) -> bool:
        """Send simple email via Gmail API"""
        try:
            import base64
            
            # Convert message to Gmail API format
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Gmail API send request
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            data = {"raw": raw_message}
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            logger.info(f"✅ Simple Gmail API email sent successfully to {to_email}")
            return True
            
        except requests.exceptions.HTTPError as e:
            # Handle 401 Unauthorized - token expired
            if e.response.status_code == 401:
                logger.warning("🔄 Access token expired in simple send, attempting to refresh...")
                try:
                    # Try to refresh the token
                    if self.oauth_manager._refresh_access_token():
                        logger.info("✅ Token refreshed successfully, retrying simple email send...")
                        # Get new access token and retry
                        new_access_token = self.oauth_manager.get_access_token()
                        headers["Authorization"] = f"Bearer {new_access_token}"
                        
                        retry_response = requests.post(url, headers=headers, json=data)
                        retry_response.raise_for_status()
                        
                        logger.info(f"✅ Simple Gmail API email sent after token refresh to {to_email}")
                        return True
                    else:
                        logger.error("❌ Failed to refresh access token in simple send")
                        return False
                except Exception as refresh_error:
                    logger.error(f"❌ Error during token refresh in simple send: {refresh_error}")
                    return False
            
            logger.error(f"❌ Simple Gmail API HTTP error for {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Simple Gmail API error for {to_email}: {e}")
            return False
    
    def _embed_image(self, message: email.mime.multipart.MIMEMultipart, image_path: str, cid: str):
        """Embed image in email with content ID"""
        if not Path(image_path).exists():
            logger.warning(f"Image not found: {image_path}")
            return
        
        with open(image_path, 'rb') as f:
            img_data = f.read()
            img = email.mime.image.MIMEImage(img_data)
            img.add_header('Content-ID', f'<{cid}>')
            message.attach(img)

class ResultsSaver:
    """Handles saving automation results to files"""
    
    @staticmethod
    def save_results_to_json(results: Dict, filename: str = None) -> str:
        """Save results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"email_results_{timestamp}.json"
        
        # Convert Student objects to dictionaries for JSON serialization
        results_copy = results.copy()
        if 'students' in results_copy:
            results_copy['students'] = [
                {
                    'email': s.email,
                    'name': s.name,
                    'first_name': s.first_name,
                    'last_name': s.last_name
                }
                for s in results['students']
            ]
        
        # Add metadata
        results_copy['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'success_rate': f"{(results['emails_sent'] / results['total_emails'] * 100):.1f}%" if results['total_emails'] > 0 else "0%"
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_copy, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

class EmailAutomationSystem:
    """Main controller for the email automation system"""
    
    def __init__(self, config: EmailConfig, settings: Dict = None):
        self.config = config
        self.settings = settings or {}
        
        # Choose email sender based on provider
        if config.provider == "gmail":
            self.email_sender = GmailEmailSender(config)
        else:
            self.email_sender = ZohoEmailSender(config)
        
        self.results_saver = ResultsSaver()
        logger.info(f"Email system initialized with {config.provider.upper()} provider")
    
    def load_emails_from_file(self, file_path: str) -> List[str]:
        """Load emails from file (auto-detects format)"""
        return FileLoader.load_emails(file_path)
    
    def process_email_list(self, email_list: List[str] = None, file_path: str = None,
                          subject_template: str = None, body_template: str = None, 
                          config_data: Dict = None, save_results: bool = True, template_type: str = 'welcome') -> Dict[str, any]:
        """Process emails from list or file and send personalized messages"""
        
        # Load and validate emails
        if file_path:
            email_list = self.load_emails_from_file(file_path)
        elif email_list:
            email_list = FileLoader.load_emails(email_list)
        else:
            logger.error("No email list or file path provided")
            return {}
        
        if not email_list:
            logger.error("No valid emails found")
            return {}
        
        logger.info(f"Processing {len(email_list)} emails...")
        
        # Set up templates
        subject_template, body_template = self._setup_templates(config_data, subject_template, body_template, template_type)
        
        # Parse emails to extract student information
        students = []
        parsing_errors = []
        
        for entry in email_list:
            try:
                student = EmailParser.parse_student_entry(entry)
                students.append(student)
                logger.info(f"Parsed: {entry} -> {student.name}")
            except Exception as e:
                error_msg = f"Failed to parse entry {entry}: {e}"
                logger.error(error_msg)
                parsing_errors.append(error_msg)
        
        if not students:
            logger.error("No valid student records created from email list")
            return {}
        
        # Create template engine
        template_engine = EmailTemplateEngine(subject_template, body_template)
        
        # Get batch settings from config
        batch_size = self.settings.get('batch_size', 50)
        batch_delay_minutes = self.settings.get('batch_delay_minutes', 1)
        
        logger.info(f"Sending emails in batches of {batch_size} with {batch_delay_minutes} minute(s) delay between batches")
        
        # Send emails in batches
        results = self.email_sender.send_bulk_emails(
            students, 
            template_engine, 
            batch_size=batch_size,
            batch_delay_minutes=batch_delay_minutes
        )
        
        # Compile final results
        final_results = {
            'total_emails': len(email_list),
            'parsed_successfully': len(students),
            'parsing_errors': parsing_errors,
            'emails_sent': results['sent'],
            'emails_failed': results['failed'],
            'emails_retried': results.get('retried', 0),
            'success_rate': f"{(results['sent'] / len(students) * 100):.1f}%" if students else "0%",
            'students': students,
            'settings_used': {
                'batch_size': batch_size,
                'batch_delay_minutes': batch_delay_minutes,
                'retry_enabled': False
            },
            'templates_used': {
                'subject': subject_template,
                'body_preview': body_template[:200] + "..." if len(body_template) > 200 else body_template
            }
        }
        
        # Save results if requested
        if save_results:
            results_file = self.results_saver.save_results_to_json(final_results)
            final_results['results_file'] = results_file
        
        return final_results
    
    def _setup_templates(self, config_data: Dict, subject_template: str, body_template: str, template_type: str = 'welcome') -> tuple:
        """Setup email templates from config or defaults"""
        # Template-specific defaults
        if template_type == 'followup':
            default_subject = 'Take the Leap – MBP Capital Is Where Your Journey Begins'
            default_body = EmailTemplateEngine.load_template_from_file("templates/MBP_freshers_followup.html")
        elif template_type == 'rejection':
            default_subject = 'Your MBP Capital Application Update'
            default_body = EmailTemplateEngine.load_template_from_file("templates/MBP_rejection.html")
        elif template_type == 'membership':
            default_subject = 'Important: MBP Capital Membership Requirement'
            default_body = EmailTemplateEngine.load_template_from_file("templates/MBP_membership.html")
        elif template_type == 'acceptance':
            default_subject = 'Congratulations – Welcome to MBP Capital Bootcamp'
            default_body = EmailTemplateEngine.load_template_from_file("templates/MBP_acceptance.html")
        else:  # welcome template
            default_subject = '🎉 Welcome $first_name - Your Journey Begins!'
            default_body = EmailTemplateEngine.load_template_from_file("templates/MBP_freshers_template.html")
        
        if not config_data or not config_data.get('email_templates'):
            return subject_template or default_subject, body_template or default_body
        
        templates = config_data['email_templates']
        
        # Use template-specific config if available
        if template_type == 'followup':
            subject = subject_template or templates.get('followup_subject', default_subject)
            config_body_key = 'followup_body'
        elif template_type == 'rejection':
            subject = subject_template or templates.get('rejection_subject', default_subject)
            config_body_key = 'rejection_body'
        elif template_type == 'membership':
            subject = subject_template or templates.get('membership_subject', default_subject)
            config_body_key = 'membership_body'
        elif template_type == 'acceptance':
            subject = subject_template or templates.get('acceptance_subject', default_subject)
            config_body_key = 'acceptance_body'
        else:
            subject = subject_template or templates.get('welcome_subject', default_subject)
            config_body_key = 'welcome_body'
        
        if body_template:
            return subject, body_template
        
        config_body = templates.get(config_body_key, '')
        if config_body.startswith('TEMPLATE_FILE:'):
            template_path = config_body.replace('TEMPLATE_FILE:', '')
            body = EmailTemplateEngine.load_template_from_file(template_path)
        else:
            body = config_body or default_body
        
        return subject, body

def main():
    """Email automation system - streamlined entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Email Automation System')
    parser.add_argument('--UG1', action='store_true', 
                       help='Send emails using UG1_members_clean.csv (name in first column, email in second)')
    parser.add_argument('--bootcamp', action='store_true', 
                       help='Send emails using bootcamp_applicants.csv (name in first column, email in second)')
    parser.add_argument('--test', action='store_true',
                       help='Test mode: Parse and display CSV entries without sending emails')
    parser.add_argument('--provider', choices=['zoho', 'gmail'], default='zoho',
                       help='Email provider to use (default: zoho)')
    parser.add_argument('--template', choices=['welcome', 'followup', 'rejection', 'membership', 'acceptance'], default='welcome',
                       help='Email template to use: welcome (MBP_freshers_template.html), followup (MBP_freshers_followup.html), rejection (MBP_rejection.html), membership (MBP_membership.html), or acceptance (MBP_acceptance.html)')
    parser.add_argument('--subject', type=str, help='Custom email subject (overrides template default)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config_data = ConfigManager.load_config()
        email_config = ConfigManager.create_email_config(config_data, args.provider)
        settings = config_data.get('settings', {})
        
        print("🎯 EMAIL AUTOMATION SYSTEM")
        print("="*40)
        logger.info(f"Sender: {email_config.sender_name} <{email_config.sender_email}>")
        template_files = {
            'followup': 'MBP_freshers_followup.html',
            'rejection': 'MBP_rejection.html',
            'membership': 'MBP_membership.html',
            'acceptance': 'MBP_acceptance.html',
            'welcome': 'MBP_freshers_template.html'
        }
        logger.info(f"Template: {args.template} ({template_files.get(args.template, 'MBP_freshers_template.html')})")
        if args.subject:
            logger.info(f"Custom subject: {args.subject}")
        
        # Initialize email automation system
        logger.info("Initializing email automation system...")
        automation = EmailAutomationSystem(email_config, settings)
        
        # Determine which file to process
        # Priority: template-based automatic selection > explicit argument > default
        if args.template == 'rejection':
            # Rejection template automatically uses rejection.csv
            csv_file = "rejection.csv"
            logger.info(f"Using rejection template - automatically loading {csv_file}...")
            email_list = FileLoader.load_csv_with_names(csv_file, name_column=0, email_column=1)
        elif args.template == 'acceptance':
            # Acceptance template automatically uses acceptance.csv
            csv_file = "acceptance.csv"
            logger.info(f"Using acceptance template - automatically loading {csv_file}...")
            email_list = FileLoader.load_csv_with_names(csv_file, name_column=0, email_column=1)
        elif args.UG1:
            # Load emails from UG1_members_clean.csv with names
            csv_file = "UG1_members_clean.csv"
            logger.info(f"Processing email list from {csv_file} (name-email format)...")
            
            # Load CSV with names and emails
            email_list = FileLoader.load_csv_with_names(csv_file, name_column=0, email_column=1)
        elif args.bootcamp:
            # Use bootcamp_applicants.csv file
            csv_file = "bootcamp_applicants.csv"
            logger.info(f"Processing email list from {csv_file}...")
            email_list = FileLoader.load_csv_with_names(csv_file, name_column=0, email_column=1)
        else:
            # Default behavior - load emails from sample_emails.txt file
            logger.info("Processing email list from sample_emails.txt...")
            results = automation.process_email_list(
                file_path="sample_emails.txt", 
                config_data=config_data, 
                template_type=args.template,
                subject_template=args.subject
            )
            print(f"✅ Demo completed: {results['emails_sent']}/{results['total_emails']} processed")
            
            # Show detailed results
            if results.get('parsing_errors'):
                print(f"⚠️  {len(results['parsing_errors'])} parsing errors occurred")
                for error in results['parsing_errors']:
                    print(f"  - {error}")
            
            if results.get('students'):
                print(f"\n👥 Processed Students:")
                for student in results['students']:
                    print(f"  📧 {student.email} → {student.name} ({student.first_name})")
            
            # Usage examples
            print(f"\n📋 Usage Examples:")
            print(f"📧 Rejection emails: python email_send.py --template rejection --provider gmail")
            print(f"📧 Acceptance emails: python email_send.py --template acceptance --provider gmail")
            print(f"📧 Welcome emails: python email_send.py --UG1 --template welcome")
            print(f"📧 Follow-up emails: python email_send.py --UG1 --template followup")
            print(f"📧 Membership reminder: python email_send.py --bootcamp --template membership")
            print(f"🧪 Test mode: python email_send.py --template acceptance --test")
            return
        
        # Common handling for all CSV-based email lists
        if not email_list:
            print(f"❌ No valid entries found in {csv_file}")
            return
        
        # Test mode - just parse and display without sending
        if args.test:
            print(f"🧪 TEST MODE: Parsing {csv_file}")
            print("="*50)
            print(f"📧 Found {len(email_list)} entries")
            print(f"📋 Template: {args.template}")
            print(f"📨 Subject: {args.subject or 'Default subject'}")
            
            # Parse emails to show what will be sent
            for i, entry in enumerate(email_list, 1):
                try:
                    student = EmailParser.parse_student_entry(entry)
                    print(f"{i:3d}. {student.name} <{student.email}>")
                except Exception as e:
                    print(f"{i:3d}. ERROR: {e}")
            
            print(f"\n� Total entries: {len(email_list)}")
            print("🚫 No emails sent in test mode")
            return
        
        # Send emails
        results = automation.process_email_list(
            email_list=email_list, 
            config_data=config_data, 
            template_type=args.template,
            subject_template=args.subject
        )
        print(f"✅ Processing completed: {results['emails_sent']}/{results['total_emails']} emails sent")
        
        # Show errors if any
        if results.get('parsing_errors'):
            print(f"⚠️  {len(results['parsing_errors'])} parsing errors")
        
        # Usage examples
        print(f"\n📋 Quick Reference:")
        print(f"  Rejection:  python email_send.py --template rejection --provider gmail")
        print(f"  Acceptance: python email_send.py --template acceptance --provider gmail")
        print(f"  Bootcamp:   python email_send.py --bootcamp --template membership --provider gmail")
        print(f"  Test mode:  python email_send.py --template acceptance --test")
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        print("   Ensure config.json and CSV files exist in the current directory.")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
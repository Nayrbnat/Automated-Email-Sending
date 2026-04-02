import os
import re
import json
import time
import base64
import mimetypes
import logging
import urllib.parse
import webbrowser
import email.mime.text
import email.mime.multipart
import email.mime.image
import email.mime.base
import email.header
import email.encoders
from pathlib import Path
from typing import List
from datetime import datetime

import requests
import pytz

from core.models import EmailConfig
from core.sender_base import BaseEmailSender

logger = logging.getLogger(__name__)


class GmailOAuth2Manager:

    def __init__(self, config: EmailConfig):
        self.config = config
        self.token_file = "gmail_token.json"
        self._access_token = None
        self._refresh_token = None

    def get_access_token(self) -> str:
        if self._load_existing_token() and self._access_token:
            return self._access_token
        if self._refresh_token and self._refresh_access_token():
            return self._access_token
        return self._start_oauth_flow()

    def _load_existing_token(self) -> bool:
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                self._access_token = data.get('access_token')
                self._refresh_token = data.get('refresh_token')
                return True
        except Exception:
            pass
        return False

    def _save_token(self, data: dict):
        with open(self.token_file, 'w') as f:
            json.dump(data, f)

    def _refresh_access_token(self) -> bool:
        try:
            resp = requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            if "refresh_token" in data:
                self._refresh_token = data["refresh_token"]
            self._save_token({"access_token": self._access_token, "refresh_token": self._refresh_token})
            return True
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False

    def _start_oauth_flow(self) -> str:
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "scope": "https://www.googleapis.com/auth/gmail.send",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        webbrowser.open(url)
        logger.info(f"Auth URL: {url}")
        code = input("\n\U0001f510 Paste authorization code: ").strip()

        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        })
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._save_token({"access_token": self._access_token, "refresh_token": self._refresh_token})
        return self._access_token


class GmailEmailSender(BaseEmailSender):

    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.oauth = GmailOAuth2Manager(config)

    def send_one(self, to_email, subject, body, attachment_path=None, cc=None, bcc=None):
        token = self.oauth.get_access_token()

        if attachment_path:
            msg = self._build_attachment_message(to_email, subject, body, attachment_path, cc=cc, bcc=bcc)
        else:
            msg = email.mime.text.MIMEText(body, 'html', 'utf-8')
            msg['To'] = to_email
            msg['From'] = self.config.sender_email
            msg['Subject'] = email.header.Header(subject, 'utf-8')
            if cc:
                msg['Cc'] = ','.join(cc) if isinstance(cc, list) else cc
            if bcc:
                msg['Bcc'] = ','.join(bcc) if isinstance(bcc, list) else bcc

        return self._send_via_api(msg, token, to_email)

    def _build_attachment_message(self, to_email, subject, body, path, cc=None, bcc=None):
        p = Path(path)
        mime_type = mimetypes.guess_type(str(p))[0] or 'application/octet-stream'

        msg = email.mime.multipart.MIMEMultipart()
        msg['To'] = to_email
        msg['From'] = self.config.sender_email
        msg['Subject'] = email.header.Header(subject, 'utf-8')
        if cc:
            msg['Cc'] = ','.join(cc) if isinstance(cc, list) else cc
        if bcc:
            msg['Bcc'] = ','.join(bcc) if isinstance(bcc, list) else bcc
        msg.attach(email.mime.text.MIMEText(body, 'html', 'utf-8'))

        att = email.mime.base.MIMEBase(*mime_type.split('/'))
        att.set_payload(p.read_bytes())
        email.encoders.encode_base64(att)
        att.add_header('Content-Disposition', f'attachment; filename="{p.name}"')
        msg.attach(att)
        return msg

    def _send_via_api(self, message, token, to_email, _retried=False) -> bool:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            resp = requests.post(url, headers=headers, json={"raw": raw})
            resp.raise_for_status()
            logger.info(f"Gmail sent to {to_email} (ID: {resp.json().get('id')})")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401 and not _retried:
                logger.warning("Token expired, refreshing...")
                if self.oauth._refresh_access_token():
                    return self._send_via_api(message, self.oauth._access_token, to_email, _retried=True)
            if e.response.status_code == 429:
                return self._handle_rate_limit(e, url, headers, raw, to_email)
            logger.error(f"Gmail API error for {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Gmail error for {to_email}: {e}")
            return False

    def _handle_rate_limit(self, exc, url, headers, raw, to_email) -> bool:
        try:
            match = re.search(r'Retry after (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)',
                              exc.response.text)
            if match:
                retry_at = datetime.strptime(match.group(1), '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC)
                wait = (retry_at - datetime.now(pytz.UTC)).total_seconds()
                if 0 < wait < 3600:
                    logger.warning(f"Rate limited. Waiting {wait:.0f}s...")
                    time.sleep(wait + 5)
                    resp = requests.post(url, headers=headers, json={"raw": raw})
                    resp.raise_for_status()
                    return True
        except Exception as e:
            logger.error(f"Rate limit handling failed: {e}")
        return False

    def _embed_image(self, message: email.mime.multipart.MIMEMultipart, image_path: str, cid: str):
        if not Path(image_path).exists():
            logger.warning(f"Image not found: {image_path}")
            return

        with open(image_path, 'rb') as f:
            img_data = f.read()

        mime_type = mimetypes.guess_type(image_path)[0] or 'image/png'
        main_type, sub_type = mime_type.split('/')

        img = email.mime.image.MIMEImage(img_data, _subtype=sub_type)
        img.add_header('Content-ID', f'<{cid}>')
        img.add_header('Content-Disposition', 'inline', filename=Path(image_path).name)
        message.attach(img)

import logging
import mimetypes
from pathlib import Path
from typing import List
from datetime import datetime, timedelta

import requests

from core.models import EmailConfig
from core.sender_base import BaseEmailSender

logger = logging.getLogger(__name__)


class ZohoAuthManager:

    def __init__(self, config: EmailConfig):
        self.config = config
        self.access_token = None
        self.token_expires_at = None

    def get_access_token(self) -> str:
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        return self._refresh()

    def _refresh(self) -> str:
        resp = requests.post("https://accounts.zoho.eu/oauth/v2/token", data={
            'grant_type': 'refresh_token',
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'refresh_token': self.config.refresh_token,
        })
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data['access_token']
        self.token_expires_at = datetime.now() + timedelta(seconds=data.get('expires_in', 3600) - 60)
        logger.info("Zoho access token refreshed")
        return self.access_token


class ZohoEmailSender(BaseEmailSender):

    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.auth = ZohoAuthManager(config)
        self.api_base = "https://mail.zoho.eu/api"
        self._account_id = None

    def send_one(self, to_email, subject, body, attachment_path=None, cc=None, bcc=None):
        token = self.auth.get_access_token()
        acct = self._get_account_id()
        headers = {'Authorization': f'Zoho-oauthtoken {token}'}

        if attachment_path:
            return self._send_with_attachment(to_email, subject, body, attachment_path, headers, acct, cc=cc, bcc=bcc)

        headers['Content-Type'] = 'application/json'
        payload = {
            'fromAddress': self.config.sender_email,
            'toAddress': to_email,
            'subject': subject,
            'content': body,
            'mailFormat': 'html',
        }
        if cc:
            payload['ccAddress'] = ','.join(cc) if isinstance(cc, list) else cc
        if bcc:
            payload['bccAddress'] = ','.join(bcc) if isinstance(bcc, list) else bcc

        resp = requests.post(f"{self.api_base}/accounts/{acct}/messages", headers=headers, json=payload, timeout=30)
        return resp.status_code == 200

    def _send_with_attachment(self, to_email, subject, body, path, headers, acct, cc=None, bcc=None):
        p = Path(path)
        mime = mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
        files = {
            'fromAddress': (None, self.config.sender_email),
            'toAddress': (None, to_email),
            'subject': (None, subject),
            'content': (None, body),
            'mailFormat': (None, 'html'),
            'attachments': (p.name, p.read_bytes(), mime),
        }
        if cc:
            files['ccAddress'] = (None, ','.join(cc) if isinstance(cc, list) else cc)
        if bcc:
            files['bccAddress'] = (None, ','.join(bcc) if isinstance(bcc, list) else bcc)

        resp = requests.post(f"{self.api_base}/accounts/{acct}/messages",
                             headers=headers, files=files, timeout=30)
        return resp.status_code == 200

    def _get_account_id(self):
        if self._account_id:
            return self._account_id
        token = self.auth.get_access_token()
        resp = requests.get(f"{self.api_base}/accounts", headers={
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json',
        }, timeout=30)
        resp.raise_for_status()
        self._account_id = resp.json()['data'][0]['accountId']
        return self._account_id

import os
import base64
import mimetypes
import logging
from pathlib import Path
from string import Template
from typing import Dict, Tuple, Optional

from core.models import Student, TemplateSpec

logger = logging.getLogger(__name__)


class EmailTemplateEngine:

    def __init__(self, subject_template: str, body_template: str):
        self.subject_tpl = Template(subject_template)
        self.body_tpl = Template(body_template)

    def create_personalized_email(self, student: Student) -> Dict[str, str]:
        v = student.template_vars
        return {
            'subject': self.subject_tpl.safe_substitute(v),
            'body': self.body_tpl.safe_substitute(v),
        }

    @staticmethod
    def load_template_file(path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Template loaded: {path} ({len(content)} chars)")
            return content
        except Exception as e:
            logger.error(f"Error loading template {path}: {e}")
            return "<p>Hello $first_name,</p><p>Welcome!</p>"


def resolve_templates(spec: TemplateSpec, config_data: dict = None,
                      subject_override: str = None) -> Tuple[str, str]:
    subject = subject_override or spec.default_subject
    body = EmailTemplateEngine.load_template_file(spec.template_file)

    if config_data and config_data.get('email_templates'):
        tpl_cfg = config_data['email_templates']
        if not subject_override and spec.config_subject_key:
            subject = tpl_cfg.get(spec.config_subject_key, subject)
        if spec.config_body_key:
            cfg_body = tpl_cfg.get(spec.config_body_key, '')
            if cfg_body.startswith('TEMPLATE_FILE:'):
                body = EmailTemplateEngine.load_template_file(cfg_body.replace('TEMPLATE_FILE:', ''))
            elif cfg_body:
                body = cfg_body

    return subject, body


def embed_images(body: str, image_map: Dict[str, str] = None) -> str:
    if image_map is None:
        image_map = {
            "logo": "image/MBP.png",
            "signature": "image/signature.png",
            "qrcode": "image/qrcode.png",
        }

    for cid, path in image_map.items():
        p = Path(path)
        if not p.exists():
            logger.debug(f"Image not found for cid:{cid}: {path}")
            continue
        b64 = base64.b64encode(p.read_bytes()).decode()
        mime = mimetypes.guess_type(str(p))[0] or "image/png"
        body = body.replace(f'src="cid:{cid}"', f'src="data:{mime};base64,{b64}"')
    return body

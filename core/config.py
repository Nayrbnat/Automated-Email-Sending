import json
import os
import logging
from typing import Dict
from dotenv import load_dotenv

from core.models import EmailConfig, TemplateSpec

logger = logging.getLogger(__name__)


def load_config(config_file: str = "config.json") -> dict:
    load_dotenv()
    with open(config_file, 'r') as f:
        return json.load(f)


def create_email_config(config_data: dict, provider: str = "zoho") -> EmailConfig:
    if provider not in ("zoho", "gmail"):
        raise ValueError(f"Unsupported provider: {provider}")

    pc = config_data.get(f"{provider}_config", {})
    if not pc:
        raise ValueError(f"No configuration found for provider: {provider}")

    prefix = provider.upper()

    cfg = EmailConfig(
        client_id=_get_env_or_config(pc.get("client_id"), f"{prefix}_CLIENT_ID"),
        client_secret=_get_env_or_config(pc.get("client_secret"), f"{prefix}_CLIENT_SECRET"),
        refresh_token=_get_env_or_config(pc.get("refresh_token"), f"{prefix}_REFRESH_TOKEN", ""),
        sender_email=_get_env_or_config(pc.get("sender_email"), f"{prefix}_SENDER_EMAIL"),
        sender_name=_get_env_or_config(pc.get("sender_name"), f"{prefix}_SENDER_NAME", "Your Name"),
        provider=provider,
    )
    logger.info(f"Config loaded — Provider: {provider.upper()}, Email: {cfg.sender_email}")
    return cfg


def load_template_specs(config_data: dict) -> Dict[str, TemplateSpec]:
    specs = {}
    templates = config_data.get("templates", {})
    for name, data in templates.items():
        specs[name] = TemplateSpec.from_dict(name, data)
    return specs


def _get_env_or_config(config_value: str, env_var: str, default: str = "") -> str:
    if isinstance(config_value, str) and config_value.startswith("ENV:"):
        return os.getenv(config_value.replace("ENV:", ""), default)
    return os.getenv(env_var) or config_value or default

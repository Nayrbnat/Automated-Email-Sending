from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class EmailConfig:
    client_id: str
    client_secret: str
    sender_email: str
    refresh_token: str = ""
    sender_name: str = "Your Name"
    provider: str = "zoho"


@dataclass
class TemplateSpec:
    name: str
    default_subject: str
    template_file: str
    csv_file: Optional[str] = None
    csv_loader: str = "names"
    name_column: int = 0
    email_column: int = 1
    config_subject_key: Optional[str] = None
    config_body_key: Optional[str] = None
    description: str = ""
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, data: dict) -> "TemplateSpec":
        return cls(
            name=name,
            default_subject=data.get("subject", data.get("default_subject", "")),
            template_file=data.get("template_file", ""),
            csv_file=data.get("csv_file", None),
            csv_loader=data.get("csv_loader", "names"),
            name_column=data.get("name_column", 0),
            email_column=data.get("email_column", 1),
            config_subject_key=data.get("config_subject_key", None),
            config_body_key=data.get("config_body_key", None),
            description=data.get("description", ""),
            cc=data.get("cc", []),
            bcc=data.get("bcc", []),
        )


@dataclass
class Student:
    email: str
    name: str
    first_name: str
    last_name: str
    team_name: str = ""
    room_number: str = ""
    presentation_slot: str = ""
    presentation_time: str = ""
    zoom_link: str = ""
    zoom_meeting_id: str = ""
    zoom_password: str = ""

    @property
    def template_vars(self) -> Dict[str, str]:
        return {
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'team_name': self.team_name,
            'room_number': self.room_number,
            'presentation_slot': self.presentation_slot,
            'presentation_time': self.presentation_time,
            'zoom_link': self.zoom_link,
            'zoom_meeting_id': self.zoom_meeting_id,
            'zoom_password': self.zoom_password,
        }

import logging
from typing import List, Dict

from core.models import Student

logger = logging.getLogger(__name__)


def parse_student_entry(entry: str) -> Student:
    entry = entry.strip()

    parts = entry.split()
    if len(parts) >= 2 and '@' in parts[-1]:
        name = ' '.join(parts[:-1])
        return Student(email=parts[-1].lower(), name=name, first_name=name, last_name="")

    if ' (ug) ' in entry:
        try:
            name_part, email_part = entry.split(' (ug) ', 1)
            if ',' in name_part:
                last, first = name_part.split(',', 1)
                return Student(
                    email=email_part.strip().lower(),
                    name=f"{first.strip()} {last.strip()}",
                    first_name=first.strip(),
                    last_name=last.strip(),
                )
        except Exception:
            pass

    return Student(email=entry.lower(), name="", first_name="", last_name="")


def parse_stock_pitch_row(row: Dict[str, str]) -> List[Student]:
    emails = [e.strip() for e in row.get('email_address', '').split(';') if '@' in e]
    names = [n.strip() for n in row.get('full_name', '').split(';') if n.strip()]

    shared = dict(
        team_name=row.get('team_name', '').strip(),
        room_number=row.get('room_number', '').strip(),
        presentation_slot=row.get('presentation_slot', '').strip(),
        presentation_time=row.get('presentation_time', '').strip(),
        zoom_link=row.get('zoom_link', '').strip(),
        zoom_meeting_id=row.get('zoom_meeting_id', '').strip(),
        zoom_password=row.get('zoom_password', '').strip(),
    )

    students = []
    for i, addr in enumerate(emails):
        name = names[i] if i < len(names) else ""
        parts = name.split()
        students.append(Student(
            email=addr.lower(),
            name=name,
            first_name=parts[0] if parts else "",
            last_name=' '.join(parts[1:]) if len(parts) > 1 else "",
            **shared,
        ))
    return students

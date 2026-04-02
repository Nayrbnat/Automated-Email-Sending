import time
import logging
from typing import List, Dict
from abc import ABC, abstractmethod

from core.models import EmailConfig, Student
from core.template_engine import EmailTemplateEngine, embed_images

logger = logging.getLogger(__name__)


class BaseEmailSender(ABC):

    def __init__(self, config: EmailConfig):
        self.config = config

    @abstractmethod
    def send_one(self, to_email: str, subject: str, body: str,
                 attachment_path: str = None, cc: List[str] = None, bcc: List[str] = None) -> bool:
        ...

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = True,
                   cc: List[str] = None, bcc: List[str] = None) -> bool:
        return self.send_one(to_email, subject, body, attachment_path=None, cc=cc, bcc=bcc)

    def send_email_with_embedded_images(self, to_email: str, subject: str, body: str,
                                       logo_path: str, signature_path: str, qrcode_path: str = None,
                                       cc: List[str] = None, bcc: List[str] = None) -> bool:
        try:
            image_map = {
                "logo": logo_path,
                "signature": signature_path,
            }
            if qrcode_path:
                image_map["qrcode"] = qrcode_path

            modified_body = embed_images(body, image_map)
            return self.send_one(to_email, subject, modified_body, attachment_path=None, cc=cc, bcc=bcc)
        except Exception as e:
            logger.error(f"Error sending email with embedded images to {to_email}: {e}")
            return False

    def send_email_with_inline_image(self, to_email: str, subject: str, body: str, image_path: str,
                                     cc: List[str] = None, bcc: List[str] = None) -> bool:
        return self.send_email_with_embedded_images(to_email, subject, body, image_path, image_path, cc=cc, bcc=bcc)

    def send_email_with_attachment(self, to_email: str, subject: str, body: str,
                                   attachment_path: str, is_html: bool = True,
                                   cc: List[str] = None, bcc: List[str] = None) -> bool:
        return self.send_one(to_email, subject, body, attachment_path=attachment_path, cc=cc, bcc=bcc)

    def send_bulk(self, students: List[Student], engine: EmailTemplateEngine,
                  batch_size: int = 50, batch_delay_min: int = 1,
                  attachment_path: str = None, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, int]:
        results = {'sent': 0, 'failed': 0}
        total = len(students)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_num = start // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            logger.info(f"Batch {batch_num}/{total_batches} (emails {start+1}-{end} of {total})")

            for student in students[start:end]:
                try:
                    content = engine.create_personalized_email(student)
                    body = embed_images(content['body'])
                    ok = self.send_one(student.email, content['subject'], body, attachment_path, cc=cc, bcc=bcc)
                    results['sent' if ok else 'failed'] += 1
                    if ok:
                        logger.info(f"Sent to {student.email}")
                    else:
                        logger.error(f"Failed for {student.email}")
                except Exception as e:
                    results['failed'] += 1
                    logger.error(f"Error for {student.email}: {e}")
                time.sleep(3)

            if end < total:
                logger.info(f"Batch done. Waiting {batch_delay_min} min...")
                time.sleep(batch_delay_min * 60)

        logger.info(f"All done — sent: {results['sent']}, failed: {results['failed']}")
        return results

    def send_bulk_emails(self, students: List[Student], template_engine: EmailTemplateEngine,
                        batch_size: int = 50, batch_delay_minutes: int = 1,
                        attachment_path: str = None, cc: List[str] = None, bcc: List[str] = None) -> Dict[str, int]:
        return self.send_bulk(students, template_engine, batch_size, batch_delay_minutes, attachment_path, cc=cc, bcc=bcc)


def create_sender(config: EmailConfig) -> BaseEmailSender:
    from core.sender_gmail import GmailEmailSender
    from core.sender_zoho import ZohoEmailSender
    if config.provider == "gmail":
        return GmailEmailSender(config)
    return ZohoEmailSender(config)

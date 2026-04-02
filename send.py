import argparse
import logging
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from core.config import load_config, create_email_config, load_template_specs
from core.template_engine import EmailTemplateEngine, resolve_templates
from core.loader import load_recipients
from core.sender_base import create_sender
from core.results import ResultsSaver

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_args():
    config_data = load_config()
    specs = load_template_specs(config_data)
    choices = list(specs.keys()) if specs else ["welcome"]

    parser = argparse.ArgumentParser(description='Email Automation System')
    parser.add_argument('--template', choices=choices, default='welcome', help='Email template to use')
    parser.add_argument('--provider', choices=['zoho', 'gmail'], default='zoho')
    parser.add_argument('--test', action='store_true', help='Test mode: parse without sending')
    parser.add_argument('--UG1', action='store_true', help='Use UG1_members_clean.csv')
    parser.add_argument('--bootcamp', action='store_true', help='Use bootcamp_applicants.csv')
    parser.add_argument('--subject', type=str, help='Custom subject (overrides template default)')
    parser.add_argument('--attach', type=str, help='Path to file attachment')
    return parser.parse_args(), config_data, specs


def main():
    args, config_data, specs = parse_args()

    if args.attach and not Path(args.attach).exists():
        print(f"\u274c Attachment not found: {args.attach}")
        return

    email_config = create_email_config(config_data, args.provider)
    settings = config_data.get('settings', {})
    spec = specs[args.template]

    print(f"\U0001f3af EMAIL AUTOMATION SYSTEM")
    print(f"   Provider: {args.provider.upper()}")
    print(f"   Template: {spec.name} \u2014 {spec.description}")
    print(f"   File:     {spec.template_file}")
    print("=" * 40)

    subject, body = resolve_templates(spec, config_data, args.subject)
    students = load_recipients(spec, args)

    if not students:
        print("\u274c No recipients found")
        return

    if args.test:
        print(f"\U0001f9ea TEST MODE \u2014 {len(students)} recipients:")
        for i, s in enumerate(students, 1):
            line = f"  {i:3d}. {s.name} <{s.email}>"
            if s.team_name:
                line += f" \u2014 Team: {s.team_name}"
            if s.room_number:
                line += f" | Room {s.room_number}, Slot {s.presentation_slot} at {s.presentation_time}"
            print(line)
        print(f"\n\U0001f4ca Total: {len(students)} | \U0001f6ab No emails sent")
        return

    sender = create_sender(email_config)
    engine = EmailTemplateEngine(subject, body)
    results = sender.send_bulk(
        students, engine,
        batch_size=settings.get('batch_size', 50),
        batch_delay_min=settings.get('batch_delay_minutes', 1),
        attachment_path=args.attach,
        cc=spec.cc if spec.cc else None,
        bcc=spec.bcc if spec.bcc else None,
    )

    total = len(students)
    sent = results['sent']
    rate = f"{sent/total*100:.1f}%" if total else "0%"
    print(f"\u2705 Done: {sent}/{total} sent ({rate})")
    if results['failed']:
        print(f"\u26a0\ufe0f  {results['failed']} failed")

    ResultsSaver.save({
        'total_emails': total,
        'emails_sent': sent,
        'emails_failed': results['failed'],
        'success_rate': rate,
        'students': students,
    })


if __name__ == "__main__":
    main()

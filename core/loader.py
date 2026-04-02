import csv
import logging
from pathlib import Path
from typing import List

from core.models import Student, TemplateSpec
from core.parser import parse_student_entry, parse_stock_pitch_row

logger = logging.getLogger(__name__)


def load_emails(source, email_column: int = 0) -> List[str]:
    if isinstance(source, list):
        return [e.strip() for e in source if '@' in e.strip()]

    path = Path(source)
    if not path.exists():
        logger.error(f"File not found: {source}")
        return []

    with open(path, 'r', encoding='utf-8') as f:
        if str(source).endswith('.csv'):
            return _load_csv(f, email_column)
        return _load_txt(f)


def load_csv_with_names(file_path: str, name_column: int = 0, email_column: int = 1) -> List[str]:
    entries = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row and len(row) > max(name_column, email_column):
                name = row[name_column].strip()
                addr = row[email_column].strip()
                if name and addr and '@' in addr:
                    entries.append(f"{name.replace(', ', '. ')} {addr}")
    logger.info(f"Loaded {len(entries)} name-email pairs from CSV")
    return entries


def load_stock_pitch_csv(file_path: str) -> List[Student]:
    students = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for row_num, row in enumerate(csv.DictReader(f), 1):
            try:
                students.extend(parse_stock_pitch_row(row))
            except Exception as e:
                logger.error(f"Error parsing row {row_num}: {e}")
    logger.info(f"Loaded {len(students)} student records from stock pitch CSV")
    return students


def load_recipients(spec: TemplateSpec, cli_args) -> List[Student]:
    csv_file = spec.csv_file

    if not csv_file:
        if cli_args.UG1:
            csv_file = "data/UG1_members_clean.csv"
        elif cli_args.bootcamp:
            csv_file = "data/bootcamp_applicants.csv"
        else:
            entries = load_emails("sample_emails.txt")
            return [parse_student_entry(e) for e in entries]

    if cli_args.test and csv_file:
        test_csv = csv_file.replace('.csv', '_test.csv')
        if Path(test_csv).exists():
            logger.info(f"Test mode: Using {test_csv} instead of {csv_file}")
            csv_file = test_csv

    if spec.csv_loader == "stock_pitch":
        return load_stock_pitch_csv(csv_file)
    elif spec.csv_loader == "names":
        entries = load_csv_with_names(csv_file, spec.name_column, spec.email_column)
        return [parse_student_entry(e) for e in entries]
    else:
        entries = load_emails(csv_file)
        return [parse_student_entry(e) for e in entries]


def _load_csv(fh, email_column: int) -> List[str]:
    emails = [row[email_column].strip()
              for row in csv.reader(fh)
              if row and len(row) > email_column and '@' in row[email_column]]
    logger.info(f"Loaded {len(emails)} emails from CSV")
    return emails


def _load_txt(fh) -> List[str]:
    entries = []
    for line in fh:
        for part in line.strip().split(';'):
            part = part.strip()
            if '@' in part:
                entries.append(part)
    logger.info(f"Loaded {len(entries)} entries from text file")
    return entries

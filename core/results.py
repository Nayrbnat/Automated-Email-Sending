import json
import os
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class ResultsSaver:

    @staticmethod
    def save(results: Dict, directory: str = "results/") -> str:
        os.makedirs(directory, exist_ok=True)
        filename = os.path.join(
            directory,
            f"email_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        out = {k: v for k, v in results.items() if k != 'students'}
        out['students'] = [{'email': s.email, 'name': s.name} for s in results.get('students', [])]
        out['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'success_rate': results.get('success_rate', '0%'),
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to {filename}")
        return filename

# services/material_auto_analyzer.py

import re
from collections import Counter

STOP_WORDS = {
    'и', 'в', 'на', 'что', 'это', 'как', 'для', 'по', 'из', 'или', 'при'
}

def extract_key_points(text, limit=7):
    """
    Простейшее выделение важных аспектов из текста материала
    """
    words = re.findall(r'\b[а-яА-Яa-zA-Z]{4,}\b', text.lower())
    words = [w for w in words if w not in STOP_WORDS]
    return [w for w, _ in Counter(words).most_common(limit)]


def analyze_material_answer(material_text, intern_answer):
    key_points = extract_key_points(material_text)

    answer_lower = intern_answer.lower()

    matched = [p for p in key_points if p in answer_lower]
    missed = [p for p in key_points if p not in answer_lower]

    coverage = len(matched) / len(key_points) if key_points else 0
    score = round(coverage * 100)

    summary = (
        f"Выделено {len(key_points)} ключевых аспектов. "
        f"Стажёр затронул {len(matched)}. "
        f"Пропущено: {', '.join(missed) if missed else 'нет'}."
    )

    return {
        'score': score,
        'coverage': coverage,
        'key_points': key_points,
        'matched': matched,
        'missed': missed,
        'summary': summary
    }

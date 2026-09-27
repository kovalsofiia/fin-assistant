"""Вручну сконструйовані мутанти backend/agent/drafts.py для пілотного експерименту.

Кожен мутант — одна цільова текстова заміна в оригінальному коді, що імітує типову
реальну помилку (межова умова, забута функція округлення/приведення типів тощо).
Мутанти застосовуються до тексту оригінального модуля, а не підтримуються окремо,
щоб вони завжди відповідали поточній версії drafts.py.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mutant:
    id: str
    description: str
    find: str
    replace: str


MUTANTS = [
    Mutant(
        id="m1_today_boundary",
        description="Межова умова дати: сьогоднішня дата помилково відхиляється як «майбутня» (> замінено на >=).",
        find="    if day > today:\n",
        replace="    if day >= today:\n",
    ),
    Mutant(
        id="m2_amount_boundary",
        description="Межова умова суми: дозволяє amount == MIN_TRANSACTION_AMOUNT (0.01), хоча має бути строго більше.",
        find="    if not (MIN_TRANSACTION_AMOUNT < value <= MAX_AMOUNT):\n",
        replace="    if not (MIN_TRANSACTION_AMOUNT <= value <= MAX_AMOUNT):\n",
    ),
    Mutant(
        id="m3_no_rounding",
        description="Забрано округлення суми до 2 знаків після коми.",
        find="        value = round(float(amount), 2)\n",
        replace="        value = float(amount)\n",
    ),
    Mutant(
        id="m4_max_past_days",
        description="Ліміт «не давніше 5 років» помилково дозволяє 6 років (366*5 замінено на 366*6).",
        find="MAX_PAST_DAYS = 5 * 366\n",
        replace="MAX_PAST_DAYS = 6 * 366\n",
    ),
    Mutant(
        id="m5_is_fop_not_bool",
        description="Забрано приведення is_fop до bool: нетипові значення (напр. рядки) не нормалізуються.",
        find='        "is_fop": bool(is_fop),\n',
        replace='        "is_fop": is_fop,\n',
    ),
    Mutant(
        id="m6_description_off_by_one",
        description="Обрізання опису на символ коротше за MAX_DESCRIPTION_CHARS (off-by-one).",
        find="[:MAX_DESCRIPTION_CHARS]",
        replace="[:MAX_DESCRIPTION_CHARS - 1]",
    ),
    Mutant(
        id="m7_category_case_sensitive",
        description="Пошук категорії стає чутливим до регістру (casefold прибрано).",
        find='        if str(category.get("name", "")).casefold() == wanted.casefold():\n',
        replace='        if str(category.get("name", "")) == wanted:\n',
    ),
]


def apply_mutant(original_source: str, mutant: Mutant) -> str:
    """Повертає код модуля з одним застосованим мутантом. Кидає, якщо шаблон не знайдено рівно один раз."""
    count = original_source.count(mutant.find)
    if count != 1:
        raise ValueError(f"Мутант {mutant.id}: шаблон знайдено {count} раз(и), очікувалось 1")
    return original_source.replace(mutant.find, mutant.replace, 1)

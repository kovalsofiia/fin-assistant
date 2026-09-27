"""Витяг Python-коду з текстової відповіді моделі."""
import re

_FENCE_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


class NoCodeFoundError(ValueError):
    """У відповіді моделі не знайдено жодного блоку коду."""


def extract_python_code(text: str) -> str:
    """Повертає вміст першого блоку ```python ... ``` (або ``` ... ```, якщо мова не вказана).

    Якщо блоків кілька, повертає найдовший — модель іноді додає короткий приклад
    імпорту окремим блоком перед основним файлом.
    """
    blocks = _FENCE_RE.findall(text)
    if not blocks:
        raise NoCodeFoundError("Відповідь моделі не містить блоку коду в потрійних лапках")
    return max(blocks, key=len).strip() + "\n"

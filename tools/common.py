"""Общее для скриптов: чтение журналов проекта и список грамматики B2. Ничего не пишет."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for _stream in (sys.stdout, sys.stderr):  # Windows: консоль не в UTF-8 — польский и русский текст падали бы
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

WORD_USED_COL = 6  # words.md: id, слово, пример, регистр, тема, добавлено, употреблено, последний раз
# errors.md: id, тема, тип, пропуск (подсказка), ответ, контекст, правило, грамматика, ошибок, верно, дата, статус
ERR_CLOZE_COL, ERR_CONTEXT_COL, ERR_G_COL, ERR_COUNT_COL, ERR_OK_COL = 3, 5, 7, 8, 9
# reviews.md: когда, режим, id, что, формат, результат, заметка
REV_WHEN, REV_ID, REV_RESULT = 0, 2, 5

GRAMMAR_MARKERS = [
    (re.compile(r"^2\.2\.\d+\."), 0),
    (re.compile(r"^\d+\)\s"), 1),
    (re.compile(r"^[a-z]\)\s"), 2),
    (re.compile(r"^–\s"), 3),
    (re.compile(r"^•\s"), 4),
]


def read(name: str) -> str:
    path = ROOT / name
    return path.read_text(encoding="utf-8") if path.exists() else ""


def table_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_rows(name: str) -> list[list[str]]:
    """Строки таблиц с id вида E12 / W3 (errors.md, words.md)."""
    rows = []
    for line in read(name).splitlines():
        cells = table_cells(line)
        if line.startswith("|") and re.match(r"^[EW]\d+$", cells[0]):
            rows.append(cells)
    return rows


def review_rows() -> list[list[str]]:
    """Строки reviews.md — первая колонка начинается с даты."""
    rows = []
    for line in read("reviews.md").splitlines():
        cells = table_cells(line)
        if line.startswith("|") and re.match(r"^\d{4}-\d{2}-\d{2}", cells[0]) and len(cells) > REV_RESULT:
            rows.append(cells)
    return rows


def profile() -> dict[str, str]:
    """profile.md: строки «- **ключ:** значение» → {ключ: значение}; пустой словарь — профиля нет."""
    found = re.findall(r"^- \*\*(.+?):\*\*\s*(.*)$", read("profile.md"), flags=re.M)
    return {k.strip(): v.strip() for k, v in found}


def as_int(cells: list[str], col: int) -> int:
    return int(cells[col]) if len(cells) > col and cells[col].isdigit() else 0


def grammar_leaves() -> list[str]:
    """108 пунктов грамматики B2 (листья списка 2.2 стандарта) с цепочкой родителей. G-номер = позиция + 1."""
    text = read("sources/b2-standard.md")
    section = text[text.index("### 2.2."):text.index("## 3.")]
    items: list[tuple[int, str]] = []
    stack: dict[int, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        level = next((lvl for rx, lvl in GRAMMAR_MARKERS if rx.match(line)), None)
        if level is None:
            if items:
                items[-1] = (items[-1][0], items[-1][1] + " " + line)
            continue
        stack = {k: v for k, v in stack.items() if k < level}
        stack[level] = line
        items.append((level, " › ".join(stack[k] for k in sorted(stack))))
    # лист = пункт, за которым не идёт более глубокий
    return [path for i, (lvl, path) in enumerate(items)
            if i + 1 == len(items) or items[i + 1][0] <= lvl]

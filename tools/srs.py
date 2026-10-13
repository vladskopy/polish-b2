"""Интервальное повторение — лесенка Лейтнера поверх reviews.md. Без базы: состояние каждый раз
пересчитывается из истории.

- ступени 1–5, интервалы 1 / 3 / 7 / 21 / 60 дней;
- ступень меняется один раз за подход: все строки с одним временем «когда» — один подход
  (5 пунктов в powtórka — это одно повторение, а не пять прыжков); подход засчитан, если ✓ ≥ 80%;
- засчитан → ступень +1 (максимум 5), не засчитан → ступень 1; «–» не считается;
- слово стартует со ступени 1 в день «добавлено»;
- «спит»: ошибка встретилась один раз, больше не возвращалась и старше 30 дней — в очередь не идёт;
- закрытые ошибки в очередь не идут.

    python3 tools/srs.py        # очередь на сегодня
"""
from dataclasses import dataclass
from datetime import date, timedelta

import common as c

INTERVALS = {1: 1, 2: 3, 3: 7, 4: 21, 5: 60}
PASS_SHARE = 0.8
SLEEP_AFTER_DAYS = 30


@dataclass(frozen=True)
class Card:
    rid: str          # E12 / W3
    box: int          # ступень 1–5
    last: date        # последний подход
    due: date         # когда повторить
    attempts: int     # подходов всего
    state: str        # due / later / sleeping / closed

    def overdue(self, today: date) -> int:
        return (today - self.due).days


def _day(when: str) -> date:
    return date.fromisoformat(when[:10])


def _sessions(rows: list[list[str]]) -> list[tuple[str, bool]]:
    """Строки одного id → подходы [(когда, засчитан)] по времени."""
    groups: dict[str, list[str]] = {}
    for r in rows:
        mark = r[c.REV_RESULT][:1]
        if mark in "✓✗":
            groups.setdefault(r[c.REV_WHEN], []).append(mark)
    return [(when, marks.count("✓") / len(marks) >= PASS_SHARE) for when, marks in sorted(groups.items())]


def build_card(rid: str, rows: list[list[str]], start: str = "", closed: bool = False,
               errors_count: int = 0, today: date | None = None) -> Card | None:
    today = today or date.today()
    history = _sessions(rows)
    if start:
        history = [(start, False)] + history  # старт слова: ступень 1 с даты добавления
    if not history:
        return None
    box = 1
    for _, passed in history:
        box = min(box + 1, 5) if passed else 1
    last = _day(history[-1][0])
    due = last + timedelta(days=INTERVALS[box])
    if closed:
        state = "closed"
    elif rid.startswith("E") and len(history) == 1 and errors_count <= 1 \
            and (today - last).days > SLEEP_AFTER_DAYS:
        state = "sleeping"
    else:
        state = "due" if due <= today else "later"
    return Card(rid, box, last, due, len(history), state)


def cards(today: date | None = None) -> list[Card]:
    today = today or date.today()
    by_id: dict[str, list[list[str]]] = {}
    for r in c.review_rows():
        by_id.setdefault(r[c.REV_ID], []).append(r)
    out = []
    for e in c.table_rows("errors.md"):
        card = build_card(e[0], by_id.get(e[0], []), closed=e[-1] == "закрыта",
                          errors_count=c.as_int(e, c.ERR_COUNT_COL), today=today)
        if card:
            out.append(card)
    for w in c.table_rows("words.md"):
        card = build_card(w[0], by_id.get(w[0], []), start=w[5], today=today)
        if card:
            out.append(card)
    return out


def queue(today: date | None = None) -> list[Card]:
    """Пора повторить: сначала самые просроченные, потом с нижних ступеней."""
    today = today or date.today()
    due = [k for k in cards(today) if k.state == "due"]
    return sorted(due, key=lambda k: (-k.overdue(today), k.box, k.rid))


def summary(today: date | None = None) -> str:
    today = today or date.today()
    all_cards = cards(today)
    due = [k for k in all_cards if k.state == "due"]
    boxes = [sum(1 for k in all_cards if k.box == b and k.state in ("due", "later")) for b in range(1, 6)]
    sleeping = sum(1 for k in all_cards if k.state == "sleeping")
    nxt = min((k.due for k in all_cards if k.state == "later"), default=None)
    line = (f"к повторению сегодня {len(due)} (ошибок {sum(k.rid.startswith('E') for k in due)}, "
            f"слов {sum(k.rid.startswith('W') for k in due)}) · ступени 1–5: {' / '.join(map(str, boxes))}")
    if sleeping:
        line += f" · спят {sleeping}"
    if not due and nxt:
        line += f" · следующее повторение {nxt:%d.%m}"
    return line


if __name__ == "__main__":
    today = date.today()
    print("ПОВТОРЕНИЕ:", summary(today))
    for k in queue(today):
        print(f"  {k.rid} · ступень {k.box} · был {k.last:%d.%m} · просрочено {k.overdue(today)} дн.")

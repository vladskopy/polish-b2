"""Вытягивает материал для сессии польского. Читает только md-файлы проекта, ничего не пишет.

`--plan`: маршрут для /b2 — долг повторения и что сегодня: повторка или новые темы.
Без флага (новые темы): 2 необсуждённые подтемы, грамматический крючок из слабого звена (grammar.py),
1 ошибка и 1 слово, которым пора на повторение (srs.py).
`--powtorka`: до 3 ошибок и 2 слов, которым пора на повторение, — самые просроченные первыми.
`--sluchanie` / `--czytanie`: тема и угол для движков из parts/.
"""
import random
import re
import sys
from datetime import date, datetime

import common as c
import grammar
import srs

CHECKPOINT_EVERY = 5  # сессий между проверками по Systemantics — tasks/systemantics-check.md
DEBT_FOR_POWTORKA = 3  # столько ошибок «пора повторить» — и /b2 ведёт на повторку
MAX_POWTORKA_IN_ROW = 2  # после двух повторок подряд — новые темы, чтобы не надоело
PARTS = ["mówienie", "gramatyka", "słuchanie", "czytanie", "pisanie"]
ROTATION = ["mówienie", "słuchanie", "czytanie"]  # между ними выбирает маршрут, когда долга нет
ROUTE_FOR_PART = {"mówienie": "темы", "słuchanie": "słuchanie", "czytanie": "czytanie", "gramatyka": "powtórka"}
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


def subtopics() -> tuple[list[str], list[str]]:
    done, todo = [], []
    for line in c.read("topics.md").splitlines():
        m = re.match(r"^- \[( |x)\] \*\*(\d+\.\d+)\*\* (.*)", line)
        if m:
            (done if m.group(1) == "x" else todo).append(f"{m.group(2)} {m.group(3)}")
    return done, todo


def sessions_done() -> int:
    return sum(1 for line in c.read("log.md").splitlines() if re.match(r"^## \d{4}-\d{2}-\d{2}", line))


def powtorka_picks(n_errors: int = 3, n_words: int = 2) -> tuple[list[srs.Card], list[srs.Card]]:
    """Из очереди повторения: самые просроченные, потом с нижних ступеней."""
    due = srs.queue()
    return ([k for k in due if k.rid.startswith("E")][:n_errors],
            [k for k in due if k.rid.startswith("W")][:n_words])


def last_session_kinds(n: int) -> list[str]:
    """Типы последних n сессий из log.md (новые сверху): 'powtórka' или 'темы'."""
    heads = [line for line in c.read("log.md").splitlines() if re.match(r"^## \d{4}-\d{2}-\d{2}", line)]
    return ["powtórka" if "powtórka" in h else "темы" for h in heads[:n]]


def part_history() -> dict[str, list[str]]:
    """Часть экзамена → даты сессий (новые первыми). Строка «- часть: …» в записи log.md;
    в старых записях без неё: powtórka → gramatyka, иначе mówienie."""
    history: dict[str, list[str]] = {p: [] for p in PARTS}
    when, part = "", ""
    for line in c.read("log.md").splitlines() + ["## 9999-99-99 конец"]:
        m = re.match(r"^## (\d{4}-\d{2}-\d{2})", line)
        if m:
            if when:
                history[part or ("gramatyka" if "powtórka" in head else "mówienie")].append(when)
            when, part, head = m.group(1), "", line
            if when.startswith("9999"):
                break
        elif when and (pm := re.match(r"^- часть:\s*(\S+)", line)) and pm.group(1) in history:
            part = pm.group(1)
    return history


def teacher_tomorrow(today: date) -> bool:
    day = c.profile().get("день занятий", "").lower()
    if day not in WEEKDAYS:
        return False
    tomorrow = WEEKDAYS[(today.weekday() + 1) % 7]
    recent = re.findall(r"^## (\d{4}-\d{2}-\d{2})", c.read("teacher-log.md"), flags=re.M)
    fresh = any((today - date.fromisoformat(d)).days < 6 for d in recent)
    return day == tomorrow and not fresh


def plan() -> tuple[str, str]:
    """(маршрут, почему) для /b2: долг повторения → повторка; иначе часть, к которой дольше не подходили."""
    due_errors = [k for k in srs.queue() if k.rid.startswith("E")]
    recent = last_session_kinds(MAX_POWTORKA_IN_ROW)
    in_row = recent == ["powtórka"] * MAX_POWTORKA_IN_ROW
    if len(due_errors) >= DEBT_FOR_POWTORKA and not in_row:
        return "powtórka", f"ошибок пора повторить {len(due_errors)} (порог {DEBT_FOR_POWTORKA})"
    history = part_history()
    candidates = random.sample(ROTATION, len(ROTATION))
    part = min(candidates, key=lambda p: history[p][0] if history[p] else "")
    last = history[part][0] if history[part] else "ни разу"
    why = f"дольше всего не было: {part} ({last})"
    if in_row and due_errors:
        why += f"; {MAX_POWTORKA_IN_ROW} повторки подряд — долг подтянется через строку ПОВТОР"
    return ROUTE_FOR_PART[part], why


def parts_line() -> str:
    history = part_history()
    return " · ".join(f"{p} {len(history[p])}" + (f" ({history[p][0][5:]})" if history[p] else "") for p in PARTS)


def print_progress(done: list[str], todo: list[str], errors: list[list[str]], words: list[list[str]]) -> None:
    closed = len(c.table_rows("errors.md")) - len(errors)
    reused = sum(1 for r in words if c.as_int(r, c.WORD_USED_COL) > 0)
    sessions = sessions_done()
    print(f"ПРОГРЕСС: ошибок закрыто {closed} (открыто {len(errors)}) · "
          f"слов употреблено снова {reused} из {len(words)}")
    print(f"ПОКРЫТИЕ: подтемы {len(done)}/{len(done) + len(todo)} · сессий {sessions}")
    all_items = grammar.items()
    print("ГРАММАТИКА:", grammar.summary_line(all_items, grammar.analyze()))
    print("ПОВТОРЕНИЕ:", srs.summary())
    if sessions and sessions % CHECKPOINT_EVERY == 0:
        print(f"ЧЕКПОИНТ: позади {sessions} сессий — после этой пройти tasks/systemantics-check.md")


def describe_card(k: srs.Card, rows: dict[str, list[str]]) -> str:
    r = rows[k.rid]
    if k.rid.startswith("W"):
        return f"{k.rid} {r[1]} · ступень {k.box}"
    g = f" · {r[c.ERR_G_COL]}" if len(r) > c.ERR_G_COL and r[c.ERR_G_COL] not in ("—", "") else ""
    return (f"{k.rid} [{r[2]}{g}] {r[c.ERR_CLOZE_COL]} · ступень {k.box}, "
            f"просрочено {k.overdue(date.today())} дн.")


def main() -> None:
    done, todo = subtopics()
    errors = [r for r in c.table_rows("errors.md") if r[-1] != "закрыта"]
    words = c.table_rows("words.md")
    rows = {r[0]: r for r in c.table_rows("errors.md") + words}
    args = sys.argv[1:]
    print(f"НАЧАЛО: {datetime.now():%Y-%m-%d %H:%M}")

    if "--plan" in args:
        if not c.profile():
            print("ПЕРВЫЙ ЗАПУСК: профиля нет → .claude/skills/b2/setup.md")
            return
        mode, why = plan()
        print(f"МАРШРУТ: {mode} — {why}")
        print("ЧАСТИ (сессий, последняя):", parts_line())
        if teacher_tomorrow(date.today()):
            print("ЗАНЯТИЕ ЗАВТРА: предложить /nauczyciel — сводку к занятию")
    elif "--sluchanie" in args or "--czytanie" in args:
        pick = random.sample(todo, 1) if todo else []
        part = "słuchanie" if "--sluchanie" in args else "czytanie"
        print(f"РЕЖИМ: {part} — правила в parts/{'sluchanie' if part == 'słuchanie' else 'czytanie'}.md")
        print("ТЕМА:", pick[0] if pick else "любая из 18 областей")
        print("ИНТЕРЕСЫ (угол):", c.profile().get("интересы", "—"))
    elif "--powtorka" in args:
        top_errors, top_words = powtorka_picks()
        print("РЕЖИМ: powtórka")
        for k in top_errors:
            r = rows[k.rid]
            print(f"ОШИБКА: {describe_card(k, rows)}")
            if len(r) > c.ERR_CONTEXT_COL and r[c.ERR_CONTEXT_COL]:
                print(f"  ТВОЯ ФРАЗА: {r[c.ERR_CONTEXT_COL]}")
        if not top_errors:
            print("ОШИБКА: повторять сегодня нечего — лучше новые темы (/b2 новое)")
        print("СЛОВА:", " | ".join(describe_card(k, rows) for k in top_words) if top_words else "повторять нечего")
    else:
        picks = random.sample(todo, min(2, len(todo)))
        print("ТЕМЫ:", " | ".join(picks) if picks else "все подтемы пройдены — бери любые две для повторения")
        all_items, stats = grammar.items(), grammar.analyze()
        hook = grammar.focus(all_items, stats, 1)
        if hook:
            it = hook[0]
            reason = "обходишь" if stats[it.gid].status == "–" else f"не используешь, слабый раздел {it.section}"
            print(f"КРЮЧОК (грамматика B2): {it.gid} [{reason}] {it.path}")
        else:
            print("КРЮЧОК (грамматика B2): все пункты встречались — бери повторяющиеся ошибки")
        due_e, due_w = powtorka_picks(1, 1)
        review = [describe_card(k, rows) for k in due_e + due_w]
        print("ПОВТОР:", " | ".join(review) if review else "повторять сегодня нечего")
    print_progress(done, todo, errors, words)


if __name__ == "__main__":
    main()

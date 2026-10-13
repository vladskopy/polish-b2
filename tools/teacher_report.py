"""Сводка к занятию с преподавателем: что было с прошлой сводки — по журналам, без интерпретации.

Период — от последней записи в teacher-log.md (или вся история). Сравнение «было → стало» — по строке
<!-- metrics: … --> из прошлой записи. Ничего не пишет: запись в teacher-log.md делает скилл /nauczyciel.

    python3 tools/teacher_report.py
"""
import re
from collections import Counter
from datetime import datetime

import common as c
import grammar
import srs

METRICS_RE = re.compile(r"<!-- metrics: (.*?) -->")


def last_report() -> tuple[str, dict[str, int]]:
    """Дата последней сводки и её метрики; ('', {}) — если сводок ещё не было."""
    text = c.read("teacher-log.md")
    dates = re.findall(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", text, flags=re.M)
    found = METRICS_RE.findall(text)
    if not dates:
        return "", {}
    metrics = dict(kv.split("=") for kv in found[0].split()) if found else {}
    return dates[0], {k: int(v) for k, v in metrics.items()}


def sessions_since(since: str) -> list[str]:
    return [line[3:] for line in c.read("log.md").splitlines()
            if re.match(r"^## \d{4}-\d{2}-\d{2}", line) and line[3:19] >= since]


def ratings_since(since: str) -> list[int]:
    out, current = [], ""
    for line in c.read("log.md").splitlines():
        if re.match(r"^## \d{4}-\d{2}-\d{2}", line):
            current = line[3:19]
        m = re.match(r"^- зашло: (\d)/5", line)
        if m and current and current >= since:  # current пуст — это шаблон формата в шапке log.md
            out.append(int(m.group(1)))
    return out


def current_metrics() -> dict[str, int]:
    errors = c.table_rows("errors.md")
    words = c.table_rows("words.md")
    stats = grammar.analyze()
    status = Counter(s.status for s in stats.values())
    return {
        "sessions": len(sessions_since("")),
        "errors_open": sum(1 for r in errors if r[-1] != "закрыта"),
        "errors_closed": sum(1 for r in errors if r[-1] == "закрыта"),
        "grammar_seen": sum(1 for s in stats.values() if s.status != "∅"),
        "grammar_ok": status["✓"],
        "grammar_repeating": status["↻"],
        "words": len(words),
        "words_reused": sum(1 for r in words if c.as_int(r, c.WORD_USED_COL) > 0),
    }


def period_events(since: str) -> dict[str, list[tuple[str, str, str]]]:
    """id → [(когда, результат, формат)] для событий за период."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    for r in c.review_rows():
        if r[c.REV_WHEN] >= since:
            out.setdefault(r[c.REV_ID], []).append((r[c.REV_WHEN], r[c.REV_RESULT][:1], r[4]))
    return out


def report() -> str:
    since, prev = last_report()
    now = current_metrics()
    events = period_events(since)
    first_seen = {}
    for r in c.review_rows():
        first_seen.setdefault(r[c.REV_ID], r[c.REV_WHEN])
    errors = {r[0]: r for r in c.table_rows("errors.md")}
    items = {it.gid: it for it in grammar.items()}
    stats = grammar.analyze()

    new_err = [e for e in events if e.startswith("E") and first_seen[e] >= since]
    repeated = [e for e in events if e.startswith("E") and first_seen[e] < since
                and any(res == "✗" for _, res, _ in events[e])]
    trained = {e: (sum(res == "✓" for _, res, _ in ev), len(ev)) for e, ev in events.items()
               if e.startswith("E") and any(fmt != "в речи" for _, _, fmt in ev)}
    g_fixed = [g for g, st in stats.items() if st.status == "✓" and any(
        w < since and res in "✗–" for w, res in st.events) and any(w >= since and res == "✓" for w, res in st.events)]
    open_q = [line for line in c.read("teacher.md").splitlines()
              if line.startswith("| 20") and c.table_cells(line)[3] == ""]
    answered = [c.table_cells(line) for line in c.read("teacher.md").splitlines()
                if line.startswith("| 20") and c.table_cells(line)[3] != ""]
    right = sum(1 for cells in answered if cells[4].lower().startswith(("да", "tak", "✓")))

    def err(e: str) -> str:
        r = errors.get(e)
        return f"{e} {r[c.ERR_CLOZE_COL]} → {r[c.ERR_CLOZE_COL + 1]}" if r else e

    def g(gid: str) -> str:
        return f"{gid} {items[gid].short}"

    ratings = ratings_since(since)
    lines = [
        f"ПЕРИОД: {since or 'с начала'} → {datetime.now():%Y-%m-%d %H:%M}",
        f"СЕССИИ: {len(sessions_since(since))} · оценки: {', '.join(map(str, ratings)) or '—'}",
        "МЕТРИКИ: " + " · ".join(
            f"{k} {prev[k]}→{v}" if k in prev else f"{k} {v}" for k, v in now.items()),
        "НОВЫЕ ОШИБКИ: " + ("; ".join(err(e) for e in new_err) or "—"),
        "ПОВТОРИЛИСЬ: " + ("; ".join(err(e) for e in repeated) or "—"),
        "ТРЕНИРОВКИ (верно/всего): " + ("; ".join(f"{e} {ok}/{n}" for e, (ok, n) in trained.items()) or "—"),
        "ГРАММАТИКА ↻: " + ("; ".join(g(x) for x, st in stats.items() if st.status == "↻") or "—"),
        "ГРАММАТИКА – обходишь: " + ("; ".join(g(x) for x, st in stats.items() if st.status == "–") or "—"),
        "ГРАММАТИКА ✓ исправилось за период: " + ("; ".join(g(x) for x in g_fixed) or "—"),
        "ГРАММАТИКА ✓ всего: " + ("; ".join(g(x) for x, st in stats.items() if st.status == "✓") or "—"),
        "ПОВТОРЕНИЕ: " + srs.summary(),
        f"ВОПРОСЫ ОТКРЫТЫ (teacher.md): {len(open_q)}",
        f"ДОВЕРИЕ: преподаватель проверил {len(answered)} поправок Claude, верных {right}"
        + (f" ({right * 100 // len(answered)}%)" if answered else ""),
        "<!-- metrics: " + " ".join(f"{k}={v}" for k, v in now.items()) + " -->",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())

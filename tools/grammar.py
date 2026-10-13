"""Грамматический анализатор: статистика по 108 пунктам грамматики B2 и выбор следующего крючка.

Источник правды — reviews.md (события ✓ / ✗ / –) и errors.md (ошибка → пункт грамматики G).
`python3 tools/grammar.py` пересобирает grammar.md и печатает сводку.
"""
import random
import re
from dataclasses import dataclass, field

import common as c

SECTIONS = {"2.2.1": "Fleksja", "2.2.2": "Słowotwórstwo", "2.2.3": "Składnia", "2.2.4": "Stylistyka"}
HOOKABLE = {"Fleksja", "Słowotwórstwo", "Składnia"}
STATUS_ORDER = ["↻", "✗", "–", "✓", "∅"]
STATUS_TITLES = {
    "✓": "Говоришь правильно",
    "✗": "Ошибки",
    "↻": "Повторяются (✗ ≥ 2)",
    "–": "Обходишь (крючок был, конструкции не было)",
    "∅": "Не используешь",
}


@dataclass(frozen=True)
class Item:
    gid: str
    section: str
    path: str

    @property
    def label(self) -> str:
        """Путь от второго уровня («celownik › jako określenie czasownika › z przyimkiem») без маркеров;
        родитель выкидывается, если ребёнок его повторяет («odmiana rzeczowników» › «odmiana rzeczowników…»)."""
        parts = [re.sub(r"^(\d+\)|[a-z]\)|–|•)\s*", "", p).strip(" ,;.:") for p in self.path.split(" › ")[1:]]
        segs = parts[1:] if len(parts) > 1 else parts
        kept = [s for i, s in enumerate(segs)
                if i + 1 == len(segs) or not segs[i + 1].lower().startswith(" ".join(s.lower().split()[:2]))]
        return re.sub(r"\s+", " ", " › ".join(kept))

    @property
    def short(self) -> str:
        """Название пункта без примеров «(np.: …)»."""
        return re.sub(r"\s*\(np\..*$", "", self.label)


@dataclass
class Stats:
    events: list[tuple[str, str]] = field(default_factory=list)  # (когда, ✓/✗/–)
    speech_ok: bool = False  # был ли ✓ в живой речи (/b2, новые темы), а не только в упражнениях

    def count(self, mark: str) -> int:
        return sum(1 for _, r in self.events if r == mark)

    @property
    def last_when(self) -> str:
        return max((w for w, _ in self.events), default="")

    @property
    def mark(self) -> str:
        """Статус для показа: ✓* — верно пока только в упражнениях, в живой речи ещё не было."""
        return "✓*" if self.status == "✓" and not self.speech_ok else self.status

    @property
    def status(self) -> str:
        if not self.events:
            return "∅"
        meaningful = [r for _, r in sorted(self.events) if r in "✓✗"]
        if not meaningful:
            return "–"
        if meaningful[-1] == "✓":
            return "✓"
        return "↻" if self.count("✗") >= 2 else "✗"


def items() -> list[Item]:
    return [Item(f"G{i}", SECTIONS[path[:5]], path) for i, path in enumerate(c.grammar_leaves(), 1)]


def analyze() -> dict[str, Stats]:
    error_to_g = {r[0]: r[c.ERR_G_COL] for r in c.table_rows("errors.md")
                  if len(r) > c.ERR_G_COL and re.match(r"^G\d+$", r[c.ERR_G_COL])}
    stats = {it.gid: Stats() for it in items()}
    for row in c.review_rows():
        gid = row[c.REV_ID] if row[c.REV_ID] in stats else error_to_g.get(row[c.REV_ID])
        result = row[c.REV_RESULT][:1]
        if gid in stats and result in "✓✗–":
            stats[gid].events.append((row[c.REV_WHEN], result))
            if result == "✓" and row[4] == "в речи":
                stats[gid].speech_ok = True
    return stats


def section_coverage(all_items: list[Item], stats: dict[str, Stats]) -> dict[str, tuple[int, int]]:
    cover: dict[str, tuple[int, int]] = {}
    for name in SECTIONS.values():
        sec = [it for it in all_items if it.section == name]
        seen = sum(1 for it in sec if stats[it.gid].status != "∅")
        cover[name] = (seen, len(sec))
    return cover


def focus(all_items: list[Item], stats: dict[str, Stats], n: int = 3) -> list[Item]:
    """Кандидаты в крючок по Голдратту — слабое звено: сначала то, что обходишь,
    потом неиспользованное из раздела с самым низким покрытием (кроме Stylistyka)."""
    avoided = [it for it in all_items if stats[it.gid].status == "–"]
    cover = section_coverage(all_items, stats)
    # Stylistyka (стиль, композиция, спойность текста) в разговор крючком не встроить — она тренируется в письме (v5)
    unused = [it for it in all_items if stats[it.gid].status == "∅" and it.section in HOOKABLE]
    unused = random.sample(unused, len(unused))
    unused.sort(key=lambda it: cover[it.section][0] / cover[it.section][1])
    return (random.sample(avoided, len(avoided)) + unused)[:n]


def summary_line(all_items: list[Item], stats: dict[str, Stats]) -> str:
    seen = sum(1 for s in stats.values() if s.status != "∅")
    repeating = [f"{it.gid} {it.short}" for it in all_items if stats[it.gid].status == "↻"]
    nxt = focus(all_items, stats, 1)
    line = f"грамматика {seen}/{len(all_items)}"
    if repeating:
        line += " · повторяются: " + "; ".join(repeating)
    if nxt:
        line += f" · в фокусе: {nxt[0].gid} {nxt[0].short}"
    return line


def render(all_items: list[Item], stats: dict[str, Stats]) -> str:
    by_status = {s: [it for it in all_items if stats[it.gid].status == s] for s in STATUS_ORDER}
    cover = section_coverage(all_items, stats)
    seen = len(all_items) - len(by_status["∅"])
    out = [
        "# Грамматика B2 — статистика",
        "",
        "Собирается автоматически: `python3 tools/grammar.py`. Руками не править — источник правды "
        "[reviews.md](reviews.md) и [errors.md](errors.md). Список пунктов — раздел 2.2 "
        "[стандарта B2](sources/b2-standard.md).",
        "",
        f"**Встречалось {seen}/{len(all_items)}** · " + " · ".join(
            f"{s} {len(by_status[s])}" for s in STATUS_ORDER),
        "",
        "✓* — верно пока только в упражнениях: в живой речи ещё не было — при неоднозначности смотреть глазами.",
        "",
        "**По разделам:** " + " · ".join(f"{name} {a}/{b}" for name, (a, b) in cover.items()),
        "",
        "**В фокусе — следующие крючки:** " + " · ".join(
            f"{it.gid} {it.short}" for it in focus(all_items, stats)),
        "",
    ]
    for s in STATUS_ORDER[:-1]:
        if by_status[s]:
            out.append(f"## {s} {STATUS_TITLES[s]}")
            out.append("")
            for it in by_status[s]:
                st = stats[it.gid]
                star = "  *(пока только в упражнениях)*" if st.mark == "✓*" else ""
                out.append(f"- **{it.gid}** {it.short} — ✓ {st.count('✓')} · ✗ {st.count('✗')} · – {st.count('–')}{star}")
            out.append("")
    out += ["## Все 108 пунктов", "", "| G | раздел | пункт | статус | ✓ | ✗ | – | последний раз |",
            "|---|---|---|---|---|---|---|---|"]
    for it in all_items:
        st = stats[it.gid]
        out.append(f"| {it.gid} | {it.section} | {it.label} | {st.mark} | {st.count('✓')} | "
                   f"{st.count('✗')} | {st.count('–')} | {st.last_when} |")
    return "\n".join(out) + "\n"


def main() -> None:
    all_items = items()
    stats = analyze()
    (c.ROOT / "grammar.md").write_text(render(all_items, stats), encoding="utf-8")
    print(summary_line(all_items, stats))


if __name__ == "__main__":
    main()

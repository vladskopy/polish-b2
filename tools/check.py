"""Проверка правды по словарю: каждую словоформу прогоняет через Morfeusz 2 (словарь SGJP, IPI PAN).

Показывает лемму и грамматику формы; формы, которых нет в словаре, помечает «?». Не оценивает,
уместна ли форма в предложении — только существует ли она и что это за форма.

    .venv/bin/python tools/check.py "Zapytałem trzy osoby, czy mają ładowarkę."
    .venv/bin/python tools/check.py --audit      # ответы, контексты и примеры из errors.md / words.md
"""
import re
import sys

import morfeusz2

import common as c

POS = {"subst": "сущ", "depr": "сущ", "adj": "прил", "adja": "прил", "adjp": "прил", "adv": "нареч",
       "num": "числ", "ppron12": "мест", "ppron3": "мест", "siebie": "мест", "fin": "глаг", "bedzie": "глаг",
       "praet": "глаг прош", "impt": "повел", "inf": "инф", "imps": "безл -no/-to", "ger": "отглаг сущ",
       "pact": "прич действ", "ppas": "прич страд", "pcon": "дееприч", "pant": "дееприч прош",
       "prep": "предлог", "conj": "союз", "comp": "союз", "qub": "частица", "winien": "глаг", "pred": "предик",
       "aglt": "связка -em/-eś", "interj": "межд", "brev": "сокращ"}
TAGS = {"sg": "ед", "pl": "мн", "nom": "им.п", "gen": "род.п", "dat": "дат.п", "acc": "вин.п", "inst": "твор.п",
        "loc": "предл.п", "voc": "зват.п", "m1": "м.р лич", "m2": "м.р одуш", "m3": "м.р", "f": "ж.р", "n": "ср.р",
        "imperf": "несов", "perf": "сов", "com": "сравн", "sup": "превосх"}
WORD = re.compile(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+(?:-[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)*")

_morf = morfeusz2.Morfeusz()


def describe(tag: str) -> str:
    """'subst:pl:gen:n:col' → 'сущ · мн · род.п · ср.р'; варианты через точку в тегах ('m2.m3') — через '/'."""
    head, *rest = tag.split(":")
    parts = [POS.get(head, head)]
    for r in rest:
        names = [TAGS[v] for v in r.split(".") if v in TAGS]
        if names:
            parts.append("/".join(dict.fromkeys(names)))
    return " · ".join(parts)


def analyse(word: str) -> list[tuple[str, str]]:
    """[(лемма, описание)] без повторов; пустой список — формы нет в словаре."""
    out: list[tuple[str, str]] = []
    for _, _, (_, lemma, tag, _, _) in _morf.analyse(word):
        if tag == "ign":
            return []
        item = (lemma.split(":")[0], describe(tag))
        if item not in out:
            out.append(item)
    return out


def check_text(text: str) -> tuple[list[str], list[str]]:
    """Строки отчёта и список слов, которых нет в словаре."""
    lines, unknown = [], []
    for word in dict.fromkeys(WORD.findall(text)):
        found = analyse(word)
        if not found:
            unknown.append(word)
            lines.append(f"  ? {word} — нет в словаре")
        else:
            variants = " | ".join(f"{lemma}: {desc}" for lemma, desc in found[:4])
            lines.append(f"  ✓ {word} ← {variants}")
    return lines, unknown


def audit() -> int:
    """Прогоняет ответы и контексты ошибок и примеры слов. Возвращает число строк с неизвестными словами."""
    sources = [(r[0], f"{r[c.ERR_CLOZE_COL + 1]} · {r[c.ERR_CONTEXT_COL]}") for r in c.table_rows("errors.md")]
    sources += [(r[0], f"{r[1]} · {r[2]}") for r in c.table_rows("words.md")]
    flagged = 0
    for rid, text in sources:
        _, unknown = check_text(text)
        if unknown:
            flagged += 1
            print(f"{rid}: нет в словаре — {', '.join(unknown)}")
    print(f"Проверено записей: {len(sources)} · с неизвестными словами: {flagged} "
          "(имена собственные и иностранные слова — норма)")
    return flagged


def main() -> None:
    args = sys.argv[1:]
    if args == ["--audit"]:
        audit()
        return
    text = " ".join(args) if args else sys.stdin.read()
    lines, unknown = check_text(text)
    print("\n".join(lines))
    print(f"ИТОГ: слов {len(lines)} · нет в словаре: {', '.join(unknown) if unknown else '—'}")


if __name__ == "__main__":
    main()

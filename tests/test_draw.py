import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import common  # noqa: E402
import draw  # noqa: E402
import grammar  # noqa: E402

ERR = "| E{n} | 4.4 | t | a ___ (b) | b | ctx | r | {g} | {count} | 0 | 2026-10-12 | открыта |"
REVIEWS = "| когда | режим | id | что | формат | результат | заметка |\n|---|---|---|---|---|---|---|\n"


def test_all_122_subtopics_are_parsed(tmp_path, monkeypatch) -> None:
    template = common.ROOT / ".claude" / "skills" / "b2" / "templates" / "topics.md"
    (tmp_path / "topics.md").write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    done, todo = draw.subtopics()
    assert (len(done), len(todo)) == (0, 122)


def test_grammar_has_108_items_in_four_sections() -> None:
    items = grammar.items()
    assert len(items) == 108
    assert {it.section for it in items} == {"Fleksja", "Słowotwórstwo", "Składnia", "Stylistyka"}
    assert items[67].gid == "G68" and "dzięki" in items[67].label


def test_table_rows_reads_only_id_rows(tmp_path, monkeypatch) -> None:
    (tmp_path / "errors.md").write_text("| id | тема |\n|---|---|\n" + ERR.format(n=1, g="G1", count=1) + "\n",
                                        encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert [r[0] for r in common.table_rows("errors.md")] == ["E1"]


def test_sessions_done_counts_dated_headings(tmp_path, monkeypatch) -> None:
    (tmp_path / "log.md").write_text(
        "# Журнал\n\n```\n## ГГГГ-ММ-ДД\n```\n## 2026-10-13 08:10 · скилл v0.1\n## 2026-10-14 19:00 · скилл v0.1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(common, "ROOT", tmp_path)
    assert draw.sessions_done() == 2


def test_grammar_status_from_reviews_and_error_mapping(tmp_path, monkeypatch) -> None:
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "b2-standard.md").write_text(
        (common.ROOT / "sources" / "b2-standard.md").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "errors.md").write_text("\n".join([ERR.format(n=1, g="G84", count=2),
                                                   ERR.format(n=2, g="—", count=1)]) + "\n", encoding="utf-8")
    (tmp_path / "reviews.md").write_text(REVIEWS + "\n".join([
        "| 2026-10-12 | /polski | E1 | x | в речи | ✗ | |",
        "| 2026-10-13 | /polski | E1 | x | в речи | ✗ | |",
        "| 2026-10-12 | /polski | E2 | x | в речи | ✗ | |",
        "| 2026-10-12 | /polski | G68 | x | в речи | ✓ | |",
        "| 2026-10-13 | /polski | G87 | x | в речи | – | |",
        "| 2026-10-12 | /polski | G62 | x | в речи | ✗ | |",
        "| 2026-10-14 | /powtorka | G62 | x | пропуск | ✓ | |",
    ]) + "\n", encoding="utf-8")
    monkeypatch.setattr(common, "ROOT", tmp_path)
    stats = grammar.analyze()
    assert stats["G84"].status == "↻"   # две ошибки через E1
    assert stats["G68"].status == "✓"
    assert stats["G87"].status == "–"   # крючок обошёл
    assert stats["G62"].status == "✓"   # последняя попытка верная
    assert stats["G62"].mark == "✓*"    # но только в упражнении, не в речи
    assert stats["G68"].mark == "✓"
    assert stats["G1"].status == "∅"
    assert grammar.focus(grammar.items(), stats, 1)[0].gid == "G87"  # обход — первым в фокус

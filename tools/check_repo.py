"""Гигиена репозитория: битые ссылки, личное, лишние файлы. Запускается в CI на каждом пуше.

    .venv/bin/python tools/check_repo.py
Ошибки — список и код выхода 1.
"""
import posixpath
import re
import subprocess
import sys

import common  # noqa: F401  — UTF-8 вывод на Windows

# Файлы, которые пишутся для корня пакета/проекта, хотя лежат глубже
ROOT_RELATIVE = ("pack/README.md", ".claude/skills/b2/templates/")
# Личное и рабочие заметки автора — только локально (.gitignore)
PRIVATE = {"profile.md", "errors.md", "words.md", "reviews.md", "log.md", "topics.md", "grammar.md",
           "teacher.md", "teacher-log.md", "README.md", "frame.md", "decisions.md", "backlog.md", "mvp.md",
           "architecture.md"}
PRIVATE_DIRS = ("jtbd/", "research/", "dist/", ".venv/")
FORBIDDEN = re.compile(r"decisions\.md|frame\.md|backlog\.md|mvp\.md|architecture\.md|lessons\.md|tasks/todo\.md"
                       r"|\bjtbd/|research/\d|Raphinh|паспорт|белорус|skopiuk|vladislav|@gmail\.com", re.I)
SKIP_FORBIDDEN = {".gitignore", "tools/pack.py", "tools/check_repo.py"}
LINK = re.compile(r"\]\(([^)\s]+)\)")


def tracked() -> list[str]:
    # отслеживаемые + новые неигнорируемые — то, что уйдёт в коммит после `git add -A`
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True, check=True).stdout
    return out.split()


def problems(files: list[str]) -> list[str]:
    found = []
    known = set(files)
    for f in files:
        d = posixpath.dirname(f)
        while d:
            known.add(d)
            d = posixpath.dirname(d)
    for f in files:
        if f in PRIVATE or f.startswith(PRIVATE_DIRS):
            found.append(f"личный или рабочий файл в репозитории: {f}")
    for f in files:
        try:
            text = open(f, encoding="utf-8").read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue
        if f not in SKIP_FORBIDDEN:
            for m in FORBIDDEN.finditer(text):
                found.append(f"личное или ссылка на рабочий файл: {f}: «{m.group(0)}»")
        if not f.endswith(".md"):
            continue
        base = "" if f.startswith(ROOT_RELATIVE) else posixpath.dirname(f)
        for m in LINK.finditer(text):
            link = m.group(1).split("#")[0]
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue
            target = posixpath.normpath(posixpath.join(base, link)).rstrip("/")
            if target not in known:
                found.append(f"битая ссылка: {f} → {m.group(1)}")
    return found


def main() -> None:
    found = problems(tracked())
    for p in found:
        print("✗", p)
    print(f"ИТОГ: проблем {len(found)}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()

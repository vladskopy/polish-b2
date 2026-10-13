"""Собирает пакет Polski B2 для других: только система, без личных данных.

    .venv/bin/python tools/pack.py
→ dist/polish-b2-v<версия>.tar.gz, dist/polish-b2-install.sh (один файл: архив внутри, base64)
  и .github/README.md — страница репозитория из pack/README.md (один источник текста).
"""
import base64
import io
import re
import tarfile
from pathlib import Path

import common  # noqa: F401  — UTF-8 вывод на Windows (иначе «КБ» роняет сборку)

ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.0"
DIST = ROOT / "dist"
INCLUDE = [
    ".claude/skills/b2", ".claude/skills/powtorka", ".claude/skills/nauczyciel",
    "tools", "tests", "parts", "tasks/systemantics-check.md", "CHANGELOG.md", "JTBD.md",
    "sources/b2-standard.md", "sources/README.md", "LICENSE",
]
RENAME = {"pack/README.md": "README.md", "pack/install.sh": "install.sh"}
PRIVATE = {"profile.md", "errors.md", "words.md", "reviews.md", "log.md", "topics.md", "grammar.md",
           "teacher.md", "teacher-log.md", "frame.md", "decisions.md", "backlog.md", "mvp.md", "architecture.md"}
SKIP_PARTS = {"__pycache__", ".pytest_cache"}


def files() -> list[tuple[Path, str]]:
    """[(источник, путь в пакете)]."""
    out = []
    for item in INCLUDE:
        src = ROOT / item
        paths = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
        out += [(p, p.relative_to(ROOT).as_posix()) for p in paths if not SKIP_PARTS & set(p.parts)]
    out += [(ROOT / src, dst) for src, dst in RENAME.items()]
    return out


def github_readme() -> Path:
    """pack/README.md написан для корня пакета; на GitHub он лежит в .github/ — относительные ссылки получают «../»."""
    text = (ROOT / "pack/README.md").read_text(encoding="utf-8")
    text = re.sub(r"\]\((?!https?://|#|\.\./)([^)]+)\)", r"](../\1)", text)
    badge = "[![ci](https://github.com/vladskopy/polish-b2/actions/workflows/ci.yml/badge.svg)]" \
            "(https://github.com/vladskopy/polish-b2/actions/workflows/ci.yml)"
    title, rest = text.split("\n", 1)
    note = "<!-- Сгенерировано tools/pack.py из pack/README.md — править там. -->"
    out = ROOT / ".github/README.md"
    out.write_text(f"{title}\n\n{badge}\n{note}\n{rest}", encoding="utf-8", newline="\n")
    return out


def build() -> tuple[Path, Path]:
    pairs = files()
    leaked = [a for _, a in pairs if "/" not in a and a in PRIVATE]
    assert not leaked, f"в пакет попали личные файлы: {leaked}"
    DIST.mkdir(exist_ok=True)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, arcname in pairs:
            data = path.read_bytes()
            info = tarfile.TarInfo(arcname)
            info.size = len(data)
            info.mode = 0o755 if arcname.endswith(".sh") else 0o644
            tar.addfile(info, io.BytesIO(data))
    github_readme()
    archive = DIST / f"polish-b2-v{VERSION}.tar.gz"
    archive.write_bytes(buf.getvalue())
    payload = base64.encodebytes(buf.getvalue()).decode("ascii")
    installer = DIST / "polish-b2-install.sh"
    installer.write_text(f"""#!/usr/bin/env bash
# Polski B2 v{VERSION} — установщик одним файлом. Использование:
#   bash polish-b2-install.sh [папка]          (по умолчанию ./polish-b2)
#   curl -fsSL <адрес>/polish-b2-install.sh | bash -s -- [папка]
# Повторный запуск в ту же папку обновляет систему; твои данные (profile.md, журналы) не трогаются.
set -euo pipefail
TARGET="${{1:-polish-b2}}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
base64 --decode > "$TMP/polish-b2.tar.gz" <<'PAYLOAD'
{payload}PAYLOAD
mkdir -p "$TARGET"
(cd "$TARGET" && tar -xzf "$TMP/polish-b2.tar.gz")  # без -C: в Git Bash путь с «C:» tar принял бы за удалённый хост
echo "Polski B2 v{VERSION} распакован в $TARGET"
bash "$TARGET/install.sh"
""", encoding="utf-8", newline="\n")  # bash не переносит CRLF — важно при сборке на Windows
    installer.chmod(0o755)
    return archive, installer


if __name__ == "__main__":
    archive, installer = build()
    print(f"{archive.relative_to(ROOT)} · {archive.stat().st_size // 1024} КБ · файлов {len(files())}")
    print(f"{installer.relative_to(ROOT)} · {installer.stat().st_size // 1024} КБ")

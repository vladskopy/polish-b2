#!/usr/bin/env bash
# Готовит распакованный Polski B2: Python-окружение, зависимости, проверка. Данные пользователя не трогает.
# macOS, Linux; Windows — в Git Bash (он есть вместе с Claude Code).
set -euo pipefail
cd "$(dirname "$0")"

echo "→ Python-окружение в .venv"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 .venv -q --allow-existing
  VIRTUAL_ENV="$PWD/.venv" uv pip install -q -r tools/requirements.txt
elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
  "$(command -v python3 || command -v python)" -m venv .venv
  PIP_PY=".venv/bin/python"; [ -x "$PIP_PY" ] || PIP_PY=".venv/Scripts/python.exe"
  "$PIP_PY" -m pip install -q -r tools/requirements.txt \
    || echo "  ⚠ не все зависимости встали — проверка словарём (morfeusz2) может не работать. Поставь uv и запусти install.sh ещё раз."
else
  echo "  ✗ нужен Python 3.10+ или uv (https://docs.astral.sh/uv/)"; exit 1
fi

# Windows: venv кладёт Python в .venv/Scripts — скиллы зовут .venv/bin/python, поэтому кладём туда переходник
if [ ! -e .venv/bin/python ] && [ -x .venv/Scripts/python.exe ]; then
  mkdir -p .venv/bin
  printf '#!/usr/bin/env bash\nexport PYTHONUTF8=1\nexec "$(dirname "$0")/../Scripts/python.exe" "$@"\n' > .venv/bin/python
  chmod +x .venv/bin/python
fi

echo "→ Проверка"
if .venv/bin/python -m pytest -q tests >/dev/null 2>&1; then echo "  тесты: ок"; else echo "  ⚠ тесты не прошли: .venv/bin/python -m pytest tests"; fi
.venv/bin/python tools/draw.py --plan | grep -E "ПЕРВЫЙ ЗАПУСК|МАРШРУТ" | sed 's/^/  /'

cat <<DONE

Готово: $(pwd)
Дальше:
  cd "$(pwd)" && claude
  /b2
DONE

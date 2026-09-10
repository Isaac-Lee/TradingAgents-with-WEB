#!/bin/sh
set -eu

workspace_path=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_path="$workspace_path/.venv/bin/python"

if [ ! -x "$python_path" ]; then
    echo 'Create .venv and install the project first. See webapp/README.md.' >&2
    exit 1
fi

cd -- "$workspace_path"
exec "$python_path" -m webapp.server "$@"

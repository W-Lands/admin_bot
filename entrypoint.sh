#!/bin/bash

POETRY_VENV="$(poetry env info -p)"
export PATH="${PATH}:${POETRY_VENV}/bin"

poetry run python -m wlands_admin_bot.main
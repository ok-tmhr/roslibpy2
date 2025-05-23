#!/bin/bash

PYTHON=3.13
curl -LsSf https://astral.sh/uv/install.sh | sh

uv python install $PYTHON
uv python pin $PYTHON
uv venv

echo 'eval "$(uv generate-shell-completion bash)"' >>~/.bashrc

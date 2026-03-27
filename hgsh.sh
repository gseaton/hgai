#!/bin/bash
echo Running hgsh...
source .venv/bin/activate
pip install -r requirements.txt
python -m shell.hgai_shell "$@"
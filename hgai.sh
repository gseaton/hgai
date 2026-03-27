#!/bin/bash
echo Running hgai server...
source .venv/bin/activate
pip install -r requirements.txt 1>/dev/null 2>/dev/null
python -m hgai.main "$@"

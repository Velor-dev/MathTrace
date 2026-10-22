"""Provision the pinned local Ubuntu bubblewrap binary without root access."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mathtrace.sandbox import invoke

if __name__ == '__main__':
    print(json.dumps(invoke({'operation': 'provision'}, 180), indent=2))

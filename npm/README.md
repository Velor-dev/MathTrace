# MathTrace project installer

This is a local, unpublished package. The included LICENSE states the proprietary free-use terms.
Require Node 22+ and Python 3.11+ with working venv/pip. No Python or coding host
is installed automatically. Production npm dependencies and lifecycle installation
hooks are unnecessary. Run the packaged binary in the target project; choose one
numbered harness, or use `--harness <id>` for automation. EOF/Ctrl+C cancels.

Build with `python tools/build_npm.py`, then use `npm pack` in the returned package
directory. Local archive execution requires no registry publication or global
MathTrace installation. The package is private and publication is disabled.

Public project author/developer: Velor-dev (https://github.com/Velor-dev).
Copyright © 2026 Velor-dev. See LICENSE beside this
README for complete permissions and separate upstream terms. Installed copies
are available under .mathtrace/docs/ in the target project. Exclude MathTrace
software assets from public project releases and reinstall from the official
distribution; free commercial use does not grant general redistribution rights.

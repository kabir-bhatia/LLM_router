"""Smart Model Router package."""

import sys

# Windows consoles default to a legacy codepage (cp1252) that can't encode the
# emoji used in log lines throughout this codebase (router.py, semantic_cache.py,
# etc.), which crashes any process the moment one of those lines prints --
# including when stdout is redirected to a file, as eval scripts do. Fixed once
# here rather than per entry point, since every module in this package imports
# through src/, guaranteeing this runs before any of those prints can fire.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

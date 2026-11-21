import platform
import sys

# Windows workaround: platform.uname() can hang on WMI (sklearn/sqlalchemy call it at import time).
if sys.platform == "win32":
    platform._wmi = None

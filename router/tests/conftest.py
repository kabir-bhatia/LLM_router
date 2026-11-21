import platform
import sys

# Windows workaround: platform.uname() can hang on WMI; fall back to environment variables.
if sys.platform == "win32":
    platform._wmi = None

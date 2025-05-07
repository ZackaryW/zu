
import os
import platform


ZU_DATA = os.path.join(os.path.expanduser("~"), ".zu")

ZU_UTIL_PKG_STORE = os.path.join(ZU_DATA, "repos")
os.makedirs(ZU_UTIL_PKG_STORE, exist_ok=True)

# global
if platform.system() == "Windows":
    ZU_GLOBAL_DATA = os.path.join("C:", "ProgramData", "zu")
else:
    ZU_GLOBAL_DATA = os.path.join("/", "usr", "local", "zu")

ZU_GLOBAL_REPO_STORE = os.path.join(ZU_GLOBAL_DATA, "repos")
os.makedirs(ZU_GLOBAL_REPO_STORE, exist_ok=True)

PKG_GIT_URL = "https://github.com/zackaryuu/{pkg_name}.git"

ZU_INTERNAL_COMMANDS = [
    "get",
    "list",
    "remove",
    "purge",  
    "index"
]

ZU_REPO_UPDATE_RECORD = os.path.join(ZU_UTIL_PKG_STORE, "update_record.json")


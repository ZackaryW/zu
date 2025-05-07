import os
import shutil
import time

def robust_remove_directory(path: str) -> bool:
    """
    Robustly remove a directory, handling Windows-specific file locking issues.
    Returns True if successful, False otherwise.
    """
    if not os.path.exists(path):
        return True

    # First try normal removal
    try:
        shutil.rmtree(path)
        return True
    except PermissionError:
        pass

    # If normal removal fails, try to force remove
    def on_rm_error(func, path, exc_info):
        # Try to make the file writable
        try:
            os.chmod(path, 0o777)
        except:
            pass
        # Try to remove again
        try:
            os.unlink(path)
        except:
            pass

    # Try removal with error handler
    try:
        shutil.rmtree(path, onerror=on_rm_error)
    except:
        pass

    # If still exists, try one more time with a small delay
    if os.path.exists(path):
        time.sleep(0.1)
        try:
            shutil.rmtree(path, onerror=on_rm_error)
        except:
            pass

    return not os.path.exists(path) 
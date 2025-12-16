
import importlib
import sys
import subprocess

class Common:
    @staticmethod
    def ensure_packages(packages, append_output_func=None):
        """Ensure the given package names are importable; if not, install via pip.

        `packages` should be an iterable of importable module names (or pip names).
        If the list is empty, this is a no-op and returns True.

        If `append_output_func` is provided it will be called with status messages
        (a single string argument). The function returns True on success, False on failure.
        """
        if not packages:
            msg = "No packages requested; nothing to do.\n"
            if append_output_func:
                try:
                    append_output_func(msg)
                except Exception:
                    pass
            else:
                print(msg, file=sys.stderr)
            return True

        missing = []
        for pkg in packages:
            try:
                importlib.import_module(pkg)
            except Exception:
                missing.append(pkg)

        if not missing:
            return True

        total = len(missing)
        for idx, pkg in enumerate(missing, start=1):
            start_msg = f"Installing {pkg} ({idx}/{total})\n"
            if append_output_func:
                try:
                    append_output_func(start_msg)
                except Exception:
                    pass
            else:
                print(start_msg, file=sys.stderr)

            cmd = [sys.executable, "-m", "pip", "install", pkg]
            try:
                # capture output so GUI can display it
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                out = proc.stdout or ""
                if append_output_func and out:
                    try:
                        append_output_func(out)
                    except Exception:
                        pass

                if proc.returncode != 0:
                    err = f"Failed to install {pkg} ({idx}/{total}): exit {proc.returncode}\n"
                    if append_output_func:
                        try:
                            append_output_func(err)
                        except Exception:
                            pass
                    else:
                        print(err, file=sys.stderr)
                    return False

                # verify import after install
                try:
                    importlib.import_module(pkg)
                except Exception:
                    warn = f"Package {pkg} installed but import failed ({idx}/{total}).\n"
                    if append_output_func:
                        try:
                            append_output_func(warn)
                        except Exception:
                            pass
                    else:
                        print(warn, file=sys.stderr)
                    return False

                ok = f"Installed {pkg} ({idx}/{total}).\n"
                if append_output_func:
                    try:
                        append_output_func(ok)
                    except Exception:
                        pass
                else:
                    print(ok, file=sys.stderr)

            except Exception as e:
                err = f"Failed to install {pkg} ({idx}/{total}): {e}\n"
                if append_output_func:
                    try:
                        append_output_func(err)
                    except Exception:
                        pass
                else:
                    print(err, file=sys.stderr)
                return False

        return True
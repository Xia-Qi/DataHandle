
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

    @staticmethod
    def detect_encoding(path, sample_size=65536):
        """Detect a file's text encoding.

        Tries `charset-normalizer` first (if installed), then falls back to
        `chardet` if available. If neither is present, checks for common BOMs
        and otherwise returns 'utf-8' as a sensible default.

        Returns the detected encoding name as a string (never None).
        """
        # Read a sample of the file in binary mode
        try:
            with open(path, 'rb') as f:
                sample = f.read(sample_size)
        except Exception:
            return 'utf-8'

        # BOM checks (deterministic)
        if sample.startswith(b'\xef\xbb\bf'):
            return 'utf-8-sig'
        if sample.startswith(b'\xff\xfe') or sample.startswith(b'\xfe\xff'):
            return 'utf-16'

        # Try charset-normalizer if available
        try:
            from charset_normalizer import from_bytes
            try:
                results = from_bytes(sample)
                best = results.best()
                if best and getattr(best, 'encoding', None):
                    return best.encoding
            except Exception:
                pass
        except Exception:
            pass

        # Fallback to chardet if available
        try:
            import chardet
            info = chardet.detect(sample)
            enc = info.get('encoding')
            if enc:
                return enc
        except Exception:
            pass

        # Last resort: assume utf-8
        return 'utf-8'
#!/usr/bin/env python3
import argparse
import csv
import datetime
import sys
import subprocess
import importlib
from time import sleep


def open_with_fallback(path):
    encs_strict = ("utf-8", "utf-8-sig", "gbk", "cp1252", "iso-8859-1")
    for enc in encs_strict:
        try:
            # open with newline='' to preserve original CR/LF characters
            f = open(path, "r", encoding=enc, errors="replace", newline='')
            return f, enc, False
        except Exception:
            continue


def ensure_packages(packages):
    """Ensure the given package names are importable; if not, install via pip.

    `packages` should be an iterable of importable module names (or pip names).
    If the list is empty, this is a no-op.
    """
    if not packages:
        print("Packages are ok, continue.", file=sys.stderr)
        return
    missing = []
    for pkg in packages:
        try:
            importlib.import_module(pkg)
        except Exception:
            missing.append(pkg)
    if not missing:
        return
    print(f"Installing missing packages: {', '.join(missing)}", file=sys.stderr)
    cmd = [sys.executable, "-m", "pip", "install"] + missing
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Failed to install packages: {e}", file=sys.stderr)
        sys.exit(4)

def compute_max_lengths(rows, ncols):
    max_lens = [0] * ncols
    for r in rows:
        for i in range(ncols):
            val = r[i] if i < len(r) else ""
            trimmed = val.strip()
            l = len(trimmed)
            if l > max_lens[i]:
                max_lens[i] = l
    return max_lens


def main():
    p = argparse.ArgumentParser(description="Generate F001_... computed lines from TSV")
    p.add_argument("file", help="Input TSV file (path required)")
    p.add_argument("-o", "--output", help="Write results to this file (default: stdout)")
    p.add_argument("--install-missing", action="store_true", help="Attempt to install missing Python packages before running")
    args = p.parse_args()

    if getattr(args, 'install_missing', False):
        # Determine external packages to check here if you have any; currently
        # this script uses only standard library modules, so pass an empty list.
        ensure_packages([])

    try:
        f, enc, replaced = open_with_fallback(args.file)
    except Exception as e:
        print(f"Failed to open '{args.file}': {e}", file=sys.stderr)
        sys.exit(2)

    with f:
        # Read raw text without newline translation and split only on CRLF ("\r\n").
        # This ensures we treat '\r\n' as the sole line delimiter.
        raw_text = f.read()
        raw_lines = raw_text.split('\r\n')

    # Validate each physical line: if any column has an odd number of quotes
    # or newline characters, mark it as an error. Collect all errors and
    # report them after checking the entire file.
    errors = []
    for lineno, line in enumerate(raw_lines, start=1):
        cols = line.split('\t')
        for colno, col in enumerate(cols, start=1):
            quote_count = col.count('"')
            newline_count = col.count('\n') + col.count('\r')
            if (quote_count % 2 == 1) or (newline_count > 1):
                errors.append(f"Line {lineno}, Column {colno}: quotes={quote_count}, newlines={newline_count}")

    if errors:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"{now} - {len(errors)} errors detected\n"
        # If an output file was specified, write the error report there.
        if getattr(args, 'output', None):
            try:
                with open(args.output, 'w', encoding='utf-8') as fo:
                    fo.write(header)
                    fo.write('Error: malformed lines detected:\n')
                    for e in errors:
                        fo.write(e + '\n')
                print(f"Wrote error report to '{args.output}'", file=sys.stderr)
            except Exception as e:
                print(f"Failed to write error report to '{args.output}': {e}", file=sys.stderr)
        else:
            print(header, file=sys.stderr)
            print("Error: malformed lines detected:\n", file=sys.stderr)
            for e in errors:
                print(e, file=sys.stderr)
        sys.exit(5)

    if 'replaced' in locals() and replaced:
        print(f"Warning: opened file using encoding '{enc}' with undecodable bytes replaced.", file=sys.stderr)

    # Now parse the tab-separated data from the validated raw lines
    reader = csv.reader(raw_lines, delimiter='\t')
    rows = [r for r in reader]

    if not rows:
        print("No rows found in file.", file=sys.stderr)
        sys.exit(1)

    headers = rows[0]
    data_rows = rows[1:]

    # determine number of columns as the max between header length and any data row
    ncols = len(headers)
    for r in data_rows:
        if len(r) > ncols:
            ncols = len(r)

    max_lens = compute_max_lengths(data_rows, ncols)

    results = []
    for i in range(ncols):
        header = headers[i].strip() if i < len(headers) else f"COL{i+1}"
        # escape quotes in header for safety
        header_safe = header.replace('"', '\\"').replace(" ","_")
        idx = i + 1
        idx_padded = f"{idx:03d}"
        maxlen = max_lens[i] if i < len(max_lens) else 0
        # Build the exact requested string with replacements
        line = f"F{idx_padded}_{header_safe} computed \nsubstr( alltrim( split( Full_Record , chr( 009 ), {idx_padded} , chr( 34 ) ) ) , 1 , {maxlen} )"
        # Emit progress so external UIs can display processing progress
        try:
            print(f"PROGRESS {idx}/{ncols}", flush=True)
        except Exception:
            pass
        results.append(line)
        #sleep(1)  # Simulate a delay for demonstration purposes

    out_text = "\n".join(results)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fo:
                fo.write(out_text)
            print(f"Wrote {len(results)} lines to '{args.output}'")
        except Exception as e:
            print(f"Failed to write output: {e}", file=sys.stderr)
            sys.exit(3)
    else:
        print(out_text)


if __name__ == '__main__':
    main()

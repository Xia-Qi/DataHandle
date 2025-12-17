#!/usr/bin/env python3
import argparse
import csv
import datetime
import sys
import subprocess
import importlib
from time import sleep
from common import Common

# Try to open the file with multiple encodings, returning the first that works
def open_with_fallback(path):
    encs_strict = ("utf-8", "utf-8-sig", "gbk", "cp1252", "iso-8859-1")
    for enc in encs_strict:
        try:
            # open with newline='' to preserve original CR/LF characters
            # newline='' 禁用 Python 的通用换行符转换——读/写时不会把 \r\n、\r、\n 统一替换成 \n，也不会自动把 \n 转回平台默认行结束符。读到的内容保持原始字节解码后包含的真实 \r/\n 字符序列。
            # \r 回车；\n 换行；\t 制表符; \r\n 回车换行,Windows 行结束符
            f = open(path, "r", encoding=enc, errors="replace", newline='')
            return f, enc, False
        except Exception:
            continue


# Compute maximum lengths of trimmed values per column
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

def write_error_report(errors, output_path=None):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = f"{now} - {len(errors)} errors detected\n"
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as fo:
                fo.write(header)
                fo.write('Error: malformed lines detected:\n')
                for e in errors:
                    fo.write(e + '\n')
            print(f"Wrote error report to '{output_path}'", file=sys.stderr)
        except Exception as e:
            print(f"Failed to write error report to '{output_path}': {e}", file=sys.stderr)
    else:
        print(header, file=sys.stderr)
        print("Error: malformed lines detected:\n", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)

def main():
    p = argparse.ArgumentParser(description="Generate F001_... computed lines from TSV")
    p.add_argument("file", help="Input TSV file (path required)")
    p.add_argument("-o", "--output", help="Write results to this file (default: stdout)")
    p.add_argument("--install-missing", action="store_true", help="Attempt to install missing Python packages before running")
    args = p.parse_args()

    if getattr(args, 'install_missing', False):
        # Determine external packages to check here if you have any; currently
        # this script uses only standard library modules, so pass an empty list.
        Common.ensure_packages([])

    # Two-pass streaming approach (memory-friendly):
    # 1) First pass: use csv.reader to compute per-column max lengths and
    #    detect problematic fields (e.g. embedded newlines) while scanning.
    # 2) Second pass: reopen file and generate the output using computed widths.

    # detect encoding for the input file and use it for all file opens
    enc = Common.detect_encoding(args.file)

    try:
        # First pass: scan file to compute max lengths
        replaced = False
        errors = []
        with open(args.file, 'r', encoding=enc, errors='replace', newline='') as fh:
            reader = csv.reader(fh, delimiter='\t')
            try:
                headers = next(reader)
            except StopIteration:
                print("No rows found in file.", file=sys.stderr)
                sys.exit(1)

            ncols = len(headers)
            max_lens = [0] * ncols
            rowno = 1
            for row in reader:
                rowno += 1
                # mark if any replacement occurred during decoding
                for v in row:
                    if '\uFFFD' in v:
                        replaced = True
                # detect embedded newlines inside fields (treated as data)
                for colno, v in enumerate(row, start=1):
                    if '\n' in v or '\r' in v:
                        errors.append(f"Line {rowno}, Column {colno}: embedded newline in field")

                if len(row) > ncols:
                    extra = len(row) - ncols
                    max_lens.extend([0] * extra)
                    ncols = len(row)

                for i in range(ncols):
                    val = row[i] if i < len(row) else ""
                    trimmed = val.strip()
                    l = len(trimmed)
                    if l > max_lens[i]:
                        max_lens[i] = l

        if errors:
            write_error_report(errors)
            sys.exit(5)

    except csv.Error as e:
        print(f"CSV parse error: {e}", file=sys.stderr)
        sys.exit(5)
    except Exception as e:
        print(f"Failed to read '{args.file}': {e}", file=sys.stderr)
        sys.exit(2)

    # headers and max_lens already computed in first pass; ensure header list available
    # Re-open file briefly to re-read header (if needed for exact original header values)
    try:
        with open(args.file, 'r', encoding=enc, errors='replace', newline='') as fh:
            reader = csv.reader(fh, delimiter='\t')
            headers = next(reader)
    except Exception:
        # header should have been read in first pass; fallback to empty headers
        headers = [f"COL{i+1}" for i in range(len(max_lens))]

    results = []
    for i in range(len(max_lens)):
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

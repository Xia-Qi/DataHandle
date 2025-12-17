#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from tkinter import ttk
import threading
import subprocess
import sys
import os
import shlex
import re

from common import Common

def detect_imports(script_path):
    """Return a list of top-level imported module names from the given script.

    This is a best-effort parser: it looks for lines like `import X` and
    `from X import ...` and returns the base module `X`.
    """
    mods = []
    try:
        enc = Common.detect_encoding(script_path)
        with open(script_path, 'r', encoding=enc, errors='replace') as f:
            for line in f:
                line = line.strip()
                m = re.match(r'import\s+([a-zA-Z0-9_\.]+)', line)
                if m:
                    base = m.group(1).split('.')[0]
                    mods.append(base)
                    continue
                m = re.match(r'from\s+([a-zA-Z0-9_\.]+)\s+import', line)
                if m:
                    base = m.group(1).split('.')[0]
                    mods.append(base)
    except Exception:
        return []
    # unique while preserving order
    seen = set()
    out = []
    for m in mods:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out



SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'test.py')

class App:
    def __init__(self, root):
        self.root = root
        root.title('TSV Analyzer GUI')

        frm = tk.Frame(root)
        frm.pack(padx=8, pady=8, fill='x')

        tk.Label(frm, text='Input TSV:').grid(row=0, column=0, sticky='w')
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(frm, textvariable=self.input_var, width=60)
        self.input_entry.grid(row=0, column=1, padx=4)
        tk.Button(frm, text='Browse', command=self.browse_input).grid(row=0, column=2)

        tk.Label(frm, text='Output file (optional):').grid(row=1, column=0, sticky='w')
        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(frm, textvariable=self.output_var, width=60)
        self.output_entry.grid(row=1, column=1, padx=4)
        tk.Button(frm, text='Browse', command=self.browse_output).grid(row=1, column=2)

        self.install_var = tk.BooleanVar(value=False)
        tk.Checkbutton(frm, text='Install missing packages', variable=self.install_var).grid(row=2, column=1, sticky='w')

        self.run_btn = tk.Button(frm, text='Run', command=self.run)
        self.run_btn.grid(row=3, column=1, pady=6)

        # Progress bar
        self.progress = ttk.Progressbar(frm, orient='horizontal', length=400, mode='determinate')
        self.progress.grid(row=4, column=0, columnspan=3, pady=(6,0))
        self.progress_label = tk.Label(frm, text='0%')
        self.progress_label.grid(row=4, column=3, padx=(6,0))

        self.text = scrolledtext.ScrolledText(root, height=20, width=100)
        self.text.pack(padx=8, pady=(0,8), fill='both', expand=True)

        self.proc_thread = None

    def browse_input(self):
        p = filedialog.askopenfilename(filetypes=[('TSV files','*.txt;*.tsv'),('All files','*.*')])
        if p:
            self.input_var.set(p)

    def browse_output(self):
        p = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text files','*.txt'),('All files','*.*')])
        if p:
            self.output_var.set(p)

    def append(self, text):
        self.text.insert('end', text)
        self.text.see('end')
        # keep progress bar visible updates responsive
        self.root.update_idletasks()

    def set_progress(self, value, maximum=None):
        """Set progress bar value and update percent label.

        If maximum is provided, update the progress maximum as well.
        """
        try:
            if maximum is not None:
                self.progress.config(maximum=maximum)
            self.progress.config(value=value)
        except Exception:
            try:
                self.progress['value'] = value
            except Exception:
                pass
        # compute percentage
        try:
            maxv = float(self.progress['maximum'])
            pct = int((float(value) / maxv) * 100) if maxv else 0
        except Exception:
            pct = 0
        self.progress_label.config(text=f"{pct}%")
        self.root.update_idletasks()

    def run(self):
        infile = self.input_var.get().strip()
        if not infile:
            messagebox.showwarning('Input required', 'Please select an input TSV file')
            return
        if not os.path.isfile(SCRIPT_PATH):
            messagebox.showerror('Script missing', f"Can't find test.py at {SCRIPT_PATH}")
            return
        args = [sys.executable, SCRIPT_PATH, infile]
        out = self.output_var.get().strip()
        if out:
            args += ['-o', out]
        if self.install_var.get():
            # detect imports in test.py and attempt to install missing packages
            mods = detect_imports(SCRIPT_PATH)
            # skip standard library common modules that shouldn't be installed
            blacklist = {'sys','os','re','csv','argparse','subprocess','threading','tkinter','shlex','importlib','datetime'}
            to_check = [m for m in mods if m not in blacklist]
            if to_check:
                # configure progress bar for package installs
                self.progress.config(mode='determinate', maximum=len(to_check), value=0)
                def append_and_update(s):
                    self.append(s)
                    # If message indicates a package installed or in-progress, update progress
                    if 'Installing ' in s or 'installed.' in s:
                        try:
                            m = re.search(r"\((\d+)/(\d+)\)", s)
                            if m:
                                cur = int(m.group(1))
                                total = int(m.group(2))
                                self.set_progress(cur, maximum=total)
                            else:
                                # increment by 1
                                cur = min(int(self.progress['value']) + 1, int(self.progress['maximum']))
                                self.set_progress(cur)
                        except Exception:
                            try:
                                cur = min(int(self.progress['value']) + 1, int(self.progress['maximum']))
                                self.set_progress(cur)
                            except Exception:
                                pass

                ok = Common.ensure_packages(to_check, append_output_func=append_and_update)
                if not ok:
                    messagebox.showerror('Install failed', 'Failed to install required packages. See output for details.')
                    self.run_btn.config(state='normal')
                    return
                # reset progress bar and label
                self.set_progress(0, maximum=len(to_check))
            # also pass flag to the script in case it wants to handle installs itself
            args.append('--install-missing')

        # disable run button
        self.run_btn.config(state='disabled')
        self.text.delete('1.0', 'end')
        self.append('Running: ' + ' '.join(shlex.quote(a) for a in args) + '\n\n')

        def target():
            try:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)
            except Exception as e:
                self.root.after(0, lambda: (self.append(f'Failed to start process: {e}\n'), self.run_btn.config(state='normal')))
                return

            # show indeterminate progress while script runs
            self.root.after(0, lambda: self.progress.config(mode='indeterminate'))
            self.root.after(0, lambda: self.progress.start(10))

            prog_re = re.compile(r"PROGRESS\s+(\d+)/(\d+)")
            for line in proc.stdout:
                m = prog_re.search(line)
                if m:
                    try:
                        cur = int(m.group(1))
                        total = int(m.group(2))
                        # Stop any indeterminate animation first, then switch to determinate and update
                        def update_progress(c=cur, t=total):
                            try:
                                self.progress.stop()
                            except Exception:
                                pass
                            # switch to determinate and set value via helper
                            self.set_progress(c, maximum=t)
                        self.root.after(0, update_progress)
                    except Exception:
                        # fallback: just append if parsing fails
                        self.root.after(0, lambda l=line: self.append(l))
                else:
                    self.root.after(0, lambda l=line: self.append(l))
            proc.wait()
            code = proc.returncode

            # stop indeterminate progress
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.progress.config(mode='determinate', value=0))

            self.root.after(0, lambda: self.append(f"\nProcess exited with code {code}\n"))
            self.root.after(0, lambda: self.run_btn.config(state='normal'))

        self.proc_thread = threading.Thread(target=target, daemon=True)
        self.proc_thread.start()


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()


import json, os, shutil, subprocess, time, urllib.request, webbrowser
from pathlib import Path
from tkinter import Tk, Frame, Label, Text, Entry, END, BOTH, X, LEFT, RIGHT, Toplevel, messagebox, StringVar
from tkinter import ttk

BASE = Path(__file__).parent
CONFIG_FILE = BASE / "console_config.json"
REPORT_FILE = BASE / "diagnostics_report.txt"

def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

def http_ok(url):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as r:
            return 200 <= r.status < 400
    except Exception:
        return False

def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def visible(title, command, cwd):
    executable = command[0]
    args = command[1:]

    ps_args = ", ".join(ps_quote(arg) for arg in args)
    invoke = f"& {ps_quote(executable)}"
    if args:
        invoke += " " + " ".join(ps_quote(arg) for arg in args)

    script = (
        f"$Host.UI.RawUI.WindowTitle = {ps_quote(title)}; "
        f"Set-Location -LiteralPath {ps_quote(cwd)}; "
        f"{invoke}"
    )

    subprocess.Popen(
        [
            "powershell.exe",
            "-NoExit",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("0M3-G4-ARC Command Console v3")
        self.root.geometry("1120x760")
        self.root.configure(bg="#090a0c")
        self.cfg = load_config()

        self.system = StringVar(value="STANDBY")
        self.vars = {k: StringVar(value="UNCHECKED") for k in [
            "backend_path","frontend_path","python_path","npm_path",
            "ollama","backend","frontend","root_path"
        ]}

        self.build()
        self.health()
        self.root.after(4000, self.tick)

    def panel(self, parent):
        return Frame(parent,bg="#111419",highlightbackground="#2c323a",highlightthickness=1,padx=14,pady=14)

    def row(self, parent, label, var):
        r=Frame(parent,bg="#111419"); r.pack(fill=X,pady=3)
        Label(r,text=label,bg="#111419",fg="#d7dbe0",font=("Consolas",10),width=22,anchor="w").pack(side=LEFT)
        Label(r,textvariable=var,bg="#111419",fg="#d7aa54",font=("Consolas",10)).pack(side=RIGHT)

    def button(self, parent, text, cmd):
        ttk.Button(parent,text=text,style="C.TButton",command=cmd).pack(side=LEFT,padx=(0,8))

    def build(self):
        style=ttk.Style(); style.theme_use("clam")
        style.configure("C.TButton",background="#171b20",foreground="#d7dbe0",padding=9,font=("Consolas",10))
        style.map("C.TButton",background=[("active","#222933")])

        Label(self.root,text="0M3-G4-ARC // COMMAND CONSOLE v3",bg="#090a0c",fg="#d7dbe0",font=("Consolas",22),anchor="w").pack(fill=X,padx=20,pady=(18,8))
        Label(self.root,textvariable=self.system,bg="#14110b",fg="#d7aa54",font=("Consolas",11),anchor="w",padx=12,pady=8).pack(fill=X,padx=20,pady=(0,14))

        body=Frame(self.root,bg="#090a0c"); body.pack(fill=BOTH,expand=True,padx=20,pady=(0,20))
        left=Frame(body,bg="#090a0c"); left.pack(side=LEFT,fill=BOTH,expand=True,padx=(0,10))
        right=Frame(body,bg="#090a0c",width=340); right.pack(side=RIGHT,fill="y",padx=(10,0))

        p=self.panel(left); p.pack(fill=X,pady=(0,10))
        Label(p,text="PATH HEALTH",bg="#111419",fg="#8e99a4",font=("Consolas",10),anchor="w").pack(fill=X,pady=(0,8))
        for k,l in [("root_path","PROJECT ROOT"),("backend_path","BACKEND DIRECTORY"),("frontend_path","FRONTEND DIRECTORY"),("python_path","BACKEND PYTHON"),("npm_path","NPM COMMAND")]:
            self.row(p,l,self.vars[k])

        p=self.panel(left); p.pack(fill=X,pady=(0,10))
        Label(p,text="RUNTIME STATUS",bg="#111419",fg="#8e99a4",font=("Consolas",10),anchor="w").pack(fill=X,pady=(0,8))
        for k,l in [("ollama","OLLAMA"),("backend","BACKEND"),("frontend","FRONTEND")]:
            self.row(p,l,self.vars[k])

        p=self.panel(left); p.pack(fill=X,pady=(0,10))
        Label(p,text="CONTROL",bg="#111419",fg="#8e99a4",font=("Consolas",10),anchor="w").pack(fill=X,pady=(0,8))
        r=Frame(p,bg="#111419"); r.pack(fill=X,pady=3)
        for text,cmd in [("HEALTH CHECK",self.health),("START SYSTEM",self.start_all),("BACKEND ONLY",self.start_backend),("FRONTEND ONLY",self.start_frontend),("OPEN UI",lambda:webbrowser.open(self.cfg["frontend_url"]))]:
            self.button(r,text,cmd)
        r2=Frame(p,bg="#111419"); r2.pack(fill=X,pady=3)
        for text,cmd in [("SETTINGS",self.settings),("OPEN REPORT",self.open_report),("OPEN ROOT",lambda:self.open_folder(self.cfg["project_root"])),("HELP",self.help)]:
            self.button(r2,text,cmd)

        p=self.panel(left); p.pack(fill=BOTH,expand=True)
        Label(p,text="DIAGNOSTICS LOG",bg="#111419",fg="#8e99a4",font=("Consolas",10),anchor="w").pack(fill=X,pady=(0,8))
        self.logbox=Text(p,bg="#0b0d10",fg="#d7dbe0",font=("Consolas",9),wrap="word",relief="flat")
        self.logbox.pack(fill=BOTH,expand=True)

        p=self.panel(right); p.pack(fill=X)
        Label(p,text="QUICK START",bg="#111419",fg="#8e99a4",font=("Consolas",10),anchor="w").pack(fill=X,pady=(0,8))
        txt=("1. Click HEALTH CHECK.\n"
             "2. All path rows should say PASS.\n"
             "3. Click START SYSTEM.\n"
             "4. Visible BACKEND and FRONTEND terminals open.\n"
             "5. Read those windows for errors.\n"
             "6. Click OPEN UI when both are ONLINE.\n\n"
             "Use SETTINGS to change the project root. "
             "Derived backend, frontend, training, and Python paths update automatically.")
        Label(p,text=txt,bg="#111419",fg="#d7dbe0",justify=LEFT,font=("Consolas",10),wraplength=300).pack(anchor="w")

    def log(self, text):
        self.logbox.insert(END,f"[{time.strftime('%H:%M:%S')}] {text}\n")
        self.logbox.see(END)

    def derive_paths(self, project_root):
        root = Path(project_root)
        self.cfg["project_root"] = str(root)
        self.cfg["backend_dir"] = str(root / "omega_arc_ollama" / "backend")
        self.cfg["frontend_dir"] = str(root / "omega_arc_ollama" / "frontend")
        self.cfg["training_dir"] = str(root / "training")
        self.cfg["backend_python"] = str(root / "omega_arc_ollama" / "backend" / ".venv" / "Scripts" / "python.exe")
        self.cfg["training_python"] = str(root / "training" / ".venv" / "Scripts" / "python.exe")

    def settings(self):
        w=Toplevel(self.root)
        w.title("0M3-G4-ARC Settings")
        w.geometry("760x480")
        w.configure(bg="#090a0c")
        holder=Frame(w,bg="#090a0c",padx=18,pady=18); holder.pack(fill=BOTH,expand=True)

        fields=[
            ("project_root","Project Root"),
            ("backend_url","Backend URL"),
            ("frontend_url","Frontend URL"),
            ("ollama_url","Ollama URL"),
            ("ollama_model","Ollama Model")
        ]
        entries={}
        for key,label in fields:
            row=Frame(holder,bg="#090a0c"); row.pack(fill=X,pady=5)
            Label(row,text=label,bg="#090a0c",fg="#d7dbe0",font=("Consolas",10),width=18,anchor="w").pack(side=LEFT)
            e=Entry(row,bg="#111419",fg="#d7dbe0",insertbackground="#d7dbe0",relief="flat",font=("Consolas",10))
            e.insert(0,str(self.cfg.get(key,""))); e.pack(side=LEFT,fill=X,expand=True)
            entries[key]=e

        preview=Text(holder,height=8,bg="#0b0d10",fg="#d7dbe0",font=("Consolas",9),relief="flat")
        preview.pack(fill=X,pady=(12,8))

        def update_preview(*_):
            root_path=entries["project_root"].get().strip()
            root=Path(root_path)
            lines=[
                f"Backend: {root / 'omega_arc_ollama' / 'backend'}",
                f"Frontend: {root / 'omega_arc_ollama' / 'frontend'}",
                f"Training: {root / 'training'}",
                f"Backend Python: {root / 'omega_arc_ollama' / 'backend' / '.venv' / 'Scripts' / 'python.exe'}",
                f"Training Python: {root / 'training' / '.venv' / 'Scripts' / 'python.exe'}",
            ]
            preview.delete("1.0",END); preview.insert("1.0","\n".join(lines))

        entries["project_root"].bind("<KeyRelease>",update_preview)
        update_preview()

        def save():
            self.derive_paths(entries["project_root"].get().strip())
            for key in ["backend_url","frontend_url","ollama_url","ollama_model"]:
                self.cfg[key]=entries[key].get().strip()
            save_config(self.cfg)
            self.log("Settings saved and derived paths updated.")
            w.destroy()
            self.health()

        ttk.Button(holder,text="SAVE SETTINGS",style="C.TButton",command=save).pack(anchor="e",pady=(8,0))

    def health(self):
        self.logbox.delete("1.0",END)
        root=Path(self.cfg["project_root"])
        backend=Path(self.cfg["backend_dir"])
        frontend=Path(self.cfg["frontend_dir"])
        py=Path(self.cfg["backend_python"])
        npm=shutil.which("npm.cmd") or shutil.which("npm")

        checks=[
            ("Project root",root.exists(),root),
            ("Backend directory",backend.exists(),backend),
            ("Backend app.py",(backend/"app.py").exists(),backend/"app.py"),
            ("Backend Python",py.exists(),py),
            ("Frontend directory",frontend.exists(),frontend),
            ("Frontend package.json",(frontend/"package.json").exists(),frontend/"package.json"),
            ("Frontend node_modules",(frontend/"node_modules").exists(),frontend/"node_modules"),
            ("npm command",bool(npm),npm or "NOT FOUND"),
        ]
        lines=["0M3-G4-ARC DIAGNOSTICS REPORT","="*40,""]
        for name,ok,value in checks:
            state="PASS" if ok else "FAIL"
            self.log(f"{state} — {name}: {value}")
            lines.append(f"{state} — {name}: {value}")
        REPORT_FILE.write_text("\n".join(lines),encoding="utf-8")

        self.vars["root_path"].set("PASS" if root.exists() else "FAIL")
        self.vars["backend_path"].set("PASS" if backend.exists() and (backend/"app.py").exists() else "FAIL")
        self.vars["frontend_path"].set("PASS" if frontend.exists() and (frontend/"package.json").exists() else "FAIL")
        self.vars["python_path"].set("PASS" if py.exists() else "FAIL")
        self.vars["npm_path"].set("PASS" if npm else "FAIL")
        self.refresh()

    def start_backend(self):
        backend=Path(self.cfg["backend_dir"]); py=Path(self.cfg["backend_python"])
        if not (backend/"app.py").exists():
            return messagebox.showerror("Invalid backend path",str(backend))
        if not py.exists():
            return messagebox.showerror("Invalid Python path",str(py))
        self.log(f"Opening backend terminal from {backend}")
        visible("0M3-G4-ARC BACKEND",[str(py),"-m","uvicorn","app:app","--reload"],str(backend))

    def start_frontend(self):
        frontend=Path(self.cfg["frontend_dir"])
        npm=shutil.which("npm.cmd") or shutil.which("npm")
        if not (frontend/"package.json").exists():
            return messagebox.showerror("Invalid frontend path",str(frontend))
        if not npm:
            return messagebox.showerror("npm missing","npm was not found on PATH.")
        self.log(f"Opening frontend terminal from {frontend}")
        visible("0M3-G4-ARC FRONTEND",[npm,"run","dev"],str(frontend))

    def start_ollama(self):
        if http_ok(self.cfg["ollama_url"]): return
        ollama=shutil.which("ollama.exe") or shutil.which("ollama")
        if ollama:
            visible("OLLAMA",[ollama,"serve"],self.cfg["project_root"])

    def start_all(self):
        self.system.set("STARTING")
        self.health()
        self.start_ollama()
        time.sleep(1)
        self.start_backend()
        time.sleep(1)
        self.start_frontend()
        self.root.after(3500,self.refresh)

    def refresh(self):
        self.vars["ollama"].set("ONLINE" if http_ok(self.cfg["ollama_url"]) else "OFFLINE")
        self.vars["backend"].set("ONLINE" if http_ok(self.cfg["backend_url"]) else "OFFLINE")
        self.vars["frontend"].set("ONLINE" if http_ok(self.cfg["frontend_url"]) else "OFFLINE")
        states=[self.vars["ollama"].get(),self.vars["backend"].get(),self.vars["frontend"].get()]
        self.system.set("READY" if states==["ONLINE","ONLINE","ONLINE"] else ("PARTIAL SYSTEM" if "ONLINE" in states else "STANDBY"))

    def open_report(self):
        if not REPORT_FILE.exists(): self.health()
        os.startfile(str(REPORT_FILE))

    def open_folder(self,path):
        p=Path(path)
        if p.exists(): os.startfile(str(p))
        else: messagebox.showerror("Folder missing",str(p))

    def help(self):
        messagebox.showinfo("Quick Start",
            "1. Click HEALTH CHECK.\n"
            "2. Confirm all path rows show PASS.\n"
            "3. If anything fails, click SETTINGS.\n"
            "4. Set Project Root to your Turning folder.\n"
            "5. Save settings; all derived paths update automatically.\n"
            "6. Click START SYSTEM.\n"
            "7. Read the visible backend/frontend terminals for errors.\n"
            "8. Click OPEN UI when both services are online."
        )

    def tick(self):
        self.refresh()
        self.root.after(4000,self.tick)

root=Tk()
App(root)
root.mainloop()

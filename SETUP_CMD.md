# Prosit-2 setup (Command Prompt) — use Python 3.12

You currently have only Python 3.14. The backend needs **Python 3.12** so all packages install from pre-built wheels (no Rust).

---

## Step A: Install Python 3.12

**Option 1 — Winget (recommended)**  
Open **cmd** and run:

```cmd
![1771776187162](image/SETUP_CMD/1771776187162.png) --accept-package-agreements
```

Close and reopen cmd after install.

**Option 2 — Manual**  
1. Go to https://www.python.org/downloads/release/python-3129/  
2. Under "Files" download **Windows installer (64-bit)**.  
3. Run it, check **"Add python.exe to PATH"**, then Install.  
4. Close and reopen cmd.

---

## Step B: Confirm Python 3.12 is available

```cmd
py -0
```

You should see both **3.12** and **3.14** (or at least 3.12).

---

## Step C: Remove old venv and create a new one with 3.12

```cmd
cd c:\Users\blank\Desktop\Projects\Prosit-2
```

```cmd
rmdir /s /q .venv
```

```cmd
py -3.12 -m venv .venv
```

```cmd
.venv\Scripts\activate.bat
```

You should see `(.venv)` and `python --version` should show **3.12.x**.

---

## Step D: Install backend dependencies

```cmd
pip install -r backend\requirements.txt
```

This should finish without Rust errors.

---

## Step E: Start backend (leave this window open)

```cmd
cd backend
```

```cmd
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Step F: Second cmd window — frontend

Open a **new** cmd, then:

```cmd
cd c:\Users\blank\Desktop\Projects\Prosit-2\frontend
```

```cmd
npm install
```

```cmd
npm run dev
```

---

## Step G: Browser

Open **http://localhost:3000**

---

**Summary:** Install Python 3.12 (winget or python.org), delete `.venv`, create a new venv with `py -3.12 -m venv .venv`, activate it, then run `pip install` and the rest.

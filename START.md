# CivicSense AI – Run from scratch

Follow these steps with **two terminals** (or run the scripts below).

---

## 1. Open the project folder

In File Explorer go to:
```
c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main
```
Or in PowerShell:
```powershell
cd "c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main"
```

---

## 2. Terminal 1 – Start the backend (API)

**Option A – If you have a virtualenv (`.venv`):**
```powershell
cd "c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main"
.venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary python-dotenv
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Option B – Without activating venv:**
```powershell
cd "c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main"
.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Leave this terminal open. You should see:
- `Uvicorn running on http://0.0.0.0:8000`
- If PostgreSQL is not installed/running: `Using in-memory storage` (that’s OK)

---

## 3. Terminal 2 – Start the frontend

**First time only – install dependencies:**
```powershell
cd "c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main\frontend"
npm install
```

**Then start the dev server:**
```powershell
cd "c:\Users\BIT\Downloads\civicsense-ai-main\civicsense-ai-main\frontend"
npm run dev
```

Leave this terminal open. You should see something like:
- `Local: http://localhost:5173/`

---

## 4. Use the app

1. In your browser open: **http://localhost:5173**
2. If you see “No schemes in the database yet”, click **“Load schemes from CSV”** (uses `schemes.csv` in the project root).
3. Fill **Your profile** (age, income, state, category, etc.) and click **“Match schemes”**.
4. View **Matched for you** and **Browse all schemes**.

---

## Quick reference

| What            | URL or command |
|-----------------|----------------|
| Frontend        | http://localhost:5173 |
| API docs        | http://localhost:8000/api/docs |
| API health      | http://localhost:8000/api/v1/health |

**Stop:** In each terminal press `Ctrl+C`.

**No PostgreSQL?** The backend uses in-memory storage automatically; you can still load CSV and match schemes.

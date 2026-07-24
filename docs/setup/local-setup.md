# Local Setup

```powershell
git init
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
python -m venv backend/.venv
backend\.venv\Scripts\pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
python -m venv ai/.venv
ai\.venv\Scripts\pip install -r ai\requirements-ai.txt
docker compose up --build
```

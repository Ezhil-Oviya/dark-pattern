# Intelligent Automated Compliance Auditing Framework

Final Year Research Project foundation for auditing Indian e-commerce platforms for CCPA dark pattern compliance using browser automation, explainable AI, and an intelligent compliance bot.

This repository currently contains only the production-ready foundation: folder boundaries, configuration, dependency manifests, placeholder modules, and documentation. Business logic is intentionally not implemented.

## Architecture

Presentation Layer -> API Layer -> Service Layer -> Business Logic Layer -> Repository Layer -> Database

Major replaceable modules:

- Authentication
- Browser Automation
- Dark Pattern Detection
- Compliance Verification
- Evidence Management
- Report Generation
- Dashboard Analytics
- AI Compliance Bot

## Initialize

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
```

## Run

```powershell
docker compose up --build
```

Backend: `http://localhost:8000`

Frontend: `http://localhost:5173`

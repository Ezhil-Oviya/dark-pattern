To run the project 
Frontend
cd frontend
npm run dev
Backend
cd backend
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

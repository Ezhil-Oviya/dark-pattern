from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.website_routes import router
from app.routes.automation_routes import router as automation_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Dark Pattern Compliance Framework"
)

# Allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api/v1",
    tags=["Website Configuration"]
)

app.include_router(

    automation_router,

    prefix="/api/v1",

    tags=["Automation"]

)

app.mount(
    "/artifacts",
    StaticFiles(directory="artifacts"),
    name="artifacts"
)

@app.get("/")
def home():
    return {
        "message": "Dark Pattern Compliance Auditing Framework API is running"
    }
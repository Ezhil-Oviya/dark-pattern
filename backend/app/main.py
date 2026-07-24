from fastapi import FastAPI

app = FastAPI(
    title="Dark Pattern Compliance Auditor API",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {
        "message": "Dark Pattern Compliance Auditor API is running successfully"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }
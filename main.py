from fastapi import FastAPI
from pydantic import BaseModel
import httpx
from app.analyze.api import router as analyze_router

app = FastAPI()
app.include_router(analyze_router)

@app.get("/")
def root():
    return {"message": "FastAPI 실행 성공!"}

        
        


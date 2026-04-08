from fastapi import FastAPI
from pydantic import BaseModel
import httpx
from app.analyze.api import router as analyze_router

app = FastAPI()
app.include_router(analyze_router)

@app.get("/")
def root():
    return {"message": "FastAPI 실행 성공!"}


@app.get("/spring-test")
async def spring_test():
    url = "http://localhost:8082/api/test"
    data = {
        "stock": "삼성전자",
        "price": 180000,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            response.raise_for_status()
            return{
                "message" : response.json()
            }
        except Exception as e:
            return{"status":"error", "message":str(e)}
        
        


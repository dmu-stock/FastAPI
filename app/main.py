from fastapi import FastAPI
from pydantic import BaseModel
# from models.db import engine 
import requests

app = FastAPI()

@app.get("/")
def root():
    return {"message": "FastAPI 실행 성공!"}


@app.get("/spring-test")
def spring_test():
    response=requests.post("http://localhost:8082/api/test", json={
        "stock": "삼성전자",
        "price": 180000,
    })
    print(f"상태 코드: {response.status_code}")
    print(f"스프링의 대답: {response.text}")


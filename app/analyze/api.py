from fastapi import APIRouter
from .service import analyze_news, predict_stock_trend
from pydantic import BaseModel
from typing import List
from typing import Optional

router = APIRouter(prefix="/api/v1")

# Dto
class NewsAnalysisRequestDto(BaseModel):
    query: str
    urls: List[str]

class StockAnalysisRequestDto(BaseModel):
    stockCode: Optional[str] = None
    ticker: Optional[str] = None
    


@router.post("/NewsAnalysis")
async def analyze_news_api(request: NewsAnalysisRequestDto):
    return await analyze_news(request.query, request.urls)

@router.post("/StockAnalysis")
async def predict_stock_api(request: StockAnalysisRequestDto):
    if request.stockCode:

        final_ticker = f"{request.stockCode}.KS"
        print(f"🇰🇷 한국 종목 분석 시작: {final_ticker}")
    elif request.ticker:

        final_ticker = request.ticker
        print(f"🇺🇸 미국 종목 분석 시작: {final_ticker}")

    return await predict_stock_trend(final_ticker)
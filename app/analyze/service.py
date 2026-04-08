from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from newspaper import Article
from dotenv import load_dotenv
from openai import OpenAI
import yfinance as yf
import os



load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



async def analyze_news(query,urls):
    all_text = ""

    print(f"검색어: {query}")
    print(f"받은 URL 개수: {len(urls)}")

    for i, url in enumerate(urls[:3]):
        print(f"   - URL {i+1}: {url}")

        # 뉴스 크롤링 (Newspaper3k)
    for url in urls:
        try:
            article = Article(url, language='ko')
            # 전체 싹다 긁어옴
            article.download()
            # 뉴스원문만 보기 위해 정제
            article.parse()
            all_text += f"\n\n[뉴스 제목: {article.title}]\n{article.text}"
        except Exception as e:
            print(f" {url} 크롤링 실패: {e}")
    
   # LLM 요약(OpenAI)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 주식 투자 전문가야. 제공된 뉴스 본문들을 읽고 핵심 내용을 3문장으로 요약해줘."},
                {"role": "user", "content": f"다음 뉴스들을 분석해서 '{query}' 관점에서 요약해줘:\n\n{all_text[:5000]}"}
            ],
            temperature=0.5
        )
        
        return response.choices[0].message.content
        

    except Exception as e:
        return f"분석 중 오류가 발생했습니다: {str(e)}"
    

async def predict_stock_trend(stock_code):
    print(f"검색어: {stock_code}")

    stock = yf.Ticker(stock_code)
    hist = stock.history(period="1mo")

    # 야후 파이낸스 최근 종가 및 거래량 추출
    latest_price = hist['Close'].iloc[-1]
    prev_price = hist['Close'].iloc[-2]
    price_change = ((latest_price - prev_price) / prev_price) * 100
    avg_volume = hist['Volume'].mean()
    latest_volume = hist['Volume'].iloc[-1]

     # AI에게 보낼 데이터 정리
    stock_context = f"""
    종목: {stock_code}
    현재가: {latest_price:.2f}
    전일 대비 등락률: {price_change:.2f}%
    최근 평균 거래량: {avg_volume:.0f}
    오늘 거래량: {latest_volume:.0f}
    """

    
   # LLM 요약(OpenAI)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 기술적 분석 전문가야. 주식의 신이지. 데이터를 보고 상승/하락을 예측해줘"},
                {"role": "user", "content": f"다음 데이터를 분석해줘: {stock_context}"}
            ],
            temperature=0.5
        )
        
        return response.choices[0].message.content
      
    except Exception as e:
        return f"분석 중 오류가 발생했습니다: {str(e)}"

    
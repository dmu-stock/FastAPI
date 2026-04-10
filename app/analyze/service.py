from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from newspaper import Article
from dotenv import load_dotenv
from openai import AsyncOpenAI
import yfinance as yf
import os




load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 뉴스 크롤링 (Newspaper3k) 메서드
def crawling_urls(urls):
    all_text = ""
        
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
        
        return all_text
    
# LLM 요약 메서듣
async def analyze_openAi(prompt):
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 기술적 분석 전문가야. 주식의 신이지. 데이터를 보고 상승/하락을 예측해줘"},
                {"role": "user", "content": f"다음 데이터를 분석해줘: {prompt}"}
            ],
            temperature=0.5
        )
    except Exception as e:
        return f"분석 중 오류가 발생했습니다: {str(e)}"
    
    return response.choices[0].message.content
    


async def analyze_news(query,urls):
    
    print(f"검색어: {query}")
    print(f"받은 URL 개수: {len(urls)}")

    #크롤링 함수 실행
    crawling_text=crawling_urls(urls)

   # LLM 요약
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 주식 투자 전문가야. 제공된 뉴스 본문들을 읽고 핵심 내용을 3문장으로 요약해줘."},
                {"role": "user", "content": f"이 프롬프트를 이용해서 전체 종목들의 주가를 예측해줘 상승/하락 등 '{query}' 관점에서 요약해줘:\n\n{crawling_text[:5000]}"}
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

    
   
    
async def analyze_news_rag(memberStock,urls):
    crawling_text = crawling_urls(urls)
    # 내 주식 정보 문자열 화
    stock_context = "사용자 보유 주식 현황:\n"
    for s in memberStock:
        stock_context += f"- 종목코드: {s.stockCode}, 평단가: {s.avgPrice}, 수량: {s.quantity}\n"

    # LLM 프롬프트 구성
    prompt = f"""
    너는 주식 분석 전문가 '주모'야. 
    아래 제공된 [보유 주식 현황]과 [최신 뉴스 정보]를 바탕으로 투자 전략을 세워줘.
    
    [보유 주식 현황]
    {stock_context}
    
    [최신 뉴스 정보]
    {crawling_text}
    
    분석 가이드라인:
    1. 현재 보유 종목과 관련된 뉴스가 있다면 해당 내용을 언급해줘.
    2. 뉴스 내용을 근거로 '매수/매도/홀딩'에 대한 의견을 조심스럽게 제안해줘.
    3. 친절하고 전문적인 말투로 답변해줘.
    """

    # 4. LLM 호출 (예: OpenAI API)
    # response = await client.chat.completions.create(model="gpt-4", messages=[{"role": "user", "content": prompt}])
    response =await analyze_openAi(prompt)
    return response

   


    
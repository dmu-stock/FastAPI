from newspaper import Article, Config
from dotenv import load_dotenv
from openai import AsyncOpenAI
import yfinance as yf
import os
import httpx
from finvizfinance.quote import finvizfinance
from ..models.request import StockType
from ..services.ticker_serevice import convert_ticker
from ..services.news_service import get_naver_news, get_finnhub_news, get_dart_disclosure

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 뉴스 크롤링 (Newspaper3k) 메서드
def crawling_urls(all_news_urls):
    config = Config()
    config.browser_user_agent = "Mozilla/5.0"
    config.request_timeout = 5
    docs = []
        
    for url in all_news_urls:
        try:
            article = Article(url, language='ko', config=config)
            # 전체 싹다 긁어옴
            article.download()
            # 뉴스원문만 보기 위해 정제
            article.parse()
            # 길이 제한
            text = article.text[:1000]

            docs.append({
                "title": article.title,
                "content": text,
                "url": url
            })
            
        except Exception as e:
            print(f" {url} 크롤링 실패: {e}")
        
    return docs
    
# LLM 요약 메서드
async def analyze_openAi(prompt):
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "너는 기술적 분석 전문가야. 주식의 신이지"},
                {"role": "user", "content": f"다음 데이터를 분석해줘: {prompt}"}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API 호출 에러: {e}")
        return f"분석 중 오류가 발생했습니다: {str(e)}"
    
    


# 핀비즈 데이터 수집
def get_finviz_analysis(ticker):

    try:
        stock = finvizfinance(ticker)
        # 핀비즈의 그 유명한 '표' 데이터를 통째로 가져옵니다.
        info = stock.ticker_fundament()
        
        analysis_data = {
            "target_price": info.get("Target Price"),
            "recommendation": info.get("Recom"),  # 1에 가까울수록 강력매수
            "insider_trading": info.get("Insider Trading"),
            "inst_ownership": info.get("Inst Own"),
            "rsi": info.get("RSI (14)"),
            "sma20_dist": info.get("SMA20"), # 20일선 이격도
            "sector": info.get("Sector"),
            "industry": info.get("Industry")
        }
    except Exception as e:
        print(f"핀비즈 데이터 수집 중 에러: {e}")
        
    return analysis_data
    


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

    
   
    
    
async def analyze_news_rag(memberStock):
   
    stock_context = "사용자 보유 주식 현황:\n"
    finviz_context = "미국 주식 추가 분석 정보:\n"
    all_news_urls = []
    news_context = ""
    for s in memberStock:
        stock_context += f"- 종목코드: {s.stockCode}, 평단가: {s.avgPrice}, 수량: {s.quantity}\n"

        # 티커 -> 주식이름
        stockName = convert_ticker(s.stockCode)

        if s.type == "USA":
            news = await get_finnhub_news(s.stockCode)

        else:
            news = await get_dart_disclosure(s.stockCode)
            print(f"{s.stockCode} DART 공시 {len(news)}건 수집 완료")
            # news += await get_naver_news(stockName)  # 보조
        
        all_news_urls.extend(news)

        if s.type ==StockType.USA:
            try:
                f_data=get_finviz_analysis(s.stockCode)
                finviz_context += (
                    f"[{s.stockCode} 분석] 섹터: {f_data['sector']}, "
                    f"목표가: {f_data['target_price']}, RSI: {f_data['rsi']}\n"
                )
                print(f"{s.stockCode} 핀비즈 결과: {f_data}")
            except Exception as e:
                print(f"핀비즈 수집 중 에러: {e}")
                pass

    # 뉴스url 크롤링
    # if all_news_urls:
    #     print(f"{len(all_news_urls)}개 url 크롤링")
    #     print(f"{(all_news_urls)}개 url 크롤링")
    #     news_results =crawling_urls(all_news_urls)
    #     for doc in news_results:
    #         news_context += f"\n뉴스제목: {doc['title']}\n내용: {doc['content']}\n"

    for item in all_news_urls:
        # 뉴스 객체에서 안전하게 데이터 추출
        title = item.get('headline') or item.get('title') or item.get('report_nm') or "제목 없음"
        content = item.get('summary') or item.get('content') or f"{item.get('corp', '')} 기업 공시 자료"
        source = item.get('source') or item.get('corp') or "국내 정보"
        news_context += f"\n- 제목: [{source}] {title}\n- 내용: {content[:300]}...\n- 요약: {content[:300]}\n"
    

    # LLM 프롬프트 구성
    prompt = f"""
    너는 여의도에서 잔뼈가 굵은 주식 전문가 '주모'야. 
    제공된 데이터를 단순 요약하지 말고, 반드시 '돈이 되는 정보'를 짚어줘.

    [데이터]
    ... (생략) ...

    [분석 가이드라인 - 필독!]
    1. 삼성전자(005930) 분석 시, 반드시 제공된 공시 리스트 중 '실적(잠정)', '주식소각' 등의 키워드를 찾아내서 언급해.
    2. 4월 7일 실적 공시와 3월 31일 주식 소각 정보를 바탕으로, 현재 평단가(18만원) 탈출 가능성을 냉정하게 분석해.
    3. "상승할 수도, 하락할 수도 있다"는 식의 애매한 답변은 금지야. 데이터에 기반해 확신 있는 어조로 말해줘.
    4. IREN은 RSI가 높으니 구체적인 익절 구간을, PLTR은 목표가 대비 현재가 괴리율을 계산해서 말해줘.
    5. 말투는 친절하지만 내용은 팩트 폭격 수준으로 날카롭게!
    """

    # LLM 호출
    response =await analyze_openAi(prompt)
    return response

   


    
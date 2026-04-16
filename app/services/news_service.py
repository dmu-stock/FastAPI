import os
import httpx
import csv
from dotenv import load_dotenv
from datetime import datetime, timedelta



load_dotenv()
async def get_naver_news(stock_name):
    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id":os.environ.get("NAVER_CLIENT_ID"),
        "X-Naver-Client-Secret":os.environ.get("NAVER_CLIENT_SECRET")
    }

    params = {
        "query": stock_name,
        "display": 10,
        "sort": "sim"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print("네이버 API 실패:", response.status_code)
        return []

    data = response.json()

    return [
        item["link"]
        for item in data.get("items", [])
        if "video" not in item["link"] and "tv.naver.com" not in item["link"]
    ]

async def get_finnhub_news(ticker:str):
    url = "https://finnhub.io/api/v1/company-news"
    FINNHUB_API_KEY=os.environ.get("FINNHUB_API_KEY")

    # 최근 7일
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=5)

    params = {
        "symbol": ticker,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "token": FINNHUB_API_KEY
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        print("FINNHUB API 실패:", response.status_code)
        return []  

    data = response.json()
    data = data[:10]
    print(f"\n--- [{ticker}] Finnhub 뉴스 데이터 구조 확인 ---")
    if data:
        print(f"샘플 뉴스 데이터 (1건): {data[0]}") 
        print(f"데이터 키 목록: {data[0].keys()}")
    else:
        print("수집된 뉴스가 없습니다.")
    print("------------------------------------------\n")

    if not data:
        return []
   

    return [
        {
            "title": item["headline"],
            "content": item.get("summary", ""),
            "url": item["url"],
            "source": item["source"]
        }
        for item in data
    ]

CORP_MAP = {}
CORPCODE_FILTERED = 'corpcode_filtered.csv'
def load_corp_map():
    with open(CORPCODE_FILTERED, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            corp_code = row[0].strip()
            ticker = row[2].strip()

            CORP_MAP[ticker] = corp_code


DART_API_KEY=os.environ.get("DART_API_KEY")

async def get_dart_disclosure(ticker:str):
    load_corp_map()
    corp_code = CORP_MAP.get(ticker)
    print(f"{corp_code}------------------")
    if not corp_code:
        return []

    url = "https://opendart.fss.or.kr/api/list.json"

    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": start_date.strftime('%Y%m%d'), # YYYYMMDD 형식 필수
        "end_de": end_date.strftime('%Y%m%d'),
        "page_count": "10"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    data = response.json()
    print(f"DEBUG DART 응답: {data}")

    return [
        {
            "title": item["report_nm"],
            "date": item["rcept_dt"],
            "corp": item["corp_name"]
        }
        for item in data.get("list", [])
    ]




import csv
import yfinance as yf
from functools import lru_cache

# 1️⃣ 서버 시작 시 CSV를 메모리에 로드
KOREA_CORP_MAP = {}
CORPCODE_FILTERED = 'corpcode_filtered.csv'

try:
    with open(CORPCODE_FILTERED, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            s_code = row['stock_code'].strip()
            if s_code:
                KOREA_CORP_MAP[s_code] = row['corp_name'].strip()
    print(f"한국 주식 {len(KOREA_CORP_MAP)}개 로드")
except Exception as e:
    print(f"CSV 로드 중 에러 발생: {e}")

TICKER_MAP = {
    "AAPL": "애플 Apple",
    "TSLA": "테슬라 Tesla",
    "NVDA": "엔비디아 NVIDIA",
    "IREN": "아이렌 IREN",
    "PLTR": "팔란티어 Palantier",
    "005930": "삼성전자",
}

@lru_cache(maxsize=1000)
def get_cached_name(ticker: str) -> str:
    return _resolve_ticker_name(ticker)

def _resolve_ticker_name(ticker: str) -> str:
    # 하드코딩 맵 확인
    if ticker in TICKER_MAP:
        return TICKER_MAP[ticker]

    # 한국 주식 (메모리 딕셔너리에서 검색)
    if ticker.isdigit():
        return KOREA_CORP_MAP.get(ticker, ticker)

    # 미국 주식 (yfinance)
    try:
        stock = yf.Ticker(ticker)
        # 속도가 중요한 경우 .fast_info를 쓸 수 있지만 이름은 .info가 정확함
        info = stock.info
        name = info.get("longName") or info.get("shortName")
        if name:
            return f"{name} ({ticker})"
    except Exception as e:
        print(f"[Ticker 변환 실패] {ticker}: {e}")

    return ticker

def convert_ticker(ticker: str) -> str:
    return get_cached_name(ticker)


"""
news_crawler.py

[무엇을 하는 파일인가?]
- Yahoo Finance에서 뉴스 '헤드라인'만 수집한다.
- 뉴스 수집 범위를
  1) 개별 종목
  2) 섹터(ETF)
  3) 시장/지수(ETF)
  로 확장하여 데이터 부족 문제를 보완한다.
- 수집한 헤드라인을 LLM으로 전처리하여
  FinBERT 감정 분석에 바로 사용할 수 있는 형태로 반환한다.

[왜 이렇게 설계했는가?]
- 뉴스 본문은 의견·배경 설명이 많아 감정 분석 노이즈가 크다.
- 시장 반응이 가장 압축된 정보는 '헤드라인'이므로 헤드라인만 사용한다.
- 개별 종목 뉴스만으로는 표본이 적을 수 있어,
  섹터/시장 뉴스로 맥락 정보를 함께 제공한다.
"""

import yfinance as yf
import pandas as pd
from typing import List


# -------------------------------------------------
# 반환 DataFrame 컬럼 정의
# (항상 동일한 구조를 유지하기 위함)
# -------------------------------------------------
NEWS_COLUMNS = [
    "date",           # 뉴스 발행 날짜
    "ticker",         # 티커 (종목 / 섹터 ETF / 시장 ETF)
    "news_type",      # stock / sector / market
    "headline",       # 원본 뉴스 헤드라인
    "source",         # 뉴스 출처 (Reuters, Bloomberg 등)
]


# -------------------------------------------------
# 뉴스 수집 대상 정의
# -------------------------------------------------

# 1) 개별 종목 뉴스
STOCK_TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META",
    "TSLA", "NVDA", "BRK-B", "V", "UNH"
]

# 2) 섹터 뉴스 (ETF 기준)
# → 산업 전반 분위기 파악 목적
SECTOR_TICKERS = {
    "XLK": "technology",
    "SOXX": "semiconductor",
    "XLF": "financial"
}

# 3) 시장 / 증시 뉴스 (지수 ETF)
# → 거시적인 시장 분위기 반영 목적
MARKET_TICKERS = {
    "SPY": "market",
    "QQQ": "nasdaq"
}


def fetch_news_by_ticker(ticker: str, news_type: str) -> pd.DataFrame:

    try:
        stock = yf.Ticker(ticker)
        news_items = stock.news or []
    except Exception as e:
        print(f"[에러] {ticker} 뉴스 수집 실패: {e}")
        return pd.DataFrame(columns=NEWS_COLUMNS)

    if not news_items:
        return pd.DataFrame(columns=NEWS_COLUMNS)

    rows = []

    for item in news_items:
        try:
            content = item.get("content", {})
            headline = content.get("title", "")
            if not headline:
                continue

            pub_date = content.get("pubDate", "")
            date = pd.to_datetime(pub_date, utc=True).date() if pub_date else None

            # 날짜 없으면 스킵
            if date is None:
                continue

            source = content.get("provider", {}).get("displayName", "")

            rows.append({
                "date": date,
                "ticker": ticker,
                "news_type": news_type,
                "headline": headline,
                "clean_headline": "",
                "source": source,
            })

        except Exception:
            continue

    if not rows:
        return pd.DataFrame(columns=NEWS_COLUMNS)

    df = pd.DataFrame(rows, columns=NEWS_COLUMNS)

    # 중복 제거
    df = df.drop_duplicates(subset=['headline']).reset_index(drop=True)

    # 최근 7일치만 유지
    today = pd.Timestamp.now().date()
    df = df[df['date'] >= (pd.Timestamp.now() - pd.Timedelta(days=7)).date()]

    print(f"[{ticker}] 뉴스 {len(df)}건 수집 완료")

    return df


def fetch_all_tickers_news(tickers: list) -> pd.DataFrame:
    all_news = []
    
    for ticker in tickers:
        df = fetch_news_by_ticker(ticker, news_type='stock')
        if not df.empty:
            all_news.append(df)
    
    if not all_news:
        print("[경고] 수집된 뉴스 없음")
        return pd.DataFrame(columns=NEWS_COLUMNS)
    
    combined = pd.concat(all_news, ignore_index=True)
    print(f"\n[완료] 총 {len(combined)}건 뉴스 수집")
    print(combined['ticker'].value_counts())
    
    return combined


# -------------------------------------------------
# 단독 실행 테스트
# -------------------------------------------------
if __name__ == "__main__":
    df_news = fetch_all_tickers_news(save_debug_csv=True)

    print("\n[미리보기]")
    print(df_news.head(10))
import pandas as pd
import os
os.environ["HF_HUB_DISABLE_UNSAFE_LOAD_CHECK"] = "1"
import numpy as np
from app.services.finbert_service import FinBertSentimentAnalyzer
from app.collector.news_crawler import fetch_all_tickers_news
from app.config.config import TICKERS

def process_market_sentiment(
    news_csv_path: str,
    output_path: str = "market_sentiment.csv"
):
    df_news = pd.read_csv(news_csv_path)
    
    df_news = df_news[
        (df_news['ticker'] != 'ticker') & 
        (df_news['date'] != 'date')
    ].reset_index(drop=True)
    
    df_news['date'] = pd.to_datetime(df_news['date'], errors='coerce').dt.date
    
    # 빈 title 제거
    df_news = df_news[df_news['title'].notna()].reset_index(drop=True)
    df_news['title'] = df_news['title'].astype(str).str.strip()
    df_news = df_news[df_news['title'] != ''].reset_index(drop=True)
    
    # 혹시 날짜 변환 실패로 NaN 된 찌꺼기가 있다면 마지막으로 한 번 더 제거
    df_news = df_news.dropna(subset=['date']).reset_index(drop=True)
    
    print(f"처리할 뉴스 수: {len(df_news)}")
    print(f"기간: {df_news['date'].min()} ~ {df_news['date'].max()}")
    
    # FinBERT 초기화
    analyzer = FinBertSentimentAnalyzer()
    
    # 배치 처리
    BATCH_SIZE = 64
    all_scores = []
    titles = df_news['title'].tolist()
    
    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        try:
            results = analyzer.analyze(batch)
            scores = [r['sentiment_score'] for r in results]
        except Exception as e:
            print(f"[경고] 배치 {i} 실패: {e}")
            scores = [0.0] * len(batch)
        
        all_scores.extend(scores)
        
        batch_idx = i // BATCH_SIZE
        if batch_idx % 50 == 0 and len(titles) > 0:
            print(f"진행 중: {i}/{len(titles)} ({i/len(titles)*100:.1f}%)")
    
    df_news['sentiment_score'] = all_scores
    
    # 날짜별 집계
    market_sentiment = df_news.groupby('date').agg(
        market_sent_mean  = ('sentiment_score', 'mean'),
        market_sent_std   = ('sentiment_score', 'std'),
        market_sent_max   = ('sentiment_score', 'max'),
        market_sent_min   = ('sentiment_score', 'min'),
        market_news_count = ('sentiment_score', 'count'),
    ).reset_index()
    
    market_sentiment['date'] = pd.to_datetime(market_sentiment['date'])
    
    # 파생 피처
    market_sentiment = market_sentiment.sort_values('date').reset_index(drop=True)
    
    market_sentiment['market_sent_ma3'] = market_sentiment['market_sent_mean'].rolling(3).mean()
    market_sentiment['market_sent_ma5'] = market_sentiment['market_sent_mean'].rolling(5).mean()
    market_sentiment['market_sent_momentum'] = (
        market_sentiment['market_sent_mean'] - market_sentiment['market_sent_ma3']
    )
    # 뉴스 급증 여부
    market_sentiment['market_news_surge'] = (
        market_sentiment['market_news_count'] /
        (market_sentiment['market_news_count'].rolling(5).mean() + 1e-9)
    )
    
    # NaN 채우기
    fill_cols = ['market_sent_ma3', 'market_sent_ma5', 
                 'market_sent_momentum', 'market_news_surge']
    market_sentiment[fill_cols] = market_sentiment[fill_cols].fillna(0)
    
    market_sentiment.to_csv(output_path, index=False)
    print(f"\n저장 완료: {output_path}")
    print(f"총 {len(market_sentiment)}일치 데이터")
    print(market_sentiment.head())
    
    return market_sentiment

tickers = TICKERS

def process_news_stock():
    news_df = fetch_all_tickers_news(tickers)

    if not news_df.empty:
        analyzer = FinBertSentimentAnalyzer()
        titles = news_df['headline'].tolist()
        results = analyzer.analyze(titles)
        news_df['sentiment_score'] = [r['sentiment_score'] for r in results]
        
        # 종목별 평균 센티멘트
        ticker_sentiment = news_df.groupby('ticker')['sentiment_score'].mean().to_dict()
    else:
        ticker_sentiment = {}

    return ticker_sentiment

if __name__ == "__main__":
    process_market_sentiment(
        news_csv_path="vintage_2425.csv",
        output_path="market_sentiment.csv"
    )
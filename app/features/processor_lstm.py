# TODO:
# 1. 데이터 정제 (Data Cleaning)
#    - yfinance에서 가져온 데이터 중 비어있는 값(NaN) 처리
#    - 주식 분할이나 배당 등이 반영된 수정 종가(Adj Close) 사용 여부 결정
#
# 2. 기술적 지표 생성 (Technical Indicators)
#    - 이동평균선(SMA/EMA): 5일, 20일, 60일선 등 계산
#    - 변동성 지표: 볼린저 밴드(Bollinger Bands), ATR 등
#    - 모멘텀 지표: RSI, MACD, Stochastic 등
#
# 3. 모델 입력용 데이터셋 구성 (Feature Matrix)
#    - XGBoost 모델이 학습할 때 사용했던 컬럼 순서와 동일하게 정렬
#    - 예측 시점(t)을 기준으로 과거 n일간의 데이터를 한 줄로 펼치기(Lag features)
#
# 4. 정규화 및 스케일링 (Optional)
#    - 데이터의 범위를 0~1 사이로 맞추는 등의 스케일링 작업 (필요 시)
#
# 5. 최종 데이터 유효성 검사
#    - 모델에 넣기 직전 데이터에 이상치나 무한대(Inf) 값이 없는지 확인

import pandas as pd
import numpy as np
from app.database.sqlite_db import get_connection
from datetime import datetime

class FeatureProcessor:
    def __init__(self, db_path: str = "stock_data.db"):
        self.db_path = db_path

    def get_raw_data(self)->pd.DataFrame:
        conn = get_connection()
        query = f"SELECT * FROM stock_prices ORDER BY date ASC"
        df = pd.read_sql(query,conn)
        conn.close()

        return df

    def calc_technical_indicators(self, df, rsi_period=14):
        # 종목과 날짜 순으로 철저하게 정렬
        df = df.sort_values(['ticker', 'date']).reset_index(drop=True)

        # ---------------------------
        # 1. 이동평균 (Trend)
        # ---------------------------
        df['ma10'] = df.groupby('ticker')['adj_close'].transform(lambda x: x.rolling(10).mean())
        df['ma20'] = df.groupby('ticker')['adj_close'].transform(lambda x: x.rolling(20).mean())

        df['close_ratio_10'] = df['adj_close'] / (df['ma10'] + 1e-9)
        df['close_ratio_20'] = df['adj_close'] / (df['ma20'] + 1e-9)

        # 변동성 활동성 지표
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                (df['high'] - df.groupby('ticker')['adj_close'].shift(1)).abs(),
                (df['low'] - df.groupby('ticker')['adj_close'].shift(1)).abs()
            )
        )

        df['atr_5'] = df.groupby('ticker')['tr'].transform(lambda x: x.rolling(5).mean())
        df['atr_change'] = df.groupby('ticker')['atr_5'].pct_change(fill_method=None)

        # ---------------------------
        # 2. 수익률 및 변동성 (Return & Vol)
        # ---------------------------
        if 'change_rate' in df.columns:
            df['return_1'] = df['change_rate']
            df['return_3'] = df.groupby('ticker')['change_rate'].transform(
                lambda x: (1 + x).rolling(3).apply(np.prod, raw=True) - 1
            )
            df['return_5'] = df.groupby('ticker')['change_rate'].transform(
                lambda x: (1 + x).rolling(5).apply(np.prod, raw=True) - 1
            )
            df['volatility_5'] = df.groupby('ticker')['return_1'].transform(
                lambda x: x.rolling(5).std()
            )
            df['volatility_regime'] = (
                df['volatility_5'] /(
                    df.groupby('ticker')['volatility_5'].transform(lambda x: x.rolling(20).mean()) + 1e-9)
            )


        # ---------------------------
        # 3. 거래량 (Volume)
        # ---------------------------
        if 'volume' in df.columns:
            df['volume_ma5'] = df.groupby('ticker')['volume'].transform(lambda x: x.rolling(5).mean())
            df['volume_ratio'] = df['volume'] / (df['volume_ma5'] + 1e-9)
            df['volume_change'] = df.groupby('ticker')['volume'].pct_change(fill_method=None)
            df['volume_z'] = (
                df['volume'] - df.groupby('ticker')['volume'].transform(lambda x: x.rolling(10).mean())
            ) / (df.groupby('ticker')['volume'].transform(lambda x: x.rolling(10).std()) + 1e-9)

            df['volume_shock'] = df['volume_z'].rolling(3).max()
        # ---------------------------
        # 4. 로그수익률 및 모멘텀
        # ---------------------------
        df['log_return'] = np.log(df['adj_close']) - np.log(df.groupby('ticker')['adj_close'].shift(1))

        # 주주의 기억 오염 방지를 위해 각 종목방 안에서만 롤링 연산 수행하도록 수정!
        df['momentum_3'] = df.groupby('ticker')['log_return'].transform(lambda x: x.rolling(3).sum())
        df['momentum_5'] = df.groupby('ticker')['log_return'].transform(lambda x: x.rolling(5).sum())
        df['momentum_accel_3'] = (
        df.groupby('ticker')['momentum_3']
            .transform(lambda x: x.diff().rolling(3).mean())
        )

        df['momentum_accel_5'] = (
            df.groupby('ticker')['momentum_5']
            .transform(lambda x: x.diff().rolling(5).mean())
        )

        # 캔들 구조 변수들
        df['candle_body'] = (df['adj_close'] - df['open']) / (df['open'] + 1e-9)
        df['high_low_spread'] = (df['high'] - df['low']) / (df['adj_close'] + 1e-9)

        df['high_10'] = df.groupby('ticker')['adj_close'].transform(lambda x: x.rolling(10).max())
        df['breakout_pressure'] = df['adj_close'] / (df['high_10'] + 1e-9)

        # ---------------------------
        # 5. 실전용 찐 정답지 라벨링 [★마진 2% 절대평가 복원]
        # ---------------------------
        # 모델이 신뢰하는 '3일 내 2.0% 상승 마진' 절대 기준으로 원상복구합니다.
        # 고가(high) 기준 3일 내 최고점이 오늘 종가 대비 2% 이상 튀었는지 확인
        df['future_max_high_3d'] = df.groupby('ticker')['high'].transform(
            lambda x: x.shift(-3).rolling(3, min_periods=1).max()
        )
        df['label'] = (df['future_max_high_3d'] / df['adj_close'] - 1 >= 0.02).astype(int)

        # ---------------------------
        # 6. 컬럼 필터링 및 데이터 정리
        # ---------------------------
        meta_cols = ['ticker', 'date']
        feature_cols = [
            'log_return', 'return_3', 'return_5', 'momentum_3', 'momentum_5','momentum_accel_3', 'momentum_accel_5',
            'close_ratio_10', 'close_ratio_20', 'atr_5', 'atr_change',
            'volume_ratio', 'volume_change', 'candle_body', 'high_low_spread',
            'label', 'volume_shock', 'volatility_regime', 'breakout_pressure'
        ]

        df = df[meta_cols + feature_cols]

        # 결측치 제거 (타겟라벨 제외한 순수 피처 기준)
        feature_only = [c for c in feature_cols if c != 'label']
        df = df.dropna(subset=feature_only)

        # 시퀀스 길이(20일) 채울 수 있는 우량 데이터만 남기기
        window_size = 20
        df = df.groupby('ticker').filter(lambda x: len(x) >= window_size).reset_index(drop=True)

        return df

if __name__ == "__main__":
    processor = FeatureProcessor()
    df = processor.get_raw_data()
    df = processor.calc_technical_indicators(df)

    today = datetime.now().strftime("%Y%m%d")
    df.to_csv(
        f"feature__indicator_lstm{today}.csv",
        index=False,
        encoding="utf-8-sig"
    )
    print(df.shape)
    print(
    df[['ticker', 'date']].duplicated().sum()
    )
    print(
        df[['ticker', 'date']]
        .value_counts()
        .head(20)
    )
    print(df.head())

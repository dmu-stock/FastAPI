import pandas as pd
import os
import numpy as np
import joblib
from app.config.config import GBM_FEATURE_COLS
import lightgbm as lgb
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    roc_auc_score
)

# -----------------------------
# 데이터 로드
# -----------------------------
df_tech = pd.read_csv("feature__indicator_20260527.csv")

# 날짜 타입 변환
df_tech['date'] = pd.to_datetime(df_tech['date'])

# -----------------------------
# Feature 선택
# -----------------------------
feature_cols = GBM_FEATURE_COLS

target_col = 'label'

# -----------------------------
# Train / Val / Test Split
# -----------------------------
train = df_tech[df_tech['date'] < '2024-07-01']
val   = df_tech[(df_tech['date'] >= '2024-07-01') & 
                (df_tech['date'] < '2025-07-01')]
test  = df_tech[df_tech['date'] >= '2025-07-01']

X_train, y_train = train[feature_cols], train[target_col]
X_val,   y_val   = val[feature_cols],   val[target_col]
X_test,  y_test  = test[feature_cols],  test[target_col]

print(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
print(f"Train 양성비율: {y_train.mean():.4f}")
print(f"Val   양성비율: {y_val.mean():.4f}")
print(f"Test  양성비율: {y_test.mean():.4f}")

# -----------------------------
# LightGBM 모델 생성
# -----------------------------
model = LGBMClassifier(
    n_estimators=2000,
    learning_rate=0.005,
    max_depth=6,
    num_leaves=20,
    min_data_in_leaf=80,
    feature_fraction=0.7,
    subsample=0.7,
    subsample_freq=1,
    colsample_bytree=0.7,
    lambda_l1=0.1,
    lambda_l2=0.1,
    objective='binary',
    boosting_type='gbdt',
    force_col_wise=True,
    random_state=42,
    class_weight='balanced',
    verbose=-1,
)

# -----------------------------
# 학습
# -----------------------------
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    callbacks=[
        early_stopping(stopping_rounds=50),
        log_evaluation(100)
    ]
)
print(f"\n최적 트리 수: {model.best_iteration_}")
joblib.dump(model, 'best_lgbm_model.pkl')

# -----------------------------
# 예측
# -----------------------------
pred = model.predict(X_test)

# 상승 확률
pred_prob = model.predict_proba(X_test)[:, 1]
threshold = 0.55
pred = (pred_prob >= threshold).astype(int)

# -----------------------------
# 평가
# -----------------------------
print("\n===== Classification Report =====")
print(classification_report(y_test, pred))

print(f"Accuracy : {accuracy_score(y_test, pred):.4f}")
print(f"ROC-AUC  : {roc_auc_score(y_test, pred_prob):.4f}")

# -----------------------------
# Feature Importance
# -----------------------------
importance_df = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values(by='importance', ascending=False)

print("\n===== Feature Importance =====")
print(importance_df)

# -----------------------------
# 예측 결과 저장
# -----------------------------
result_df = test[['ticker', 'date']].copy()

result_df['actual'] = y_test.values
result_df['pred'] = pred
result_df['pred_prob'] = pred_prob

# -----------------------------
# 날짜별 상대 점수(Z-score)
# -----------------------------
result_df['rank_score'] = (
    result_df.groupby('date')['pred_prob']
    .transform(
        lambda x: (x - x.mean()) / (x.std() + 1e-9)
    )
)
# -----------------------------
# 날짜별 Top50 성능
# -----------------------------
daily_scores = []

for date, group in result_df.groupby("date"):

    top50 = group.sort_values(
        "rank_score",
        ascending=False
    ).head(50)

    hit_rate = top50["actual"].mean()

    daily_scores.append(hit_rate)

print("\n===== Daily Top50 Mean =====")
print(np.mean(daily_scores))

# -----------------------------
# 전체 기준 Top-K
# -----------------------------
print("\n===== Top-K Performance =====")
for k in [3, 5, 10]:
    daily_actuals = []
    
    for date, group in result_df.groupby('date'):
        top_k = group.sort_values('rank_score', ascending=False).head(k)
        daily_actuals.extend(top_k['actual'].tolist())
    
    hit_rate = np.mean(daily_actuals)
    print(f"날짜별 Top{k} 평균 타율: {hit_rate:.4f}  "
          f"(베이스라인 대비 {hit_rate/result_df['actual'].mean():.2f}배)")

print(f"베이스라인: {result_df['actual'].mean():.4f}")



result_df.to_csv("prediction_result.csv", index=False)

print("\nprediction_result.csv 저장 완료")
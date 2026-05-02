from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ['puissance_brute_kw', 'gaz_debit_nm3h', 'eg_puissance_kw', 'ec_recup_puissance_kw']


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds/updates 'is_anomaly' and 'anomaly_type' columns.
    Runs: Z-score → IQR → Isolation Forest → stuck sensor → dropout.
    """
    result = df.copy()
    result['is_anomaly'] = result.get('is_anomaly', False).astype(bool)
    if 'anomaly_type' not in result.columns:
        result['anomaly_type'] = None

    feature_cols = [c for c in FEATURES if c in result.columns]
    if not feature_cols:
        return result

    def _flag(mask: pd.Series, atype: str):
        new = mask & ~result['is_anomaly']
        result.loc[new, 'anomaly_type'] = atype
        result.loc[mask, 'is_anomaly'] = True

    # 1. Z-score ±3σ
    for col in feature_cols:
        series = result[col].dropna()
        if len(series) < 10:
            continue
        z = (result[col] - series.mean()) / (series.std() + 1e-9)
        _flag(z.abs() > 3, 'zscore_spike')

    # 2. IQR 1.5×
    for col in feature_cols:
        series = result[col].dropna()
        if len(series) < 10:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        mask = (result[col] < q1 - 1.5 * iqr) | (result[col] > q3 + 1.5 * iqr)
        _flag(mask.fillna(False), 'iqr_outlier')

    # 3. Isolation Forest (multivariate)
    X = result[feature_cols].dropna()
    if len(X) > 50:
        iso = IsolationForest(contamination=0.05, random_state=42, n_jobs=-1)
        preds = iso.fit_predict(X)
        iso_mask = pd.Series(preds == -1, index=X.index).reindex(result.index, fill_value=False)
        _flag(iso_mask, 'isolation_forest')

    # 4. Stuck sensor: rolling std == 0 over 6 consecutive readings
    for col in feature_cols:
        rolling_std = result[col].rolling(6, min_periods=6).std()
        _flag((rolling_std == 0).fillna(False), 'stuck_sensor')

    # 5. Dropout: null run > 3
    for col in feature_cols:
        null_mask = result[col].isna()
        groups = (~null_mask).cumsum()
        run_lengths = null_mask.groupby(groups).transform('sum')
        _flag((run_lengths > 3) & null_mask, 'dropout')

    return result

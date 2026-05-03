import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import timedelta

def generate_forecast(df: pd.DataFrame, horizon_hours: int = 24) -> pd.DataFrame:
    """
    Trains a simple Random Forest on historical data to forecast the next `horizon_hours`.
    Predicts 'puissance_brute_kw' and 'gaz_debit_nm3h'.
    Returns a dataframe with future timestamps and predictions.
    """
    if df.empty or 'timestamp' not in df.columns:
        return pd.DataFrame()

    df = df.dropna(subset=['timestamp']).copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Needs some minimum amount of data to forecast
    if len(df) < 50:
        return pd.DataFrame()
        
    targets = ['puissance_brute_kw', 'gaz_debit_nm3h']
    models = {}
    
    # Feature engineering for time series
    df['hour'] = df['timestamp'].dt.hour
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['day'] = df['timestamp'].dt.day
    
    X = df[['hour', 'dayofweek', 'day']]
    
    for target in targets:
        if target in df.columns and df[target].notna().sum() > 20:
            y = df[target].fillna(method='ffill').fillna(method='bfill')
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            models[target] = model
            
    if not models:
        return pd.DataFrame()

    last_ts = df['timestamp'].max()
    future_dates = [last_ts + timedelta(hours=i) for i in range(1, horizon_hours + 1)]
    future_df = pd.DataFrame({'timestamp': future_dates})
    future_df['hour'] = future_df['timestamp'].dt.hour
    future_df['dayofweek'] = future_df['timestamp'].dt.dayofweek
    future_df['day'] = future_df['timestamp'].dt.day
    
    X_future = future_df[['hour', 'dayofweek', 'day']]
    
    for target, model in models.items():
        future_df[f'pred_{target}'] = model.predict(X_future)
        
    # Also estimate CO2 for the forecast
    if 'pred_puissance_brute_kw' in future_df.columns and 'pred_gaz_debit_nm3h' in future_df.columns:
        # Roughly: puissance_brute_kw * 1h = kWh -> * 0.267
        # gaz_debit_nm3h * 1h = Nm3 -> * 9.082 * 1.163 * 0.202
        future_df['pred_co2_kg'] = (future_df['pred_puissance_brute_kw'] * 0.267) + \
                                   (future_df['pred_gaz_debit_nm3h'] * 9.082 * 1.163 * 0.202)
                                   
    return future_df

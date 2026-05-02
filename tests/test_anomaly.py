import pandas as pd
import numpy as np
from anomaly import detect_anomalies


def _make_df(n=200, spike_idx=50):
    """Creates a DataFrame with one obvious spike at spike_idx."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        'id': range(n),
        'puissance_brute_kw': rng.normal(1200, 20, n),
        'gaz_debit_nm3h': rng.normal(272, 2, n),
        'eg_puissance_kw': rng.normal(260, 15, n),
        'ec_recup_puissance_kw': rng.normal(450, 30, n),
        'is_anomaly': False,
        'anomaly_type': None,
    })
    df.loc[spike_idx, 'puissance_brute_kw'] = 5000.0
    return df


def test_spike_detected():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    assert result.loc[50, 'is_anomaly'] is True or result.loc[50, 'is_anomaly'] == True


def test_normal_records_mostly_clean():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    anomaly_rate = result['is_anomaly'].mean()
    assert anomaly_rate < 0.15


def test_stuck_sensor_detected():
    df = _make_df()
    # Force all 8 values to be identical (0 variance)
    df.loc[10:17, 'puissance_brute_kw'] = 999.999
    result = detect_anomalies(df)
    # At least one of these should be flagged as stuck sensor
    stuck_flags = result.loc[10:17, 'is_anomaly'].sum()
    assert stuck_flags > 0


def test_dropout_detected():
    df = _make_df()
    df.loc[20:24, 'gaz_debit_nm3h'] = np.nan
    result = detect_anomalies(df)
    assert result.loc[22, 'is_anomaly'] is True or result.loc[22, 'is_anomaly'] == True


def test_output_has_anomaly_type():
    df = _make_df(spike_idx=50)
    result = detect_anomalies(df)
    assert result.loc[50, 'anomaly_type'] is not None

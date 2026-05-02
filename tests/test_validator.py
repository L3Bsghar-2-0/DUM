import os
from validator import validate_batch, _rule_validate
from extractors.base import ExtractionResult


def _make_record(**kwargs) -> ExtractionResult:
    return ExtractionResult(source_file="f.xlsx", source_type="excel", **kwargs)


def test_rule_validate_good_record():
    r = _make_record(
        voltage_v=408.0, facteur_puissance=0.98, gaz_debit_nm3h=272.0,
        gaz_volume_nm3=2024472.0, puissance_brute_kw=1199.0,
        energie_alternateur_kwh=9070710.0, eg_puissance_kw=230.0,
        ec_recup_puissance_kw=587.0, steg_achat_kwh=788205.0
    )
    out = _rule_validate(r)
    assert out.confidence_score >= 0.5
    assert 'voltage_out_of_range' not in ' '.join(out.extraction_warnings)


def test_rule_validate_bad_voltage():
    r = _make_record(voltage_v=500.0)
    out = _rule_validate(r)
    assert any('voltage' in w for w in out.extraction_warnings)


def test_rule_validate_bad_power_factor():
    r = _make_record(facteur_puissance=0.5)
    out = _rule_validate(r)
    assert any('facteur_puissance' in w for w in out.extraction_warnings)


def test_rule_validate_bad_gas_flow():
    r = _make_record(gaz_debit_nm3h=500.0)
    out = _rule_validate(r)
    assert any('gaz_debit' in w for w in out.extraction_warnings)


def test_validate_batch_no_api_key_uses_rule_mode():
    records = [_make_record(voltage_v=408.0), _make_record(voltage_v=600.0)]
    out = validate_batch(records, api_key=None)
    assert len(out) == 2
    assert out[0].confidence_score >= 0.0
    assert out[1].confidence_score < out[0].confidence_score or \
           any('voltage' in w for w in out[1].extraction_warnings)

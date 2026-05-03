from __future__ import annotations
import json
import os
from extractors.base import ExtractionResult

_BOUNDS: dict[str, tuple[float, float]] = {
    'voltage_v': (380.0, 440.0),
    'facteur_puissance': (0.90, 1.0),
    'gaz_debit_nm3h': (200.0, 300.0),
    'puissance_brute_kw': (800.0, 1400.0),
    'vitesse_rpm': (1400.0, 1600.0),
    'eg_temp_entree_c': (3.0, 15.0),
    'eg_temp_sortie_c': (5.0, 20.0),
    'ec_recup_temp_entree_c': (90.0, 105.0),
    'rendement_electrique_pct': (30.0, 55.0),
    'rendement_total_pct': (50.0, 90.0),
}


def _rule_validate(record: ExtractionResult) -> ExtractionResult:
    warnings = list(record.extraction_warnings)
    violations = 0
    for field, (lo, hi) in _BOUNDS.items():
        val = getattr(record, field, None)
        if val is not None and not (lo <= val <= hi):
            warnings.append(f"{field}_out_of_range: {val} not in [{lo}, {hi}]")
            violations += 1

    coverage = record.field_coverage()
    penalty = violations * 0.1
    confidence = max(coverage - penalty, 0.0)

    data = record.model_dump()
    data['confidence_score'] = confidence
    data['extraction_warnings'] = warnings
    return ExtractionResult(**data)


def _llm_validate_batch(records: list[ExtractionResult], api_key: str) -> list[ExtractionResult]:
    """Uses DeepSeek v4 (via Nvidia NIM) to validate batch logic."""
    from openai import OpenAI
    import json
    
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
    
    # Pre-calculate rule violations as baseline
    records = [_rule_validate(r) for r in records]
    
    # Skip slow LLM API call during unit tests
    if os.getenv("PYTEST_CURRENT_TEST"):
        return records
        
    # We only send a subset of info to LLM to save tokens
    payload = []
    for r in records:
        d = r.model_dump(exclude_none=True)
        payload.append({
            "id": r.source_file + str(r.timestamp),
            "puissance": d.get("puissance_brute_kw"),
            "gaz_nm3h": d.get("gaz_debit_nm3h"),
            "rendement": d.get("rendement_electrique_pct")
        })
        
    prompt = (
        "You are an energy auditor. Review these records for physical impossibilities "
        "(e.g., efficiency > 55%, power > 1500kW but low gas, etc). "
        "Return ONLY a JSON list of objects with {'id': str, 'has_error': bool, 'reason': str}. "
        f"Records: {json.dumps(payload)}"
    )
    
    try:
        response = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"): content = content[7:-3]
        elif content.startswith("```"): content = content[3:-3]
        llm_results = json.loads(content.strip())
        
        # Merge back
        error_map = {item['id']: item for item in llm_results if isinstance(item, dict)}
        for r in records:
            rid = r.source_file + str(r.timestamp)
            if rid in error_map and error_map[rid].get('has_error'):
                r.extraction_warnings.append(f"LLM_Flag: {error_map[rid].get('reason')}")
                r.confidence_score = max(r.confidence_score - 0.2, 0.0)
    except Exception as e:
        print(f"LLM validate error: {e}")
        
    return records


def validate_batch(
    records: list[ExtractionResult],
    api_key: str | None = None,
) -> list[ExtractionResult]:
    key = api_key or os.getenv("NVIDIA_API_KEY", "")
    
    if not key:
        return [_rule_validate(r) for r in records]

    # Rule validate all records, but only send non-excel records to LLM
    # Sending thousands of Excel rows to an LLM will hang the pipeline and API
    excel_records = [_rule_validate(r) for r in records if r.source_type == "excel"]
    llm_candidates = [r for r in records if r.source_type != "excel"]
    
    BATCH = 50
    llm_results = []
    for i in range(0, len(llm_candidates), BATCH):
        batch = llm_candidates[i:i + BATCH]
        llm_results.extend(_llm_validate_batch(batch, key))
        
    return excel_records + llm_results

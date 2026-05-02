from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

COVERAGE_FIELDS = [
    'gaz_volume_nm3', 'gaz_debit_nm3h', 'puissance_brute_kw',
    'energie_alternateur_kwh', 'eg_puissance_kw', 'ec_recup_puissance_kw',
    'steg_achat_kwh', 'steg_vente_kwh', 'production_positive_kwh',
]

class ExtractionResult(BaseModel):
    # Metadata
    timestamp: Optional[datetime] = None
    source_file: str
    source_type: str  # excel / pdf / image
    confidence_score: float = 0.0
    is_anomaly: bool = False
    anomaly_type: Optional[str] = None
    co2_kg: Optional[float] = None
    extraction_warnings: list[str] = []
    pci_thermie_nm3: float = 9.082
    cos_phi: float = 1.0

    # Gas
    gaz_volume_nm3: Optional[float] = None
    gaz_debit_nm3h: Optional[float] = None

    # Electrical
    elec_auxiliaire_kwh: Optional[float] = None
    puissance_brute_kw: Optional[float] = None
    heures_fonctionnement: Optional[float] = None
    energie_alternateur_kwh: Optional[float] = None
    energie_reactive_kvarh: Optional[float] = None
    vitesse_rpm: Optional[float] = None
    facteur_puissance: Optional[float] = None
    voltage_v: Optional[float] = None
    courant_phase1_a: Optional[float] = None
    courant_phase2_a: Optional[float] = None
    courant_phase3_a: Optional[float] = None

    # Chilled water (absorption)
    eg_debit_m3h: Optional[float] = None
    eg_temp_entree_c: Optional[float] = None
    eg_temp_sortie_c: Optional[float] = None
    eg_energie_kwh: Optional[float] = None
    eg_puissance_kw: Optional[float] = None

    # Recovered hot water
    ec_recup_debit_m3h: Optional[float] = None
    ec_recup_temp_entree_c: Optional[float] = None
    ec_recup_temp_sortie_c: Optional[float] = None
    ec_recup_energie_kwh: Optional[float] = None
    ec_recup_puissance_kw: Optional[float] = None

    # Hot water Alpha Sanitaire
    ec_alpha_sani_debit_m3h: Optional[float] = None
    ec_alpha_sani_temp_entree_c: Optional[float] = None
    ec_alpha_sani_temp_sortie_c: Optional[float] = None
    ec_alpha_sani_energie_kwh: Optional[float] = None
    ec_alpha_sani_puissance_kw: Optional[float] = None

    # Hot water Alpha
    ec_alpha_debit_m3h: Optional[float] = None
    ec_alpha_temp_entree_c: Optional[float] = None
    ec_alpha_temp_sortie_c: Optional[float] = None
    ec_alpha_energie_kwh: Optional[float] = None
    ec_alpha_puissance_kw: Optional[float] = None

    # Hot water Gamma
    ec_gamma_debit_m3h: Optional[float] = None
    ec_gamma_temp_entree_c: Optional[float] = None
    ec_gamma_temp_sortie_c: Optional[float] = None
    ec_gamma_energie_kwh: Optional[float] = None
    ec_gamma_puissance_kw: Optional[float] = None

    # Efficiencies
    rendement_electrique_pct: Optional[float] = None
    rendement_thermique_pct: Optional[float] = None
    rendement_total_pct: Optional[float] = None

    # STEG grid
    steg_achat_kwh: Optional[float] = None
    steg_vente_kwh: Optional[float] = None
    production_positive_kwh: Optional[float] = None
    production_negative_kwh: Optional[float] = None

    def field_coverage(self) -> float:
        filled = sum(1 for f in COVERAGE_FIELDS if getattr(self, f) is not None)
        return filled / len(COVERAGE_FIELDS)

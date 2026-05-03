from __future__ import annotations
import json
from datetime import datetime
import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean, DateTime,
    Text, update
)
from sqlalchemy.orm import DeclarativeBase, Session
from extractors.base import ExtractionResult


class Base(DeclarativeBase):
    pass


class EnergyRecord(Base):
    __tablename__ = "energy_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=True)
    source_file = Column(String, index=True)
    source_type = Column(String)
    confidence_score = Column(Float, default=0.0)
    is_anomaly = Column(Boolean, default=False)
    anomaly_type = Column(String, nullable=True)
    anomaly_confidence = Column(Float, nullable=True)
    site = Column(String, default="Main Factory")
    co2_kg = Column(Float, nullable=True)
    extraction_warnings = Column(Text, nullable=True)
    pci_thermie_nm3 = Column(Float, default=9.082)
    cos_phi = Column(Float, default=1.0)

    gaz_volume_nm3 = Column(Float, nullable=True)
    gaz_debit_nm3h = Column(Float, nullable=True)

    elec_auxiliaire_kwh = Column(Float, nullable=True)
    puissance_brute_kw = Column(Float, nullable=True)
    heures_fonctionnement = Column(Float, nullable=True)
    energie_alternateur_kwh = Column(Float, nullable=True)
    energie_reactive_kvarh = Column(Float, nullable=True)
    vitesse_rpm = Column(Float, nullable=True)
    facteur_puissance = Column(Float, nullable=True)
    voltage_v = Column(Float, nullable=True)
    courant_phase1_a = Column(Float, nullable=True)
    courant_phase2_a = Column(Float, nullable=True)
    courant_phase3_a = Column(Float, nullable=True)

    eg_debit_m3h = Column(Float, nullable=True)
    eg_temp_entree_c = Column(Float, nullable=True)
    eg_temp_sortie_c = Column(Float, nullable=True)
    eg_energie_kwh = Column(Float, nullable=True)
    eg_puissance_kw = Column(Float, nullable=True)

    ec_recup_debit_m3h = Column(Float, nullable=True)
    ec_recup_temp_entree_c = Column(Float, nullable=True)
    ec_recup_temp_sortie_c = Column(Float, nullable=True)
    ec_recup_energie_kwh = Column(Float, nullable=True)
    ec_recup_puissance_kw = Column(Float, nullable=True)

    ec_alpha_sani_debit_m3h = Column(Float, nullable=True)
    ec_alpha_sani_temp_entree_c = Column(Float, nullable=True)
    ec_alpha_sani_temp_sortie_c = Column(Float, nullable=True)
    ec_alpha_sani_energie_kwh = Column(Float, nullable=True)
    ec_alpha_sani_puissance_kw = Column(Float, nullable=True)

    ec_alpha_debit_m3h = Column(Float, nullable=True)
    ec_alpha_temp_entree_c = Column(Float, nullable=True)
    ec_alpha_temp_sortie_c = Column(Float, nullable=True)
    ec_alpha_energie_kwh = Column(Float, nullable=True)
    ec_alpha_puissance_kw = Column(Float, nullable=True)

    ec_gamma_debit_m3h = Column(Float, nullable=True)
    ec_gamma_temp_entree_c = Column(Float, nullable=True)
    ec_gamma_temp_sortie_c = Column(Float, nullable=True)
    ec_gamma_energie_kwh = Column(Float, nullable=True)
    ec_gamma_puissance_kw = Column(Float, nullable=True)

    rendement_electrique_pct = Column(Float, nullable=True)
    rendement_thermique_pct = Column(Float, nullable=True)
    rendement_total_pct = Column(Float, nullable=True)

    steg_achat_kwh = Column(Float, nullable=True)
    steg_vente_kwh = Column(Float, nullable=True)
    production_positive_kwh = Column(Float, nullable=True)
    production_negative_kwh = Column(Float, nullable=True)


def _record_to_row(r: ExtractionResult) -> dict:
    data = r.model_dump()
    data['extraction_warnings'] = json.dumps(data.get('extraction_warnings', []))
    return data


def write_records(engine, records: list[ExtractionResult]) -> None:
    rows = [_record_to_row(r) for r in records]
    with Session(engine) as session:
        session.bulk_insert_mappings(EnergyRecord, rows)
        session.commit()


def read_all_records(engine) -> pd.DataFrame:
    with Session(engine) as session:
        rows = session.query(EnergyRecord).all()
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([{
            c.name: getattr(row, c.name)
            for c in EnergyRecord.__table__.columns
        } for row in rows])


def update_anomaly_flags(engine, df: pd.DataFrame) -> None:
    with Session(engine) as session:
        for _, row in df.iterrows():
            session.execute(
                update(EnergyRecord)
                .where(EnergyRecord.id == int(row['id']))
                .values(
                    is_anomaly=bool(row.get('is_anomaly', False)),
                    anomaly_type=row.get('anomaly_type'),
                    anomaly_confidence=row.get('anomaly_confidence'),
                )
            )
        session.commit()

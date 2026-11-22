"""Pruebas de la segmentación de centros (técnica analítica justificada del checklist)."""
import numpy as np
import pandas as pd

from edualerta.db import sql
from edualerta.services import segmentation


def test_segmentation_is_reproducible_and_complete(loaded):
    conn = loaded["conn"]
    feats = segmentation.center_features(conn, "2025-T3", sql.get_rules(conn))
    assert len(feats) == 32
    a = segmentation.segment(feats)
    b = segmentation.segment(feats)
    assert a["k"] == b["k"] and (a["centros"]["grupo"] == b["centros"]["grupo"]).all()   # semilla fija
    assert 2 <= a["k"] <= 5 and -1 <= a["silueta"] <= 1
    assert set(a["centros"]["grupo"]) == set(range(1, a["k"] + 1))
    assert sum(g["centros"] for g in a["grupos"]) == 32
    assert all(g["perfil"] for g in a["grupos"])


def test_groups_ordered_by_need_and_separate_obvious_clusters():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(10):   # centros en rezago
        rows.append({"centro_codigo": f"A{i}", "estudiantes": 15, "asistencia_pct": 80 + rng.normal(0, 1),
                     "promedio": 62 + rng.normal(0, 1), "prioritarios_pct": 30 + rng.normal(0, 1),
                     "dispositivos_por_estudiante": 0.05, "tiene_internet": 0})
    for i in range(10):   # centros favorables
        rows.append({"centro_codigo": f"B{i}", "estudiantes": 15, "asistencia_pct": 97 + rng.normal(0, 1),
                     "promedio": 88 + rng.normal(0, 1), "prioritarios_pct": 1 + rng.normal(0, 0.5),
                     "dispositivos_por_estudiante": 0.6, "tiene_internet": 1})
    seg = segmentation.segment(pd.DataFrame(rows), k=2)
    c = seg["centros"]
    assert c[c["centro_codigo"].str.startswith("A")]["grupo"].nunique() == 1
    assert (c[c["centro_codigo"].str.startswith("A")]["grupo"] == 1).all()   # grupo 1 = mayor necesidad
    assert seg["grupos"][0]["perfil"] == "Rezago académico y brecha tecnológica"
    assert seg["silueta"] > 0.7

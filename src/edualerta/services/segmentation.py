"""Segmentación de centros educativos por perfil de necesidad (técnica analítica del checklist).

Por qué: las reglas de alerta miran a cada estudiante por separado. La dirección necesita además
agrupar centros con necesidades parecidas para diseñar intervenciones por tipo (tutoría, dotación
tecnológica, asistencia) en vez de una sola respuesta para todos.

Cómo: k-means sobre indicadores estandarizados (z-score) por centro, inicialización k-means++ con
semilla fija (reproducible) y elección de k por el coeficiente de silueta. Cada grupo se describe
por cómo se aparta su centroide del promedio, para que la interpretación sea explicable.

Límites: con ~32 centros sintéticos los grupos son demostrativos; orientan el análisis, no
reemplazan el criterio de la dirección.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from edualerta.services import indicators, tech

FEATURES = {
    "asistencia_pct": ("asistencia", True),
    "promedio": ("promedio académico", True),
    "prioritarios_pct": ("estudiantes prioritarios", False),
    "dispositivos_por_estudiante": ("dispositivos por estudiante", True),
    "tiene_internet": ("conectividad", True),
}
SEED = 2025


def center_features(conn: sqlite3.Connection, periodo: str, rules: dict) -> pd.DataFrame:
    ind = indicators.indicator_frame(conn, periodo)
    if ind.empty:
        return pd.DataFrame()
    g = ind.groupby(["centro_codigo", "centro_nombre", "region_nombre", "zona"])
    df = pd.DataFrame({
        "estudiantes": g["estudiante_codigo"].count(),
        "asistencia_pct": g["dias_asistidos"].sum() / g["dias_programados"].sum() * 100,
        "promedio": g["promedio"].mean(),
        "prioritarios_pct": g["nivel_alerta"].apply(lambda s: (s == "prioritario").mean() * 100),
    }).reset_index()
    res = tech.resources_frame(conn, periodo, rules)
    if res.empty:
        return pd.DataFrame()
    df = df.merge(res[["centro_codigo", "dispositivos_por_estudiante", "tiene_internet"]], on="centro_codigo")
    return df.dropna(subset=list(FEATURES)).reset_index(drop=True)


def _kmeans(x: np.ndarray, k: int, rng: np.random.Generator, iters: int = 100) -> tuple[np.ndarray, np.ndarray]:
    # k-means++
    centers = [x[rng.integers(len(x))]]
    for _ in range(1, k):
        d2 = np.min(((x[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        probs = d2 / d2.sum() if d2.sum() > 0 else np.full(len(x), 1 / len(x))
        centers.append(x[rng.choice(len(x), p=probs)])
    c = np.array(centers)
    labels = np.zeros(len(x), dtype=int)
    for _ in range(iters):
        labels_new = ((x[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        if (labels_new == labels).all() and _ > 0:
            break
        labels = labels_new
        for j in range(k):
            if (labels == j).any():
                c[j] = x[labels == j].mean(0)
    return labels, c


def silhouette(x: np.ndarray, labels: np.ndarray) -> float:
    d = np.sqrt(((x[:, None, :] - x[None]) ** 2).sum(-1))
    scores = []
    for i in range(len(x)):
        same = labels == labels[i]
        if same.sum() <= 1:
            scores.append(0.0)
            continue
        a = d[i, same].sum() / (same.sum() - 1)
        b = min(d[i, labels == j].mean() for j in set(labels) if j != labels[i])
        scores.append((b - a) / max(a, b))
    return float(np.mean(scores))


def segment(df: pd.DataFrame, k: int | None = None) -> dict:
    """Devuelve centros con su grupo, descripción de cada grupo y la silueta por k evaluado."""
    cols = list(FEATURES)
    x = df[cols].to_numpy(float)
    mu, sd = x.mean(0), x.std(0)
    sd[sd == 0] = 1
    z = (x - mu) / sd
    candidates = [k] if k else [k_ for k_ in range(2, 6) if k_ < len(df)]
    best, scores = None, {}
    for k_ in candidates:
        runs = [_kmeans(z, k_, np.random.default_rng(SEED + r)) for r in range(10)]
        labels, cent = min(runs, key=lambda lc: ((z - lc[1][lc[0]]) ** 2).sum())
        s = silhouette(z, labels)
        scores[k_] = round(s, 3)
        if best is None or s > best[0]:
            best = (s, k_, labels, cent)
    s, k_best, labels, cent = best
    # ordenar grupos de mayor a menor necesidad (puntaje compuesto)
    need = [-(c[0] + c[1] - c[2] + c[3] + c[4]) for c in cent]
    order = np.argsort(need)[::-1]
    remap = {old: new for new, old in enumerate(order)}
    out = df.copy()
    out["grupo"] = [remap[l] + 1 for l in labels]
    groups = []
    for new, old in enumerate(order):
        c = cent[old]
        traits = []
        for (col, (name, higher_good)), zval in sorted(zip(FEATURES.items(), c), key=lambda t: -abs(t[1])):
            if abs(zval) < 0.5:
                continue
            good = (zval > 0) == higher_good
            traits.append(("mejor" if good else "peor", name, zval))
        members = out[out["grupo"] == new + 1]
        groups.append({
            "grupo": new + 1, "centros": len(members), "estudiantes": int(members["estudiantes"].sum()),
            "rasgos": traits[:3],
            "perfil": _name(traits),
            **{col: round(float(members[col].mean()), 2) for col in cols},
        })
    # nombres únicos: si dos grupos comparten perfil, se distinguen por su rasgo más marcado
    seen = {}
    for g in groups:
        seen.setdefault(g["perfil"], []).append(g)
    for perfil, gs in seen.items():
        if len(gs) > 1:
            for g in gs:
                if g["rasgos"]:
                    t, n, _ = g["rasgos"][0]
                    more = (t == "mejor") != (n == "estudiantes prioritarios")
                    g["perfil"] = f"{perfil}: {'más' if more else 'menos'} {n}"
    return {"centros": out, "grupos": groups, "k": k_best, "silueta": round(s, 3), "silueta_por_k": scores}


def _name(traits) -> str:
    bad = [n for t, n, _ in traits if t == "peor"]
    good = [n for t, n, _ in traits if t == "mejor"]
    if not bad and not good:
        return "Perfil promedio"
    if bad and any(n in ("conectividad", "dispositivos por estudiante") for n in bad) and any(
            n in ("asistencia", "promedio académico", "estudiantes prioritarios") for n in bad):
        return "Rezago académico y brecha tecnológica"
    if bad and all(n in ("conectividad", "dispositivos por estudiante") for n in bad):
        return "Brecha tecnológica"
    if bad:
        return "Riesgo académico"
    return "Condiciones favorables"

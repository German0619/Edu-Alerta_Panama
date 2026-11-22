"""Generador determinista de datos sintéticos de demostración (F02, F74, F85).

Produce, con una semilla fija:
  data/raw/   -> carga base 2025 (T1-T3) en CSV, JSON y GeoJSON, con errores de calidad
                 intencionales para que el ETL demuestre limpieza y rechazo de registros.
  data/demo/  -> paquete de carga del período 2026-T1 para subir desde la interfaz
                 durante la sustentación (muestra la evolución posterior a la intervención).

Todos los estudiantes son ficticios y se identifican solo con un código anónimo E-NNNN.
Solo usa la librería estándar para poder ejecutarse en cualquier entorno.
"""
from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

from edualerta import config

SEED = 20250303
DIAS_POR_PERIODO = 50
ASIGNATURAS = ["Español", "Matemáticas", "Ciencias Naturales", "Ciencias Sociales", "Inglés", "Tecnología"]
DEMO_STUDENT = "E-0042"
# Calibración de la población sintética (objetivo aprox.: 10 % prioritario, 20 % preventivo)
HAB_BASE, HAB_CTX, HAB_SD = 76, 14, 11
AUS_BASE, AUS_CTX, AUS_SD = 0.065, 0.07, 0.055

# codigo, nombre, tipo, lat, lon, radio_hex, contexto (0 desfavorable - 1 favorable)
REGIONES = [
    ("BOC", "Bocas del Toro", "provincial", 9.15, -82.25, 0.30, 0.45),
    ("CHI", "Chiriquí", "provincial", 8.45, -82.55, 0.30, 0.75),
    ("CNB", "Comarca Ngäbe-Buglé", "comarcal", 8.65, -81.75, 0.28, 0.20),
    ("VER", "Veraguas", "provincial", 8.15, -81.15, 0.30, 0.55),
    ("HER", "Herrera", "provincial", 7.90, -80.65, 0.18, 0.80),
    ("LSA", "Los Santos", "provincial", 7.55, -80.35, 0.20, 0.80),
    ("COC", "Coclé", "provincial", 8.45, -80.35, 0.25, 0.65),
    ("COL", "Colón", "provincial", 9.25, -80.00, 0.22, 0.55),
    ("POE", "Panamá Oeste", "metropolitana", 8.75, -79.95, 0.18, 0.70),
    ("PNO", "Panamá Norte", "metropolitana", 9.25, -79.55, 0.12, 0.70),
    ("PCE", "Panamá Centro", "metropolitana", 8.98, -79.55, 0.12, 0.90),
    ("SMI", "San Miguelito", "metropolitana", 9.08, -79.36, 0.08, 0.60),
    ("PES", "Panamá Este", "metropolitana", 9.05, -79.00, 0.22, 0.55),
    ("CGY", "Comarca Guna Yala", "comarcal", 9.35, -78.55, 0.20, 0.25),
    ("DAR", "Darién", "provincial", 8.05, -77.75, 0.35, 0.30),
    ("CEW", "Comarca Emberá-Wounaan", "comarcal", 8.55, -77.95, 0.15, 0.20),
]

PERIODOS = [
    ("2025-T1", 2025, 1, date(2025, 3, 3), date(2025, 6, 6)),
    ("2025-T2", 2025, 2, date(2025, 6, 16), date(2025, 9, 12)),
    ("2025-T3", 2025, 3, date(2025, 9, 22), date(2025, 12, 12)),
    ("2026-T1", 2026, 1, date(2026, 3, 2), date(2026, 6, 5)),
]
BASE_PERIODS = PERIODOS[:3]
DEMO_PERIOD = PERIODOS[3]

# Perfil fijo del estudiante demostrativo por período: (ausencias, racha final, notas)
DEMO_PROFILE = {
    "2025-T1": (4, 1, [68, 70, 72, 74, 70, 72]),    # 92 %, 71 -> regular
    "2025-T2": (8, 2, [60, 62, 66, 68, 63, 65]),    # 84 %, 64 -> preventivo
    "2025-T3": (14, 3, [52, 55, 60, 62, 57, 62]),   # 72 %, 58, 3 consecutivas -> prioritario
    "2026-T1": (6, 1, [64, 66, 70, 71, 67, 70]),    # 88 %, 68 -> mejora tras la tutoría
}


def school_days(start: date, end: date, n: int = DIAS_POR_PERIODO) -> list[date]:
    days, d = [], start
    while d <= end and len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def hexagon(lat: float, lon: float, r: float) -> list[list[float]]:
    pts = [[round(lon + r * math.cos(math.radians(a)), 4), round(lat + r * math.sin(math.radians(a)), 4)]
           for a in range(0, 360, 60)]
    return pts + [pts[0]]


def _write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def _attendance_pattern(rng: random.Random, n_days: int, p_abs: float, streak: int) -> list[str]:
    estados = []
    for _ in range(n_days):
        x = rng.random()
        if x < p_abs:
            estados.append("ausente")
        elif x < p_abs + 0.02:
            estados.append("justificada")
        elif x < p_abs + 0.07:
            estados.append("tardanza")
        else:
            estados.append("presente")
    if streak:
        start = rng.randrange(0, n_days - streak)
        for i in range(start, start + streak):
            estados[i] = "ausente"
    return estados


def _demo_attendance(n_days: int, absences: int, final_streak: int) -> list[str]:
    """Ausencias aisladas (separadas por días presentes) + una racha al final del período."""
    estados = ["presente"] * n_days
    isolated = absences - final_streak
    end_block = n_days - final_streak - 1
    step = max(2, end_block // max(isolated, 1))
    pos = 1
    for _ in range(isolated):
        estados[pos] = "ausente"
        pos += step
    for i in range(n_days - final_streak, n_days):
        estados[i] = "ausente"
    return estados


def generate(raw_dir: Path | None = None, demo_dir: Path | None = None, seed: int = SEED) -> dict:
    raw_dir = Path(raw_dir or config.RAW_DIR)
    demo_dir = Path(demo_dir or config.DEMO_DIR)
    rng = random.Random(seed)

    # ------------------------------------------------------------- regiones (GeoJSON)
    features = [{
        "type": "Feature",
        "properties": {"codigo": c, "nombre": n, "tipo": t},
        "geometry": {"type": "Polygon", "coordinates": [hexagon(lat, lon, r)]},
    } for c, n, t, lat, lon, r, _ in REGIONES]
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "regiones.geojson").write_text(json.dumps({
        "type": "FeatureCollection",
        "name": "regiones_educativas_panama_simplificadas",
        "metadata": {"nota": "Geometría hexagonal aproximada para demostración; no son límites oficiales."},
        "features": features,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------------------- centros
    centros = []  # (codigo, nombre, region, zona, dependencia, nivel, contexto)
    n = 0
    for c, nombre, tipo, *_rest, ctx in REGIONES:
        for k in range(2):
            n += 1
            zona = "urbana" if tipo == "metropolitana" or (k == 0 and ctx > 0.5) else "rural"
            dependencia = "particular" if (tipo == "metropolitana" and k == 1 and n % 3 == 0) else "oficial"
            nivel = "premedia" if k == 0 else "media"
            ctx_c = max(0.05, min(0.98, ctx + (0.08 if zona == "urbana" else -0.08)))
            centros.append((f"CE-{n:03d}", f"Centro Educativo {nombre} {k + 1}", c, zona, dependencia, nivel, ctx_c))
    centro_rows = []
    for i, (cod, nom, reg, zona, dep, niv, _) in enumerate(centros):
        if i == 4:   # error intencional: código con espacios y minúsculas -> normalización F16
            cod = f"  {cod.lower()} "
        if i == 6:
            zona = zona.capitalize()
        centro_rows.append([cod, nom, reg, zona, dep, niv])
    # encabezados heterogéneos (se normalizan con alias)
    _write_csv(raw_dir / "centros.csv", ["Código Centro", "Nombre Centro", "Region", "Zona", "Dependencia", "Nivel"],
               centro_rows)

    # ------------------------------------------------------------- períodos
    _write_csv(raw_dir / "periodos.csv", ["codigo", "anio", "trimestre", "fecha_inicio", "fecha_fin"],
               [[c, a, t, i.isoformat(), f.isoformat()] for c, a, t, i, f in PERIODOS])

    # ------------------------------------------------------------- estudiantes y matrículas
    estudiantes = []  # (codigo, genero, anio_nac, centro_idx, grado, habilidad, p_aus)
    sid = 0
    for ci, centro in enumerate(centros):
        ctx = centro[6]
        for _ in range(rng.randint(12, 18)):
            sid += 1
            grado = rng.choice([7, 8, 9]) if centro[5] == "premedia" else rng.choice([10, 11, 12])
            habilidad = rng.gauss(HAB_BASE + HAB_CTX * ctx, HAB_SD)
            p_aus = max(0.0, min(0.35, rng.gauss(AUS_BASE - AUS_CTX * ctx, AUS_SD)))
            estudiantes.append([f"E-{sid:04d}", rng.choice("FM"), 2025 - grado - 6, ci, grado, habilidad, p_aus])
    est_rows = [[e[0], e[1], e[2]] for e in estudiantes]
    est_rows.append(list(est_rows[10]))                        # duplicado exacto
    est_rows.append(["E-9001", "", 2011])                      # género nulo -> rechazo
    est_rows[99][0] = est_rows[99][0].lower()                  # código en minúsculas
    _write_csv(raw_dir / "estudiantes.csv", ["codigo_estudiante", "sexo", "anio_nacimiento"], est_rows)

    mat_rows = []
    for e in estudiantes:
        for pc, *_ in BASE_PERIODS:
            mat_rows.append([e[0], centros[e[3]][0], pc, e[4], "activa"])
    _write_csv(raw_dir / "matriculas.csv", ["estudiante_codigo", "centro_codigo", "periodo_codigo", "grado", "estado"],
               mat_rows)

    # ------------------------------------------------------------- inventario tecnológico
    def inventory_rows(periods, drift: float = 0.0):
        rows = []
        for ci, c in enumerate(centros):
            n_est = sum(1 for e in estudiantes if e[3] == ci)
            ctx = c[6]
            for k, (pc, *_r) in enumerate(periods):
                local = random.Random(seed + ci * 10 + k)
                internet = 1 if local.random() < 0.25 + 0.75 * ctx else 0
                vel = round(local.uniform(20, 150) * ctx, 1) if internet else 0
                comps = int(n_est * max(0.0, local.gauss(0.45 * ctx - 0.05 + drift, 0.05)))
                tabs = int(n_est * max(0.0, local.gauss(0.15 * ctx + drift, 0.04)))
                if c[0] == "CE-021":   # Panamá Centro: alta conectividad (comparación F49)
                    internet, vel, comps, tabs = 1, 150.0, n_est, n_est // 2
                if c[0] == "CE-005":   # Comarca Ngäbe-Buglé: sin conectividad
                    internet, vel, comps, tabs = 0, 0.0, 1, 0
                rows.append([c[0], pc, "si" if internet else "no", vel, comps, tabs])
        return rows

    _write_csv(raw_dir / "inventario_tecnologico.csv",
               ["centro", "periodo", "internet", "velocidad", "computadoras", "tabletas"],
               inventory_rows(BASE_PERIODS))

    # ------------------------------------------------------------- asistencia y calificaciones
    def period_records(period, demo: bool):
        pc, _, _, ini, fin = period
        days = school_days(ini, fin)
        asis, cal = [], []
        for e in estudiantes:
            code = e[0]
            if code == DEMO_STUDENT:
                absences, streak, notas = DEMO_PROFILE[pc]
                estados = _demo_attendance(len(days), absences, streak)
            else:
                drift = {"2025-T1": -0.01, "2025-T2": 0.0, "2025-T3": 0.015, "2026-T1": 0.0}[pc]
                p = max(0.0, e[6] + drift + rng.gauss(0, 0.015))
                streak = rng.choice([0, 0, 0, 0, 2, 3]) if p > 0.15 else 0
                estados = _attendance_pattern(rng, len(days), p, streak)
                base = e[5] - 25 * max(0.0, p - 0.12) + rng.gauss(0, 3)
                notas = [max(0, min(100, round(rng.gauss(base, 8)))) for _ in ASIGNATURAS]
            for d, s in zip(days, estados):
                asis.append([code, d, s])
            for a, nota in zip(ASIGNATURAS, notas):
                cal.append([code, pc, a, nota])
        return asis, cal

    all_asis, all_cal = [], []
    for period in BASE_PERIODS:
        a, c = period_records(period, demo=False)
        all_asis += a
        all_cal += c

    abbreviations = {"presente": "P", "ausente": "A", "justificada": "J", "tardanza": "T"}
    asis_rows = []
    for i, (code, d, s) in enumerate(all_asis):
        fecha = d.strftime("%d/%m/%Y") if i % 7 == 0 else d.isoformat()     # formatos mixtos
        estado = abbreviations[s] if i % 11 == 0 else (s.capitalize() if i % 13 == 0 else s)
        asis_rows.append([code, fecha, estado])
    asis_rows += [
        ["E-9999", "2025-03-04", "presente"],      # estudiante inexistente -> rechazo
        ["E-0003", "2025-06-10", "ausente"],       # fecha entre períodos -> rechazo
        ["E-0004", "2025-13-45", "presente"],      # fecha inválida -> rechazo
        ["E-0005", "2025-03-05", "dormido"],       # estado desconocido -> rechazo
        list(asis_rows[3]),                        # duplicado exacto
    ]
    _write_csv(raw_dir / "asistencias_2025.csv", ["codigo_estudiante", "fecha", "estado"], asis_rows)

    cal_rows = [list(r) for r in all_cal]
    cal_rows += [
        ["E-0007", "2025-T1", "Educación Física", 105],   # fuera de rango
        ["E-0008", "2025-T1", "Educación Física", ""],    # nota nula
        ["E-0009", "2025-T1", "Educación Física", "8O"],  # error de digitación
    ]
    _write_csv(raw_dir / "calificaciones_2025.csv", ["Código Estudiante", "Periodo", "Materia", "Calificación"],
               cal_rows)

    # ------------------------------------------------------------- seguimiento histórico (JSON)
    textos_obs = [
        "Docente reporta desmotivación y dificultad para entregar tareas.",
        "Se observa mejora en participación durante las clases.",
        "Llega tarde con frecuencia por dificultades de transporte.",
        "Familia informa cambio de residencia reciente.",
        "Requiere apoyo en comprensión lectora.",
    ]
    textos_dx = [
        "Diagnóstico académico: brechas en matemáticas básicas.",
        "Diagnóstico de orientación: factores socioeconómicos que afectan la asistencia.",
    ]
    docs = []
    sample = rng.sample([e[0] for e in estudiantes if e[0] != DEMO_STUDENT], 30)
    for i, code in enumerate(sample):
        tipo = ["observacion", "observacion", "diagnostico", "intervencion"][i % 4]
        texto = (rng.choice(textos_dx) if tipo == "diagnostico" else
                 "Tutoría académica grupal realizada." if tipo == "intervencion" else rng.choice(textos_obs))
        fecha = school_days(BASE_PERIODS[i % 3][3], BASE_PERIODS[i % 3][4])[rng.randrange(10, 45)]
        docs.append({"id": f"HIST-{i + 1:03d}", "estudiante_codigo": code, "fecha": fecha.isoformat(),
                     "tipo": tipo, "autor_rol": "docente" if tipo == "observacion" else "orientador",
                     "texto": texto})
    docs.append({"id": "HIST-900", "estudiante_codigo": DEMO_STUDENT, "fecha": "2025-08-20",
                 "tipo": "observacion", "autor_rol": "docente",
                 "texto": "Docente de Matemáticas reporta desmotivación y ausencias aisladas."})
    docs.append({"id": "HIST-901", "estudiante_codigo": "E-9999", "fecha": "2025-08-21",
                 "tipo": "observacion", "autor_rol": "docente", "texto": "Registro huérfano (debe rechazarse)."})
    (raw_dir / "seguimiento_historico.json").write_text(
        json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")

    # ------------------------------------------------------------- paquete demo 2026-T1
    demo_dir.mkdir(parents=True, exist_ok=True)
    pc = DEMO_PERIOD[0]
    _write_csv(demo_dir / f"matriculas_{pc}.csv",
               ["estudiante_codigo", "centro_codigo", "periodo_codigo", "grado", "estado"],
               [[e[0], centros[e[3]][0], pc, min(12, e[4] + 1), "activa"] for e in estudiantes])
    a, c = period_records(DEMO_PERIOD, demo=True)
    _write_csv(demo_dir / f"asistencias_{pc}.csv", ["estudiante_codigo", "fecha", "estado"],
               [[x, d.isoformat(), s] for x, d, s in a] + [["E-0042", "2026-02-30", "presente"]])
    _write_csv(demo_dir / f"calificaciones_{pc}.csv", ["estudiante_codigo", "periodo_codigo", "asignatura", "nota"],
               c + [["E-0001", pc, "Matemáticas", -5]])
    _write_csv(demo_dir / f"inventario_tecnologico_{pc}.csv",
               ["centro", "periodo", "internet", "velocidad", "computadoras", "tabletas"],
               inventory_rows([DEMO_PERIOD], drift=0.03))

    return {"estudiantes": len(estudiantes), "centros": len(centros), "asistencias": len(asis_rows),
            "calificaciones": len(cal_rows), "documentos_json": len(docs)}


def ensure_generated() -> bool:
    """Genera los datos solo si faltan. Devuelve True si se generaron."""
    if (config.RAW_DIR / "regiones.geojson").exists() and (config.DEMO_DIR / "asistencias_2026-T1.csv").exists():
        return False
    generate()
    return True


if __name__ == "__main__":
    print(generate())

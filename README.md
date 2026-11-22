# EDU-ALERTA Panamá

Sistema de Información Gerencial para **alertas educativas tempranas**: integra asistencia, calificaciones,
recursos tecnológicos y contexto regional, genera alertas **explicables** y documenta el ciclo
*alerta → revisión humana → intervención → evaluación → decisión*.

> Prototipo académico (SIG) con **datos sintéticos**. Las alertas son señales basadas en reglas configurables;
> no son probabilidades de deserción ni política oficial de MEDUCA.

Equipo: Germán Carreño · Nathalia Rivera · Alison Vargas

---

## 1. Ejecución rápida (Docker)

Requisitos: Docker Desktop (o Docker Engine + Compose v2).

```bash
docker compose up -d --build        # construye la imagen y levanta mongo + app + scheduler
```

Abra **http://localhost:8501** · contraseña demostrativa: `edualerta`

| Usuario | Perfil | Puede |
|---|---|---|
| Nathalia Rivera | Dirección / Planificación | Ver todo, registrar decisiones y riesgos |
| Alison Vargas | Seguimiento académico | Revisar alertas, abrir casos, registrar intervenciones |
| Germán Carreño | Tecnología (CIO) | Cargar fuentes, ejecutar ETL, inventario, reglas, auditoría, pruebas |

En el primer arranque el contenedor `app` crea el esquema SQL, los índices MongoDB, genera los datos
sintéticos y ejecuta el pipeline una vez. Los arranques posteriores reutilizan los volúmenes.

### Servicios

| Servicio | Función |
|---|---|
| `mongo` | MongoDB 7 (observaciones, alertas, casos, intervenciones, decisiones, auditoría) |
| `app` | Interfaz Streamlit + bootstrap (SQLite en el volumen `sqlite_data`) |
| `scheduler` | Ejecución programada del pipeline; la frecuencia se edita en Administración › Reglas |
| `tests` | Pytest (perfil `test`) contra un MongoDB real |
| `mongo-express` | Visor web opcional de MongoDB (perfil `tools`, puerto 8081) |

### Comandos útiles

```bash
docker compose --profile test run --rm tests test       # 42 pruebas (unitarias, flujo, integración, dashboard)
docker compose exec app python -m edualerta.cli pipeline           # ejecutar ETL manualmente
docker compose exec app python -m edualerta.cli pipeline --force   # reprocesar (prueba de idempotencia)
docker compose exec app python -m edualerta.cli reset              # restablecer escenario de demostración
docker compose --profile tools up -d mongo-express                 # visor de MongoDB en :8081
docker compose logs -f scheduler
docker compose down          # detener (conserva datos)  ·  down -v  borra los volúmenes
```

### MongoDB Atlas (opcional)

Copie `.env.example` a `.env` y defina `MONGO_URI=mongodb+srv://...`. El resto no cambia.

---

## 2. Guion de demostración (caso E-0042)

1. **Alison** › *Seguimiento* › buscar `E-0042`: alerta **prioritaria** con 3 motivos
   (asistencia 72 %, promedio 58, 3 ausencias consecutivas).
2. Seleccionar la fila → **Confirmar** con justificación → **Abrir caso** asignando tutor.
3. Pestaña *Casos e intervenciones* → registrar **tutoría** + observación (MongoDB).
   *Inicio* refleja el caso «en seguimiento» y el KPI de intervenciones.
4. **Germán** › *Datos y ETL* › **Preparar paquete demo 2026-T1** → **Ejecutar pipeline**
   (rechaza a propósito una fecha inválida y una nota negativa; ver *Calidad y rechazos*).
5. **Alison** › caso de E-0042 › *Evolución*: 2026-T1 sube a 88 % / 68 (Δ +16 / +10) → nivel preventivo.
6. **Nathalia** › *Decisiones*: revisar recomendación y evidencias → **aprobar** con responsable,
   fecha de revisión y riesgos (probabilidad × impacto) → seguimiento de cumplimiento.
7. *Administración* › *Auditoría*: quién hizo qué y cuándo. *Automatización*: ejecutar las pruebas.

---

## 3. Arquitectura

```
data/raw (CSV · JSON · GeoJSON) ─┐
data/incoming (cargas subidas)  ─┴─► ETL Python (extraer → limpiar → validar → cargar → integrar)
                                         │                         │
                                   SQLite (relacional)      MongoDB (documental)
                                         └──────► indicadores · alertas · recomendaciones
                                                         │
                                            Streamlit + Plotly (8 pantallas)
                                                         │
                                        revisión → intervención → decisión → auditoría
```

```
app/                    Interfaz Streamlit (Inicio.py enruta según perfil; views/ = 8 pantallas)
src/edualerta/
  config.py             rutas, variables de entorno y YAML
  datagen.py            generador determinista de datos sintéticos (incluye errores de calidad intencionales)
  db/sql.py             esquema SQLite (PK, FK, UNIQUE, CHECK) y utilidades
  db/mongo.py           conexión, índices únicos (idempotencia), modo degradado
  etl/extract.py        lectura CSV/JSON/GeoJSON, normalización de encabezados, vista previa
  etl/transform.py      limpieza y reglas de negocio por entidad; rechazos con motivo
  etl/pipeline.py       orquestador, bitácora, huellas SHA-256, carga de paquetes
  services/             indicadores, alertas, seguimiento, tecnología, regional, KPI,
                        recomendaciones/decisiones, calidad, auditoría, perfiles, reportes PDF
  scheduler.py · cli.py ejecución programada y comandos
config/                 settings (umbrales, perfiles) · sources · kpis · riesgos
tests/                  pytest (mongomock + MongoDB real + AppTest de Streamlit)
```

### Modelo de datos

**SQLite**: `regiones`, `centros`, `periodos`, `estudiantes`, `matriculas`, `asistencias`, `calificaciones`,
`recursos_tecnologicos`, `indicadores`, `ejecuciones_etl`, `rechazos_etl`, `fuentes`, `archivos_procesados`,
`configuracion`.

**MongoDB**: `observaciones`, `alertas` (`_id = estudiante|periodo`), `casos`, `intervenciones`, `decisiones`
(`regla_clave` única), `auditoria`. Todas se vinculan a SQL por `estudiante_codigo` (E-NNNN).

### Reglas de alerta (configurables en Administración)

| Nivel | Criterios (cualquiera) |
|---|---|
| Prioritario | asistencia < 75 % · promedio < 60 · ≥ 3 ausencias consecutivas injustificadas |
| Preventivo | asistencia < 90 % · promedio < 70 · ≥ 2 ausencias consecutivas |
| Regular | ninguno de los anteriores |

Las ausencias justificadas se excluyen de los días programados y cortan las rachas.

---

## 4. Trazabilidad de funcionalidades

| Módulo | Funcionalidades | Dónde |
|---|---|---|
| 1. Centros, estudiantes y períodos | F01–F06 | Datos y ETL › Centros y estudiantes · `services/masters.py` |
| 2. Importación y fuentes | F07–F13 | Datos y ETL › Cargar fuentes / Fuentes · `etl/extract.py` |
| 3. Pipeline ETL y calidad | F14–F22 | `etl/transform.py`, `etl/pipeline.py`, `scheduler.py` · Bitácora |
| 4. Persistencia SQL y MongoDB | F23–F28 | `db/sql.py`, `db/mongo.py`, `followup.student_profile` |
| 5. Indicadores y alertas | F29–F36 | `services/indicators.py`, `services/alerts.py` · Seguimiento › Alertas |
| 6. Seguimiento e intervenciones | F37–F44 | `services/followup.py` · Seguimiento › Casos / Perfil |
| 7. Recursos tecnológicos | F45–F50 | `services/tech.py` · Tecnología escolar |
| 8. Comparación regional | F51–F56 | `services/regional.py` · Regiones (mapa) |
| 9. Dashboard gerencial | F57–F64 | Inicio · Análisis · `services/kpi.py`, `services/reports.py` |
| Técnica analítica (checklist) | Segmentación k-means | Análisis › Perfiles de centros · `services/segmentation.py` |
| Alineación del SIG (sección 10) | Matriz, AS-IS / TO-BE | Administración › Alineación del SIG |
| 10. Decisiones | F65–F71 | `services/recommendations.py` · Decisiones |
| 11. Gobierno, riesgos y auditoría | F72–F78 | `services/auth.py`, `services/audit.py`, `services/quality.py` · Administración |
| 12. Automatización y pruebas | F79–F86 | `cli.py`, `scheduler.py`, `tests/`, este README |

---

### Diseño y funcionamiento sin internet

La interfaz usa un sistema visual propio (barra lateral «pizarra», semáforo reservado a niveles de riesgo,
tipografías Figtree y Bricolage Grotesque). Las fuentes están dentro del proyecto (`app/static/fonts`, licencia
SIL OFL) y Streamlit las sirve desde el contenedor: la aplicación no necesita internet. La única excepción es el
fondo cartográfico del mapa regional (teselas de CARTO/OpenStreetMap); sin conexión, las regiones se dibujan
igual pero sin el mapa base.

## 5. Desarrollo local sin Docker (opcional)

Python 3.12, MongoDB accesible en `MONGO_URI`.

```bash
pip install -r requirements.txt -r requirements-dev.txt
export PYTHONPATH=src SQLITE_PATH=data/db/edualerta.db MONGO_URI=mongodb://localhost:27017
python -m edualerta.cli bootstrap
streamlit run app/Inicio.py
pytest
```

# Guía final v3: lo que falta en el código y en el documento de EDU-ALERTA

Versión ajustada al documento **`EDU_ALERTA_SIG_Final_con_niveles.docx`** (37 páginas, entrega **30 de noviembre de 2026**).
Reemplaza las guías anteriores.

## 0. Qué cambió respecto a la guía anterior

**1. El documento ya tiene la división por nivel** que pidió la profesora. MEDUCA sí la publica: un cuadro por nivel,
todos del año lectivo 2024 y de la Oficina de Estadística (fuente de los datos: SIDE).

| Nivel | Cuadro | Matrícula | Aprobados | Aplazados | Reprobados | Desertores |
| --- | --- | --- | --- | --- | --- | --- |
| Primaria | 2-12 | 482.961 | 96,4 % | no publica | 3,1 % | 0,6 % |
| Premedia | 3-12 | 218.293 | 79,22 % | 13,24 % | 5,67 % | 1,87 % |
| Media | 4-12 | 149.934 | 78,02 % | 14,61 % | 4,97 % | 2,39 % |

Premedia + media = educación secundaria (7.º a 12.º). En las tres, las **comarcas** tienen la mayor deserción (1,7 %, 4,67 % y 8,89 %).

**2. Qué quedó en el documento** (todo con las cifras por nivel y región, y con el detalle completo en el nuevo **Anexo D**):

- Resumen y Delimitación: aclaran que el escenario sintético cubre **premedia y media (7.º a 12.º), 16 centros de cada una, sin primaria**.
- Evidencia del problema: una fila nueva con las cifras oficiales por nivel.
- Planteamiento › nueva sección **«Estadísticas oficiales por nivel educativo (año lectivo 2024)»**: tabla nacional por nivel, tabla de
  deserción y reprobación por región y nivel (con las tres comarcas desglosadas), tres lecturas y el control aritmético.
- Inventario de fuentes, AS-IS, Cobertura funcional, Alcance del contraste: ahora hablan de niveles (los cuadros pertinentes para el
  escenario son el 3-12 y el 4-12; el 2-12 describe un nivel que el prototipo no modela).
- Resultados › nueva tabla **premedia vs. media** con los indicadores de 2025-T3 (medida en el escenario, ver D-6).
- Recomendaciones: nueva recomendación 4 (priorizar premedia, media y comarcas). Riesgos adicionales: «niveles no comparables».
- Limitaciones («primaria no modelada») y Trabajo futuro (extender a primaria y agregar selector de nivel).
- Referencias (+ cuadros 3-12 y 4-12), Anexo A (+ filas de GitHub y presentación), Anexo C (+ enlaces) y **Anexo D** (tres tablas completas).

**3. Cómo se armó este archivo (importante).** Solo tenía el PDF final, no su Word. Reconstruí el documento completo a partir del
texto del PDF y le apliqué los cambios de arriba, con el mismo formato (Times New Roman 12, portada, índice, pie con número).
Comparé el texto automáticamente: salvo las partes que cambié a propósito, coincide con el PDF. Las **tablas** y las **figuras** no se
comparan igual de bien: revisen a ojo que no falte nada. Tienen dos caminos:

- Usar este `.docx` como base (más simple), o
- Copiar a su Word las secciones de la lista anterior, si ya tienen ediciones propias.

**4. Lo que sigue en amarillo** (todo lo demás está cerrado): las 12 capturas (cada marcador dice exactamente qué foto va ahí),
los enlaces de GitHub y de la presentación (Anexo A y C), la **revisión manual de las cifras oficiales** (D-7), la confirmación del
desglose de la segmentación y las cifras por nivel en Docker.

**5. Honestidad de las cifras.** Las cifras oficiales las transcribí desde los PDF de MEDUCA y las validé con tres controles
(la matrícula de las 14 regiones suma el total de cada nivel, las tres tasas de cada fila suman 100 % dentro del redondeo y las tasas
ponderadas reproducen la tasa nacional). Eso detecta la mayoría de los errores, pero **no sustituye** mirar el PDF: ver D-7.
Excluí las filas por área (indígena, rural, urbana) porque en media no suman el total (149.734 contra 149.934).

El título y el año del Cuadro 2-12 siguen coincidiendo con la referencia del documento. El PDF anterior ya no integraba datos reales al sistema, así
que **no hace falta** el extractor, `indicadores_regionales` ni pestaña de estadísticas oficiales. **No lo hagan antes del 30.**

Aclaración que ya está en el documento: los cuadros publican **14 regiones educativas** (las tres comarcas agrupadas, con desglose
aparte) y el escenario usa **16**; no se comparan una a una.

## 1. Qué falta, en orden

| # | Qué | Dónde | Tiempo | Bloquea |
| --- | --- | --- | --- | --- |
| 1 | Crear el repositorio de GitHub y pegar el enlace | Código y Anexos A y C | 20 min | Consigna (enlace obligatorio) |
| 2 | Agregar el aviso de «datos sintéticos» en todas las pantallas | `app/common.py` | 10 min | Capturas honestas |
| 3 | Levantar con Docker y confirmar cifras (incluida la tabla por nivel) | Terminal | 30 min | Capturas 9 y 10, y decidir 48 o 49 pruebas |
| 4 | Tomar las **12 capturas** (marcadores amarillos) | Interfaz y terminal | 1 a 1,5 h | Documento |
| 5 | Revisar a mano 5 celdas por cuadro oficial contra el PDF de MEDUCA | Anexo D | 20 min | Credibilidad de las cifras |
| 6 | README, LICENSE y `DATA_SOURCES.md` | Repositorio | 20 min | Presentación del repo |
| 7 | Presentación y enlace | Anexo C | Aparte | Consigna |
| 8 | (Decisión) devolver «qué salió mal / lecciones» | Documento | 20 min | Rúbrica de la profesora |

Plan sugerido: viernes noche, puntos 1 a 3; sábado, 4 y 5; domingo, 6, 7 y revisión final; lunes, entrega.

Todas las rutas de código son relativas a `Edu-Alerta_Panama/`.

---

## A. Repositorio de GitHub (el zip no tiene `.git`)

```bash
cd Edu-Alerta_Panama
git init -b main
git add .
git status            # no debe aparecer data/db/*, .env ni archivos .db
git commit -m "EDU-ALERTA Panamá: versión inicial del SIG"
```

Cree un repositorio vacío en GitHub (sin README ni .gitignore) y conéctelo:

```bash
git remote add origin https://github.com/<usuario>/edu-alerta-panama.git
git push -u origin main
```

Antes del primer `push`:

- El `.gitignore` ya excluye `.env`, `data/db/*` y `data/incoming/*`. Confirme que no hay credenciales.
- Agregue `LICENSE` (por ejemplo MIT).
- No suba copias de la base (`.db`) ni capturas con datos fuera del escenario.
- Pegue el enlace en el **Anexo C** del documento (fila «Repositorio de GitHub del equipo») y en la presentación.
  Cuando lo tenga, cambie en el **Anexo A** el estado a «Cubierto» (ver D-8).

---

---

## B. Aviso de datos sintéticos en todas las pantallas

Hoy el aviso solo aparece en la pantalla de ingreso. Como el documento insiste en que los resultados regionales son
del generador, las capturas deben mostrarlo. Las ocho pantallas llaman a `common.header(...)`, así que basta **un cambio**.

En `app/common.py`, al final de la función `header(...)` (después del `st.markdown(...)` que dibuja el título), agregue:

```python
    st.caption(
        "Datos sintéticos de demostración: estudiantes, centros, regiones e indicadores del escenario no describen "
        "la realidad de Panamá. Las estadísticas de MEDUCA se usan solo como referencia en el documento y no "
        "se procesan en este sistema."
    )
```

Después ejecute las pruebas (`pytest`, o el comando de Docker de la sección C). No cambia ninguna cifra.

Criterio de aceptación: ninguna pantalla con gráfico regional se ve sin esa línea.

---

---

## C. Docker: confirmar cifras y decidir qué reportar (48 o 49 pruebas)

El PDF reporta **48 pruebas aprobadas y 1 omitida** y dice que no se probó con MongoDB real. Esas cifras salieron de
una simulación de MongoDB. En Docker, la prueba omitida **sí corre** y el resultado esperado es **49 aprobadas, 0 omitidas**.
Eso afecta a la **captura de la ilustración 9** (mostraría 49) y al texto del documento (dice 48). Elijan una opción:

| Opción | Qué hacen | Qué cambia en el documento |
| --- | --- | --- |
| **1 (recomendada)** | Correr todo en Docker, tomar las capturas ahí | Actualizar el texto en 6 lugares (lista abajo) |
| 2 | Mantener 48 + 1 omitida y tomar la captura de pruebas sin Docker (`pytest` local) | Nada, pero queda el hueco de MongoDB real declarado |

**Lugares del PDF que cambian si hacen la opción 1** (solo si los números confirman):

1. Resumen: «48 pruebas… una omitida» y la frase final sobre MongoDB real.
2. Resultados › Pruebas automatizadas: «48 aprobadas y 1 omitida… simulación de MongoDB». Ese párrafo también dice que se hizo una
   prueba de humo de la interfaz (22 combinaciones de pantalla y perfil). La hice yo en el entorno de trabajo con MongoDB simulado;
   si no la repiten, borren esa oración.
3. Resultados › Evidencias y alcance: fila «Integración con una instancia MongoDB real» (pasaría a «Verificado»).
4. Conclusiones › Limitaciones: viñeta «Validación de infraestructura».
5. Anexo B: la frase que dice que las 48 pruebas usaron simulación.
6. Pie de la ilustración 9.

Si **no** pueden correr Docker, no pasa nada: el documento ya declara esa limitación con honestidad. En ese caso
tomen la captura 8 con `pytest` local y déjenlo como está.

### Comandos

```bash
docker compose down -v                       # parte de cero para que coincidan las cifras
docker compose up -d --build                 # mongo + app + scheduler; el arranque corre el pipeline inicial
docker compose --profile test run --rm tests test      # esperado: 49 passed
docker compose exec app python -m edualerta.cli pipeline           # 2.ª corrida: debe omitir 9 archivos
docker compose exec app python -m edualerta.cli pipeline --force   # reprocesa; no debe duplicar
```

Las pruebas usan su propia base (`edualerta_test` y un SQLite temporal), así que no estropean la base de la app.

### Volcar los números que cita el documento

```bash
docker compose exec app python - <<'PY'
from edualerta.db import sql
with sql.session() as c:
    for t in ["regiones", "centros", "periodos", "estudiantes", "matriculas", "asistencias",
              "calificaciones", "recursos_tecnologicos", "indicadores"]:
        print(t, c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    print("alertas 2025-T3:", [tuple(r) for r in c.execute(
        "SELECT nivel_alerta, COUNT(*) FROM indicadores WHERE periodo_codigo='2025-T3' GROUP BY 1")])
    print("corridas:", [tuple(r) for r in c.execute(
        "SELECT id, disparador, estado, leidos, aceptados, rechazados, omitidos FROM ejecuciones_etl ORDER BY id")])
PY

docker compose exec mongo mongosh edualerta --quiet --eval \
 'printjson({alertas: db.alertas.countDocuments(), observaciones: db.observaciones.countDocuments(), decisiones: db.decisiones.countDocuments(), auditoria: db.auditoria.countDocuments()})'
```

Valores que reporta el PDF y que deben coincidir:

| Medición | Valor en el PDF |
| --- | --- |
| Pruebas | 48 aprobadas, 1 omitida (en Docker: 49 y 0) |
| Corrida 1 | 84.298 leídos, 84.287 aceptados, 11 rechazados, 0 omitidos |
| Corrida 2 (mismos archivos) | 0 leídos, 9 omitidos |
| Conteos | 16 regiones, 32 centros, 4 períodos, 489 estudiantes, 1.467 matrículas, 73.350 asistencias, 8.802 calificaciones, 96 recursos |
| Alertas 2025-T3 | 36 prioritarias, 140 preventivas, 313 regulares |
| MongoDB tras la 1.ª corrida | 450 alertas, 31 observaciones, 24 decisiones, 2 de auditoría |
| k-means | k = 2, silueta 0,390 (tres: 0,343; cuatro: 0,367; cinco: 0,360) |
| Por nivel, 2025-T3 | Ver la tabla de la sección D-6 (premedia: 243 estudiantes; media: 246) |

Cuidados al comparar:

- En Docker, la corrida inicial la hace el arranque de `app` (disparador `bootstrap`). El `scheduler` puede agregar corridas
  propias a `ejecuciones_etl`; compare los **leídos, aceptados, rechazados y omitidos** de cada corrida, no el número de fila.
- La **auditoría crece cada vez que alguien inicia sesión o actúa**. El «2» solo se ve antes de entrar a la interfaz, así
  que lance el comando de MongoDB **antes** de iniciar sesión (o acepte que verá más).
- Si algo difiere, corrija el documento con el valor medido, no al revés.

---

---

## D. Capturas, cifras por nivel y revisión del documento

### D-1. Orden para que las cifras de las capturas coincidan con el texto

El documento usa como base el **período 2025-T3** y un escenario **sin casos abiertos** (Intervenciones realizadas = «No aplica»,
Alertas sin seguimiento = 176). Por eso:

1. Tomen primero **todas las capturas de línea base** (todas menos la de E-0042), con el período 2025-T3 y **sin** abrir casos ni confirmar alertas.
2. Después hagan el recorrido de demostración (paquete 2026-T1) solo para la captura de E-0042.
3. Si se equivocan y abren un caso antes de tiempo: `docker compose exec app python -m edualerta.cli reset` y empiecen de nuevo.

Usuarios (contraseña `edualerta`): **german** (Tecnología), **nathalia** (Dirección), **alison** (Seguimiento).

### D-2. Las 12 capturas (y cómo ponerlas)

Cada marcador amarillo del documento ya trae dentro la instrucción de la captura. Para reemplazarlo: seleccione el marcador,
bórrelo, inserte la imagen centrada (ancho aproximado de 6 pulgadas) y **deje debajo la leyenda «Ilustración N»**, que ya está numerada de
1 a 13. La Ilustración 1 (arquitectura) ya es una figura real, no una captura.

| Ilustración | Sección | Dónde y cómo | Qué debe verse |
| --- | --- | --- | --- |
| 2 | Modelo de datos › MongoDB | `docker compose --profile tools up -d mongo-express` y abra `http://localhost:8081` › base `edualerta` | Las seis colecciones y, abierta, una alerta con sus motivos |
| 3 | Modelo de datos › SQLite | `docker compose cp app:/app/data/db/edualerta.db ./snapshot.db` y ábrala con DB Browser for SQLite (no la suba al repositorio) | Lista de tablas y la estructura de una (por ejemplo `indicadores`) |
| 4 | k-means | **nathalia** › Análisis › **Perfiles de centros**, período 2025-T3 | Los 2 grupos, silueta 0,39 y los 9 + 23 centros |
| 5 | Dashboard | **nathalia** › Inicio, período 2025-T3 | Los 7 KPI (94,0 %; 96,7 %; 36; 62,5 %; 0,26; No aplica; 176) |
| 6 | Seguimiento | **alison** › Seguimiento › **Alertas**, buscar `E-0042` | La alerta prioritaria con sus 3 motivos |
| 7 | Regiones | **nathalia** › Regiones, período 2025-T3 | Mapa y tabla, con el aviso de datos sintéticos y regiones de muestra insuficiente |
| 8 | Recursos tecnológicos | **german** › Tecnología › **Mapa de necesidades** (o **Centros prioritarios**) | Brecha de dispositivos y conectividad por centro |
| 9 | Pruebas | Terminal: `docker compose --profile test run --rm tests test` | Total de pruebas (49 en Docker; 48 + 1 omitida sin MongoDB) |
| 10 | Pipeline ETL | **german** › Datos y ETL › **Bitácora**; o `docker compose exec app python -m edualerta.cli pipeline` | Corrida 1 (84.298 / 84.287 / 11) y corrida 2 (9 omitidos); la pestaña **Calidad y rechazos** muestra los 11 motivos |
| 11 | Caso E-0042 | **alison** › Seguimiento › **Perfil del estudiante** (`E-0042` ya viene escrito), **después** de cargar el paquete 2026-T1 (german › Datos y ETL › «Agregar paquete de demostración 2026-T1» › «Ejecutar pipeline») | Los cuatro períodos 2025-T1 a 2026-T1 |
| 12 | Decisiones | **nathalia** › Decisiones › **Por decidir** | Recomendaciones con su evidencia (si registran una decisión, háganlo después de las capturas de línea base) |
| 13 | Riesgos | **german** o **nathalia** › Administración › **Gobierno de datos** («Matriz de riesgos y controles»); opcional: **Auditoría** | Los riesgos R1 a R6 con su P × I |

Consejos: ventana ancha, recorte sin el escritorio, y que se lea el aviso de datos sintéticos.

### D-3. Correcciones de forma: ya aplicadas en el documento

Del listado anterior ya quedaron resueltas: fecha única (30 de noviembre), figuras numeradas 1 a 13, Anexo B sin la frase
truncada y con `--build`, «auditoría» con tilde, referencia a «Evidencias y alcance de la verificación» en «Cómo se evalúa», filas de GitHub y
presentación en el Anexo A, aclaración de 14 vs. 16 regiones, cifras con punto de miles, porcentajes sin espacio y columnas más anchas.
Si trabajan sobre su propio Word en vez de este archivo, repasen esos puntos. También se actualizó la portada con el título final del PDF.

### D-4. Segmentación: confirmar el desglose por grupo

El documento ya usa los valores **medidos** (ya no «ilustrativos») y los marca en amarillo para confirmarlos en Docker:

| Grupo | Centros | Estudiantes | Prioritarios | Con internet | Dispositivos | Dispositivos por estudiante |
| --- | --- | --- | --- | --- | --- | --- |
| Rezago académico y brecha tecnológica | 9 | 142 | 24 (16,9 %) | 3 de 9 | 4 | 0,028 |
| Perfil promedio | 23 | 347 | 12 (3,5 %) | 17 de 23 | 124 | 0,357 |
| Total | 32 | 489 | 36 | 20 | 128 | 0,26 |

La tabla del documento muestra **promedios de las tasas por centro** (17,0 % y 3,4 %); las tasas ponderadas son 16,9 % y 3,5 %.
Ambas son correctas y el texto ya lo explica. Para reproducirlo en Docker, tras la primera corrida, cree `grupos.py` y ejecútelo con
`docker compose exec -T app python - < grupos.py`:

```python
import pandas as pd
from edualerta.db import sql
from edualerta.services import segmentation, tech

PER = "2025-T3"
with sql.session() as c:
    rules = sql.get_rules(c)
    seg = segmentation.segment(segmentation.center_features(c, PER, rules))
    res = tech.resources_frame(c, PER, rules)[["centro_codigo", "dispositivos", "matriculados"]]
    cen = seg["centros"].merge(res, on="centro_codigo")
    ind = pd.read_sql(
        "SELECT i.nivel_alerta, m.centro_codigo FROM indicadores i JOIN matriculas m "
        "ON m.estudiante_codigo=i.estudiante_codigo AND m.periodo_codigo=i.periodo_codigo "
        "WHERE i.periodo_codigo=?", c, params=[PER]).merge(cen[["centro_codigo", "grupo"]], on="centro_codigo")
    for g, s in cen.groupby("grupo"):
        pri = int((ind[ind.grupo == g].nivel_alerta == "prioritario").sum())
        print(f"grupo {g}: centros={len(s)} estudiantes={int(s.estudiantes.sum())} prioritarios={pri} "
              f"internet={int(s.tiene_internet.sum())}/{len(s)} dispositivos={int(s.dispositivos.sum())}")
```

Si el resultado en Docker difiere, use el de Docker y quite el amarillo.

### D-5. Hueco frente a lo que pidió la profesora (decisión del equipo)

La profesora quiere la estructura de los casos de ejemplo: situación de partida, **qué salió mal**, qué se rediseñó, resultados y
**lecciones**. El documento conserva el AS-IS/TO-BE de la organización, pero **no tiene** las subsecciones «Qué salió mal en la
primera versión del proyecto», «Qué se solucionó y qué no» ni «Lecciones». Si la rúbrica premia explicar el proceso del propio
equipo, devuelvan, en media página:

- **Qué salió mal:** la primera versión no nombraba organización ni decisión, presentaba resultados como pendientes y describía la
  orquestación como más de lo que era (hay un ejecutor periódico, no un orquestador). Además, las estadísticas de referencia eran solo de primaria
  mientras que el escenario modela premedia y media.
- **Qué se ajustó:** se fijó la organización de referencia y la decisión modelada, se midieron resultados sobre el escenario, se acotó el alcance
  a datos sintéticos y se separaron las estadísticas oficiales por nivel.
- **Lecciones:** empezar por la decisión y no por la tecnología; declarar cada vez qué es sintético; medir antes de afirmar; comprobar que la referencia
  oficial corresponde al mismo nivel que el escenario.

Es una decisión del equipo: no cambia el código, solo el documento.

### D-6. Cifras por nivel del escenario: confirmar en Docker

La tabla nueva de Resultados (premedia vs. media, 2025-T3) la medí en el entorno de trabajo con MongoDB simulado. Los totales reproducen los
del documento (94,0 %, 96,7 %, 36 / 140 / 313, 20 de 32 con internet, 128 dispositivos). Confírmenla en Docker con `nivel.py`
(`docker compose exec -T app python - < nivel.py`), tras la primera corrida y **antes** de abrir casos:

```python
import pandas as pd
from edualerta.db import sql
from edualerta.services import indicators, tech

PER = "2025-T3"
with sql.session() as c:
    rules = sql.get_rules(c)
    ind = indicators.indicator_frame(c, PER)
    res = tech.resources_frame(c, PER, rules)
    cen = pd.read_sql("SELECT codigo, nivel FROM centros", c)
    res = res.merge(cen, left_on="centro_codigo", right_on="codigo")
    for nivel, g in list(ind.groupby("nivel_educativo")) + [("TOTAL", ind)]:
        r = res if nivel == "TOTAL" else res[res.nivel == nivel]
        ev = g["aprobado"].dropna()
        print(nivel, "centros", g.centro_codigo.nunique(), "estudiantes", len(g),
              "asistencia %d/%d" % (g.dias_asistidos.sum(), g.dias_programados.sum()),
              "aprobacion %d/%d" % (ev.sum(), len(ev)),
              g.nivel_alerta.value_counts().to_dict(),
              "internet %d/%d" % (r.tiene_internet.sum(), len(r)),
              "dispositivos %d matriculados %d" % (r.dispositivos.sum(), r.matriculados.sum()))
```

Valores que debe imprimir (y que están en el documento):

| Indicador (2025-T3) | Premedia (7.º a 9.º) | Media (10.º a 12.º) | Total |
| --- | --- | --- | --- |
| Centros / estudiantes | 16 / 243 | 16 / 246 | 32 / 489 |
| Asistencia (días asistidos / programados) | 11.217 / 11.920 (94,1 %) | 11.305 / 12.037 (93,9 %) | 22.522 / 23.957 (94,0 %) |
| Aprobación | 237 / 243 (97,5 %) | 236 / 246 (95,9 %) | 473 / 489 (96,7 %) |
| Prioritarios / preventivos / regulares | 15 / 69 / 159 | 21 / 71 / 154 | 36 / 140 / 313 |
| Con internet | 9 de 16 | 11 de 16 | 20 de 32 |
| Dispositivos / matriculados | 70 / 243 (0,29) | 58 / 246 (0,24) | 128 / 489 (0,26) |

Si algo difiere, corrija el documento con el valor de Docker. Las diferencias entre niveles vienen del generador, no de la realidad; el documento ya lo dice.

**Opcional (solo si sobra tiempo):** el tablero filtra por grado (7.º a 12.º), no por nivel. Un selector «Nivel» (premedia / media) en los filtros
permitiría una captura por nivel, pero cambia código y capturas; el documento lo declara como trabajo futuro, así que **no es necesario**.

### D-7. Revisión manual de las cifras oficiales de MEDUCA (obligatoria, 20 minutos)

Abran cada PDF y comparen estas celdas con el **Anexo D** del documento (columna «Total»; en los PDF, usen la columna de ambos sexos):

| Cuadro | Total nacional | Comarcas | Bocas del Toro | Panamá Centro |
| --- | --- | --- | --- | --- |
| 2-12 Primaria | 482.961 · 96,4 · 3,1 · 0,6 | 69.757 · 89,1 · 9,3 · 1,7 | 31.403 · 93,9 · 5,5 · 0,5 | 77.144 · 98,2 · 1,3 · 0,5 |
| 3-12 Premedia | 218.293 · 79,22 · 13,24 · 5,67 · 1,87 | 24.711 · 76,96 · 12,28 · 6,1 · 4,67 | 12.391 · 66,62 · 21,38 · 9,12 · 2,88 | 39.334 · 82,05 · 11,28 · 5,5 · 1,17 |
| 4-12 Media | 149.934 · 78,02 · 14,61 · 4,97 · 2,39 | 11.843 · 70,96 · 14,3 · 5,85 · 8,89 | 7.697 · 64,54 · 20,53 · 9,78 · 5,14 | 29.307 · 84,3 · 11,2 · 3,45 · 1,04 |

Orden de las cifras: matrícula · aprobados · (aplazados) · reprobados · desertores, todas en %, salvo la matrícula.
Revisen además una fila de comarca desglosada (por ejemplo Ngäbe-Buglé: media 10.780 · 70,58 · 14,48 · 5,71 · 9,23). Si una celda no
coincide, corrijan el Anexo D **y** la tabla de la sección «Estadísticas oficiales por nivel» (comparten los números), y quiten el amarillo.

Enlaces (también están en el Anexo C):

- https://www.meduca.gob.pa/wp-content/uploads/2025/07/04062025_cuadro_2-12_primaria_2024.pdf
- https://www.meduca.gob.pa/wp-content/uploads/2025/07/09062025_Cuadro_3-12_Premedia_2024.pdf
- https://www.meduca.gob.pa/wp-content/uploads/2025/08/04062025_Cuadro_4-12_Media_2024.pdf

---

## E. README y documentación del repositorio

1. Al inicio de `README.md`, agregue **«Caso de estudio»**: organización de referencia (MEDUCA), decisión modelada (priorizar
   centros y casos para apoyo), y una línea clara: **todos los datos que procesa el sistema son sintéticos y cubren premedia y media
   (7.º a 12.º); las estadísticas públicas de MEDUCA (cuadros 2-12, 3-12 y 4-12) son solo referencia del documento y no se cargan al
   pipeline**. Enlace al documento.
2. Corrija el conteo de pruebas: el README dice 49; sin MongoDB real corren 48 y una se omite.
3. Reemplace cualquier frase que sugiera orquestación completa por: «El ejecutor periódico lanza el pipeline cada 60 minutos
   (configurable). No modela dependencias entre tareas ni reintentos automáticos».
4. Agregue `DATA_SOURCES.md` con las referencias externas, **todas como contexto**, sin carga al sistema: los tres cuadros de MEDUCA
   (URL, fecha de consulta, año lectivo 2024, nivel), el informe CECC-UNESCO (URL) y las notas de La Estrella (1 y 2 de marzo y
   14 de julio de 2026). Indique que ninguna se procesa.
5. En `EDU-ALERTA_Panama_Funcionalidades.md`, una nota al inicio: el prototipo fue autorizado para 3 integrantes y los roles
   corresponden a los de la organización simulada.

---

## F. Qué NO hacer antes del 30 (el documento ya lo declara como trabajo futuro)

| Idea | Por qué esperar |
| --- | --- |
| Cargar los cuadros de MEDUCA al pipeline | Contradice el alcance del documento (se usan como referencia, no se cargan) |
| Agregar primaria al generador de datos | Cambia 489 estudiantes, 32 centros y todas las cifras y capturas; está como trabajo futuro 2 |
| Selector de nivel en el tablero | Cambia código y capturas; ya se declara como trabajo futuro 2 |
| Reintentos en `scheduler.py` | Hay que cambiar 5 lugares del texto (orquestación, limitaciones, Anexo A, trabajo futuro, cobertura funcional) |
| Límites oficiales para el mapa | Requiere verificar licencia; es trabajo futuro 3 |
| Validar con OULAD | Trabajo futuro 5; es un experimento aparte |
| IA generativa | El proyecto cubre «otras técnicas» con k-means y el Anexo A lo declara |

---

## G. Lista final antes de entregar (30 de noviembre de 2026)

- [ ] Repositorio de GitHub creado, con README, LICENSE y sin `.env` ni bases de datos; enlace en los Anexos A y C (y estado «Cubierto» en el Anexo A).
- [ ] Aviso de datos sintéticos visible en las 8 pantallas.
- [ ] Docker: `up`, pruebas, pipeline y segunda corrida ejecutados; cifras confirmadas (y texto actualizado si dio 49).
- [ ] Tabla por nivel (D-6) y desglose de segmentación (D-4) confirmados en Docker.
- [ ] Las 12 capturas insertadas, con las leyendas «Ilustración 1» a «Ilustración 13» intactas.
- [ ] Cifras oficiales del Anexo D revisadas contra los tres PDF (D-7).
- [ ] Decisión tomada sobre «qué salió mal / lecciones» (D-5).
- [ ] Una sola fecha de entrega en todo el documento (30 de noviembre).
- [ ] Enlace de la presentación en el Anexo C y presentación con la misma estructura: organización, problema, qué falló, qué se rediseñó, resultados, límites (y una diapositiva con las cifras por nivel).
- [ ] Búsqueda final de «PENDIENTE», «INSERTAR» y «completar» en el documento: debe dar cero resultados, y sin texto amarillo.
- [ ] Revisar los números de página del índice después de insertar las capturas: en este archivo el índice es texto fijo, no un campo que se actualice solo. Si las páginas se desfasan, corríjanlos a mano o pídanme regenerarlo con las capturas ya puestas.

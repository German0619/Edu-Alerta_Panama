# Fuentes de datos externas

**Ninguna de estas fuentes se procesa en el sistema.** Todas se citan solo como **contexto** en el documento del
proyecto. Los datos que carga el pipeline (estudiantes, centros, regiones, asistencia, calificaciones y recursos) los
crea el generador determinista `src/edualerta/datagen.py`. Son **sintéticos** y cubren premedia y media (7.º a 12.º).

## Estadísticas oficiales de MEDUCA (año lectivo 2024)

Publicadas por la Oficina de Estadística de MEDUCA (fuente de los datos: SIDE). Cada cuadro trae matrícula, aprobados,
aplazados (solo premedia y media), reprobados y desertores por región educativa (14 regiones, con las comarcas
agrupadas y desglosadas aparte). El escenario sintético usa 16 regiones, así que las cifras no se comparan región por región.

| Cuadro | Nivel | Año lectivo | URL | Fecha de consulta |
| --- | --- | --- | --- | --- |
| 2-12 | Primaria (el prototipo no lo modela) | 2024 | https://www.meduca.gob.pa/wp-content/uploads/2025/07/04062025_cuadro_2-12_primaria_2024.pdf | _(fecha de consulta)_ |
| 3-12 | Premedia (7.º a 9.º) | 2024 | https://www.meduca.gob.pa/wp-content/uploads/2025/07/09062025_Cuadro_3-12_Premedia_2024.pdf | _(fecha de consulta)_ |
| 4-12 | Media (10.º a 12.º) | 2024 | https://www.meduca.gob.pa/wp-content/uploads/2025/08/04062025_Cuadro_4-12_Media_2024.pdf | _(fecha de consulta)_ |

Resumen nacional (detalle completo en el Anexo D del documento):

| Nivel | Matrícula | Aprobados | Aplazados | Reprobados | Desertores |
| --- | --- | --- | --- | --- | --- |
| Primaria | 482.961 | 96,4 % | no publica | 3,1 % | 0,6 % |
| Premedia | 218.293 | 79,22 % | 13,24 % | 5,67 % | 1,87 % |
| Media | 149.934 | 78,02 % | 14,61 % | 4,97 % | 2,39 % |

## Otras referencias

| Fuente | Uso | URL |
| --- | --- | --- |
| Informe CECC-UNESCO (Ed-DQAF, datos de 2017 y 2018) | Antecedente de calidad e integración de datos del SIDE | https://www.meduca.gob.pa/wp-content/uploads/2025/04/Entrega_Informe_CECC-UNESCO-Panama.pdf |
| La Estrella de Panamá, 1 de marzo de 2026: «Aulas a medias…» | Evidencia del problema: estudiantes fuera del sistema y comarcas | https://www.laestrella.com.pa/panama/nacional/aulas-a-medias-desercion-escolar-se-mantiene-mientras-sigue-conflicto-docente-BG20370526 |
| La Estrella de Panamá, 2 de marzo de 2026: «Fracaso escolar persiste…» | Evidencia del problema: reprobación por nivel | https://www.laestrella.com.pa/panama/nacional/fracaso-escolar-persiste-mas-27-mil-alumnos-reprobados-FG20408278 |
| La Estrella de Panamá, 14 de julio de 2026 (columna de opinión) | Posible limitación de cobertura de las cifras oficiales | https://www.laestrella.com.pa/opinion/columnistas/el-costo-de-la-desercion-escolar-en-panama-PB24078241 |

## Lo que no se hace

- Los cuadros de MEDUCA **no se cargan al pipeline** y no existe la tabla `indicadores_regionales` ni una pestaña de
  estadísticas oficiales. Eso queda como trabajo futuro.
- Primaria no está en el escenario sintético. Extender el modelo a primaria y agregar un selector de nivel es
  trabajo futuro.

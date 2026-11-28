# Capturas para el documento final

Capturas reales del sistema para reemplazar los marcadores amarillos «INSERTAR CAPTURA REAL» del documento
`EDU_ALERTA_SIG_Final_con_niveles`. Todas muestran **datos sintéticos** del escenario de demostración.

## Cómo se tomaron

- Con Playwright, en una copia limpia del sistema: un proyecto de Docker aparte (`docker compose -p edu-capturas`,
  puerto 8502) con volúmenes propios. Así la base del equipo no se tocó.
- Línea base: período **2025-T3**, sin casos abiertos ni alertas confirmadas, con los umbrales por defecto
  (asistencia prioritaria < 75 %).
- Se siguió el orden de la guía v3 (D-1). Primero se tomaron todas las capturas de línea base. Después se cargó el
  paquete demo 2026-T1, solo para la Ilustración 11.
- Ventana de 1440 px de ancho. El aviso de datos sintéticos se ve en todas las pantallas del sistema.

## Qué archivo va en cada ilustración

| Ilustración | Archivo | Sección del documento | Qué muestra |
| --- | --- | --- | --- |
| 1 | — | Diseño del sistema | Ya es una figura en el documento (arquitectura); no es una captura |
| 2 | `ilustracion_02a_mongodb_colecciones.png` y `ilustracion_02b_mongodb_alerta_E-0042.png` | Modelo de datos › MongoDB | mongo-express: las 6 colecciones y la alerta `E-0042\|2025-T3` con sus 3 motivos |
| 3 | **falta** | Modelo de datos › SQLite | DB Browser for SQLite con la lista de tablas y la estructura de `indicadores` (es una app de escritorio; se toma a mano) |
| 4 | `ilustracion_04_kmeans_perfiles.png` | Segmentación k-means | nathalia › Análisis › Perfiles de centros: 2 grupos, silueta 0,39, 9 + 23 centros |
| 5 | `ilustracion_05_dashboard_inicio.png` | Dashboard principal | nathalia › Inicio: 94,0 %; 96,7 %; 36; 62,5 %; 0,26; No aplica; 176 |
| 6 | `ilustracion_06_seguimiento_E-0042.png` | Seguimiento y alertas | alison › Seguimiento › Alertas, E-0042: alerta prioritaria con 3 motivos |
| 7 | `ilustracion_07_regiones.png` (opcional: `ilustracion_07b_regiones_tabla.png`) | Comparación regional | nathalia › Regiones: mapa, aviso y advertencia de muestra insuficiente (Colón, 27 estudiantes) |
| 8 | `ilustracion_08_tecnologia.png` | Recursos tecnológicos | german › Tecnología › Mapa de necesidades |
| 9 | `ilustracion_09_pruebas.png` | Pruebas automatizadas | german › Administración › Automatización y pruebas › «Ejecutar pruebas»: **49 passed** |
| 10 | `ilustracion_10_etl_bitacora.png` (opcional: `ilustracion_10b_calidad_rechazos.png`) | Pipeline ETL | german › Datos y ETL › Bitácora: corrida 1 = 84.298 / 84.287 / 11; las siguientes omiten 9 archivos |
| 11 | `ilustracion_11_perfil_E-0042.png` | Evolución histórica | alison › Seguimiento › Perfil del estudiante, después del paquete 2026-T1: los cuatro períodos |
| 12 | `ilustracion_12_decisiones.png` | Recomendaciones y decisiones | nathalia › Decisiones › Por decidir: 24 recomendaciones con su evidencia |
| 13 | `ilustracion_13_riesgos.png` | Matriz de riesgos | german › Administración › Gobierno de datos: R1 a R6 con P × I |

## Notas para el documento

- **Ilustración 9:** se tomó desde la interfaz, no desde la terminal. La salida es la de pytest real (49 passed).
  Ajusten el texto del marcador o tomen la de terminal con `docker compose --profile test run --rm tests test`.
- **Ilustración 10:** la bitácora muestra también una corrida del ejecutor programado (n.º 3, 0 leídos y 9
  omitidos), porque pasó una hora durante la sesión. No cambia ninguna cifra.
- Para insertarlas: borrar el marcador amarillo, insertar la imagen centrada (unas 6 pulgadas de ancho) y dejar
  debajo la leyenda «Ilustración N».

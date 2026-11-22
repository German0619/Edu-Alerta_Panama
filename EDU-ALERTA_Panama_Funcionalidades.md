# EDU-ALERTA Panamá

## Catálogo completo de funcionalidades del sistema

**Proyecto final -- Sistemas de Información Gerencial (SIG)**\
**Sector:** Educación\
**Equipo:** Germán Carreño, Nathalia Rivera y Alison Vargas\
**Nota:** La profesora autorizó expresamente que el equipo esté
conformado por tres integrantes.

------------------------------------------------------------------------

## 1. Enfoque del proyecto

EDU-ALERTA Panamá es un Sistema de Información Gerencial que integra
tres problemáticas educativas:

1.  Riesgo de abandono escolar y bajo rendimiento académico.
2.  Desigualdad en la disponibilidad de recursos tecnológicos
    educativos.
3.  Diferencias regionales en los indicadores y oportunidades
    educativas.

La deserción y el riesgo académico constituyen el eje central. Las
condiciones tecnológicas y regionales funcionan como dimensiones de
contexto que ayudan a interpretar las necesidades y orientar la
planificación.

**Principio central:** alinear el proceso administrativo, la tecnología
que lo respalda y la decisión gerencial que se espera mejorar.

> Problema gerencial → diagnóstico del proceso → rediseño administrativo
> → integración tecnológica → indicadores → decisión → intervención →
> evaluación.

El sistema no pretende sustituir el criterio de docentes o directivos ni
afirmar que puede predecir con certeza la deserción. Su función es
organizar evidencia, identificar señales de riesgo mediante criterios
explicables y apoyar la priorización de intervenciones humanas.

## 2. Resumen de módulos

Se proponen 12 módulos funcionales. Las funcionalidades no representan
necesariamente 86 pantallas; muchas son operaciones internas del
pipeline, consultas, validaciones o acciones dentro de una misma vista.

  Módulo                                             Funcionalidades Prioridad
  ------------------------------------------------ ----------------- -----------
  1\. Gestión de centros, estudiantes y períodos                   6 Esencial
  2\. Importación y fuentes de datos                               7 Esencial
  3\. Pipeline ETL y calidad de datos                              9 Esencial
  4\. Persistencia SQL y MongoDB                                   6 Esencial
  5\. Indicadores académicos y alertas                             8 Esencial
  6\. Seguimiento e intervenciones                                 8 Esencial
  7\. Recursos tecnológicos escolares                              6 Esencial
  8\. Comparación regional                                         6 Esencial
  9\. Dashboard gerencial                                          8 Esencial
  10\. Decisiones y recomendaciones gerenciales                    7 Esencial
  11\. Gobierno de datos, riesgos y auditoría                      7 Esencial
  12\. Automatización, pruebas y demostración                      8 Esencial
  **Total**                                                   **86** 

## 3. Catálogo detallado de funcionalidades

### Módulo 1. Gestión de centros, estudiantes y períodos

**Proceso:** mantener información institucional organizada para el
seguimiento educativo.

-   **F01.** Registrar y consultar centros educativos con código,
    nombre, región, zona urbana/rural y dependencia.
-   **F02.** Registrar estudiantes ficticios con identificadores
    anónimos y centro educativo asociado.
-   **F03.** Administrar períodos académicos: año, trimestre o período
    de evaluación.
-   **F04.** Asociar cada estudiante con su centro, grado y matrícula
    correspondiente.
-   **F05.** Filtrar registros por centro, región, grado y período.
-   **F06.** Validar duplicados y relaciones entre estudiantes, centros
    y matrículas.

**Tecnología:** SQLite, Python y formularios Streamlit.\
**Decisión apoyada:** determinar qué población estudiantil se está
monitoreando, por centro y período.\
**Evidencia:** consulta de estudiantes y centros con sus respectivas
relaciones.

### Módulo 2. Importación y fuentes de datos

**Proceso:** incorporar información procedente de diferentes fuentes
para evitar análisis aislados.

-   **F07.** Importar archivos CSV de estudiantes, asistencia y
    calificaciones.
-   **F08.** Importar archivos CSV de centros, inventario tecnológico y
    matrícula.
-   **F09.** Importar documentos JSON de observaciones, diagnósticos e
    intervenciones.
-   **F10.** Incorporar datos geográficos GeoJSON para representar
    regiones educativas.
-   **F11.** Mostrar una vista previa de cada archivo antes de
    procesarlo.
-   **F12.** Verificar que cada fuente contenga las columnas o atributos
    requeridos.
-   **F13.** Registrar metadatos: nombre de fuente, formato, origen,
    fecha de carga, cantidad de registros y naturaleza real o sintética.

**Tecnología:** Python, Pandas, JSON y GeoPandas o Plotly.\
**Decisión apoyada:** identificar qué fuentes están disponibles y si
pueden utilizarse de manera confiable.\
**Evidencia:** cargar un CSV, un JSON y un GeoJSON correctamente,
mostrando su contenido y metadatos.

### Módulo 3. Pipeline ETL y calidad de datos

**Proceso:** transformar registros dispersos en información
estandarizada, validada y útil para la gerencia.

-   **F14.** Ejecutar la extracción automática de las fuentes
    configuradas.
-   **F15.** Detectar valores nulos, duplicados y registros
    inconsistentes.
-   **F16.** Normalizar nombres de columnas, formatos de fecha y códigos
    institucionales.
-   **F17.** Validar reglas de negocio: calificaciones dentro del rango,
    fechas válidas y asistencia vinculada con estudiantes registrados.
-   **F18.** Integrar datos académicos, asistencia, centros y recursos
    mediante sus identificadores.
-   **F19.** Calcular indicadores derivados durante la transformación.
-   **F20.** Almacenar los datos procesados en la base SQL y preparar
    los registros correspondientes a MongoDB.
-   **F21.** Registrar resultados de cada ejecución: inicio,
    finalización, registros aceptados, rechazados y errores.
-   **F22.** Ejecutar el pipeline en el orden correcto mediante un
    orquestador Python, con opción de ejecución manual y programada.

**Tecnología:** Python, Pandas, SQLite y un orquestador sencillo
mediante funciones o tareas programadas.\
**Decisión apoyada:** determinar si la información está suficientemente
actualizada y validada para sustentar una decisión gerencial.\
**Evidencia:** ejecutar el pipeline y mostrar registros de entrada,
limpieza, transformación, almacenamiento y bitácora de ejecución.

El ETL debe realizar transformaciones reales. Un botón que simplemente
cargue un CSV al dashboard no demuestra adecuadamente el requisito de
ingeniería de datos.

### Módulo 4. Persistencia SQL y MongoDB

**Proceso:** almacenar, organizar y recuperar la información de acuerdo
con su estructura.

-   **F23.** Crear tablas SQL relacionadas para estudiantes, centros,
    matrículas, períodos, asistencia, calificaciones y recursos
    tecnológicos.
-   **F24.** Implementar claves primarias, foráneas y restricciones de
    integridad.
-   **F25.** Crear colecciones MongoDB para observaciones, alertas,
    intervenciones y decisiones.
-   **F26.** Implementar operaciones de creación, lectura y
    actualización de documentos MongoDB.
-   **F27.** Relacionar registros SQL y documentos MongoDB mediante
    identificadores comunes.
-   **F28.** Ejecutar consultas integradas para mostrar datos académicos
    junto con el historial de seguimiento.

**Tecnología:** SQLite, MongoDB Atlas, PyMongo y Python.\
**Decisión apoyada:** consultar tanto indicadores cuantitativos como el
historial cualitativo que explica las intervenciones.\
**Evidencia:** registrar una observación desde la aplicación,
verificarla en MongoDB y recuperarla en el perfil de seguimiento.

### Módulo 5. Indicadores académicos y alertas tempranas

**Proceso:** identificar oportunamente estudiantes que requieren
evaluación y seguimiento.

-   **F29.** Calcular el porcentaje de asistencia de cada estudiante.
-   **F30.** Detectar ausencias consecutivas y recurrentes.
-   **F31.** Calcular promedios académicos por estudiante, asignatura y
    período.
-   **F32.** Identificar rendimiento inferior a los umbrales
    configurados.
-   **F33.** Clasificar los casos en prioritario, preventivo o regular
    mediante reglas explicables.
-   **F34.** Mostrar los motivos específicos que activaron cada alerta.
-   **F35.** Comparar la evolución de los indicadores entre períodos.
-   **F36.** Permitir que un responsable revise, confirme o descarte una
    alerta, registrando el motivo.

**Tecnología:** Python, Pandas, consultas SQL y MongoDB.\
**Decisión apoyada:** determinar qué estudiantes requieren atención
primero y por qué.\
**Evidencia:** un estudiante ficticio con ausencias consecutivas y bajo
rendimiento debe generar una alerta explicable y quedar disponible para
seguimiento.

El prototipo identificará indicadores de riesgo; no afirmará calcular
probabilidades reales de deserción sin datos longitudinales y validación
estadística.

### Módulo 6. Seguimiento e intervenciones

**Proceso:** convertir las alertas en acciones institucionales
verificables.

-   **F37.** Abrir un caso de seguimiento a partir de una alerta
    confirmada.
-   **F38.** Asignar un responsable del caso: tutor, orientador o
    coordinador.
-   **F39.** Registrar el tipo de intervención: tutoría, entrevista,
    contacto familiar, apoyo académico u otra.
-   **F40.** Almacenar observaciones cualitativas en MongoDB.
-   **F41.** Registrar la fecha de intervención, estado y próxima
    revisión.
-   **F42.** Actualizar el estado del caso: pendiente, en seguimiento,
    atendido o cerrado.
-   **F43.** Consultar el historial cronológico de intervenciones.
-   **F44.** Evaluar la evolución posterior del estudiante comparando
    sus indicadores antes y después de la intervención.

**Tecnología:** Streamlit, Python, SQL y MongoDB.\
**Decisión apoyada:** determinar qué intervención se realizará, quién la
ejecutará y si es necesario ajustarla.\
**Evidencia:** crear una intervención y demostrar que el dashboard
refleja el nuevo estado del caso.

Este módulo es especialmente importante para el enfoque
proceso--tecnología--decisión, porque demuestra que las alertas tienen
una consecuencia administrativa real dentro del prototipo.

### Módulo 7. Recursos tecnológicos escolares

**Proceso:** identificar carencias de infraestructura tecnológica para
orientar apoyos institucionales.

-   **F45.** Registrar disponibilidad de internet por centro educativo.
-   **F46.** Registrar cantidad de computadoras y dispositivos
    utilizables.
-   **F47.** Calcular indicadores de disponibilidad de dispositivos por
    estudiante.
-   **F48.** Clasificar necesidades tecnológicas mediante criterios
    configurables.
-   **F49.** Comparar disponibilidad de recursos entre centros.
-   **F50.** Generar una lista de centros candidatos a recibir atención
    tecnológica prioritaria.

**Tecnología:** SQL, Python y visualizaciones Plotly.\
**Decisión apoyada:** identificar qué centros necesitan ser evaluados
para recibir recursos y qué carencias justifican esa prioridad.\
**Evidencia:** comparar dos centros ficticios con diferentes niveles de
conectividad y mostrar sus necesidades.

### Módulo 8. Comparación regional

**Proceso:** analizar desigualdades territoriales que puedan afectar la
planificación educativa.

-   **F51.** Visualizar regiones de Panamá en un mapa interactivo.
-   **F52.** Mostrar indicadores agregados de asistencia por región.
-   **F53.** Comparar promedios académicos y tasas de aprobación.
-   **F54.** Comparar conectividad y disponibilidad de dispositivos.
-   **F55.** Filtrar comparaciones por año, región, centro y nivel
    educativo, según los datos disponibles.
-   **F56.** Identificar regiones con indicadores desfavorables mediante
    criterios transparentes.

**Tecnología:** GeoJSON, Python y Plotly.\
**Decisión apoyada:** determinar dónde se concentran las necesidades y
cuáles regiones conviene estudiar o atender prioritariamente.\
**Evidencia:** seleccionar una región en el mapa y observar sus
indicadores agregados.

Los análisis regionales deberán respetar los tamaños de muestra y la
cobertura real de los datos. Si se utiliza una muestra sintética de
escuelas, las conclusiones serán demostrativas y no representarán
oficialmente a todas las escuelas de Panamá.

### Módulo 9. Dashboard gerencial interactivo

**Proceso:** transformar información técnica en indicadores
comprensibles para los responsables administrativos.

-   **F57.** Presentar un resumen ejecutivo con los KPI principales.
-   **F58.** Incorporar gráficos de evolución histórica por período.
-   **F59.** Mostrar la distribución de alertas por nivel y centro
    educativo.
-   **F60.** Incorporar filtros interactivos que actualicen gráficos y
    tablas.
-   **F61.** Visualizar el estado de las intervenciones.
-   **F62.** Mostrar comparaciones académicas, tecnológicas y
    regionales.
-   **F63.** Permitir consultar los detalles y criterios de cálculo de
    cada KPI.
-   **F64.** Exportar tablas y reportes ejecutivos en CSV o PDF.

**Tecnología:** Streamlit, Plotly y Python.\
**Decisión apoyada:** identificar las situaciones que requieren atención
gerencial sin revisar manualmente múltiples archivos.\
**Evidencia:** modificar un filtro y demostrar cómo cambian los
indicadores y las comparaciones.

### Módulo 10. Decisiones y recomendaciones gerenciales

**Proceso:** traducir los resultados del análisis en decisiones
administrativas documentadas.

-   **F65.** Generar recomendaciones basadas en reglas explícitas a
    partir de los KPI.
-   **F66.** Presentar las evidencias que justifican cada recomendación.
-   **F67.** Priorizar recomendaciones según criterios de urgencia y
    alcance.
-   **F68.** Permitir registrar una decisión gerencial: aprobar,
    posponer, rechazar o solicitar revisión.
-   **F69.** Asociar a cada decisión un responsable, justificación y
    fecha de revisión.
-   **F70.** Evaluar los riesgos de una decisión mediante probabilidad,
    impacto y controles de mitigación.
-   **F71.** Consultar el historial de decisiones y su estado de
    cumplimiento.

**Tecnología:** Python, MongoDB y Streamlit.\
**Decisión apoyada:** seleccionar acciones, justificar su prioridad y
evaluar riesgos antes de ejecutarlas.\
**Evidencia:** generar una recomendación, registrar su aprobación,
asignar responsable y consultar su historial.

El sistema debe diferenciar entre una recomendación automática y una
decisión humana. Por ejemplo, puede recomendar revisar la asignación de
equipos a un centro, pero la aprobación corresponde al responsable
administrativo.

### Módulo 11. Gobierno de datos, riesgos y auditoría

**Proceso:** garantizar que la información sea comprensible, trazable y
utilizada responsablemente.

-   **F72.** Definir perfiles de uso: dirección, seguimiento académico y
    tecnología.
-   **F73.** Restringir la visualización y modificación de información
    según cada perfil.
-   **F74.** Mantener datos estudiantiles sintéticos o anonimizados en
    el prototipo.
-   **F75.** Registrar acciones importantes: cargas, cambios de alertas,
    intervenciones y decisiones.
-   **F76.** Documentar el origen, definición y responsable de cada
    conjunto de datos.
-   **F77.** Mostrar indicadores de calidad de datos: completitud,
    consistencia y registros rechazados.
-   **F78.** Documentar los riesgos de privacidad, calidad,
    interpretación y continuidad operativa, junto con sus controles.

**Tecnología:** Python, SQL y MongoDB.\
**Decisión apoyada:** establecer qué datos pueden utilizarse, quién es
responsable y cuándo una información no debe emplearse para decidir.\
**Evidencia:** un registro de auditoría que muestre quién realizó una
acción, qué ocurrió y cuándo.

Para la sustentación basta con un esquema de roles demostrativo
correctamente implementado; no es necesario desarrollar una
infraestructura empresarial de identidad.

### Módulo 12. Automatización, pruebas y demostración

**Proceso:** asegurar que la solución pueda ejecutarse, actualizarse y
verificarse de forma reproducible.

-   **F79.** Ejecutar el proceso completo de actualización de datos
    mediante una acción central.
-   **F80.** Configurar una frecuencia de actualización programada o
    simularla de manera reproducible.
-   **F81.** Evitar duplicaciones al ejecutar nuevamente el pipeline con
    datos que ya fueron procesados.
-   **F82.** Gestionar errores de conexión, archivos incorrectos y
    registros inválidos sin interrumpir toda la aplicación.
-   **F83.** Ejecutar pruebas de validación del pipeline y de los
    cálculos de KPI.
-   **F84.** Ejecutar pruebas de integración entre SQL, MongoDB y el
    dashboard.
-   **F85.** Preparar datos de demostración y un mecanismo para
    restablecer el escenario inicial.
-   **F86.** Publicar el proyecto en GitHub con código, instrucciones de
    instalación, configuración y ejecución.

**Tecnología:** Python, Pytest, GitHub y archivos de configuración.\
**Decisión apoyada:** confiar en que la información utilizada en las
decisiones es reproducible y que la operación del prototipo puede
mantenerse.\
**Evidencia:** ejecutar el sistema desde una instalación documentada y
demostrar pruebas satisfactorias.

------------------------------------------------------------------------

## 4. Las ocho pantallas principales

Las 86 funcionalidades se pueden distribuir en ocho pantallas
principales. La aplicación puede utilizar un menú lateral de Streamlit y
pestañas internas para evitar una navegación excesivamente compleja.

  Pantalla                 Contenido
  ------------------------ ----------------------------------------------
  1\. Inicio               Resumen ejecutivo y KPI
  2\. Datos y ETL          Carga, limpieza y ejecución del pipeline
  3\. Seguimiento          Estudiantes, alertas, casos e intervenciones
  4\. Tecnología escolar   Recursos y necesidades
  5\. Regiones             Mapa y comparaciones regionales
  6\. Análisis             Tendencias, filtros y resultados
  7\. Decisiones           Recomendaciones, responsables y riesgos
  8\. Administración       Fuentes, reglas, auditoría y pruebas

El dashboard no debe ser únicamente de lectura. Las pantallas de carga,
alertas, seguimiento y decisiones necesitan acciones funcionales que
persistan sus resultados.

## 5. Arquitectura tecnológica recomendada

``` text
FUENTES DE DATOS
    |
    |-- CSV: asistencia, calificaciones, matrícula y centros
    |-- JSON: observaciones e intervenciones
    |-- GeoJSON: regiones y datos geográficos
    |
    v
PIPELINE ETL - PYTHON
    |
    |-- Extracción
    |-- Limpieza
    |-- Validación
    |-- Transformación
    |-- Integración
    |
    +----------------------+----------------------+
    |                                             |
    v                                             v
SQLITE                                        MONGODB ATLAS
    |                                             |
    |-- Estudiantes                               |-- Observaciones
    |-- Centros                                   |-- Alertas
    |-- Matrículas                                |-- Intervenciones
    |-- Asistencias                               |-- Decisiones
    |-- Calificaciones                            |-- Auditoría
    |-- Recursos tecnológicos                     |
    |                                             |
    +----------------------+----------------------+
                           |
                           v
              MOTOR DE INDICADORES Y ALERTAS
                           |
                           v
                  STREAMLIT + PLOTLY
                           |
                           v
             REVISIÓN Y DECISIÓN GERENCIAL
                           |
                           v
                INTERVENCIÓN Y SEGUIMIENTO
```

### Tecnologías

-   **Python:** procesamiento, reglas de negocio, indicadores e
    integración.
-   **Pandas:** manipulación y transformación de datos.
-   **SQLite:** almacenamiento relacional para el prototipo.
-   **MongoDB Atlas:** almacenamiento documental de observaciones,
    alertas, intervenciones y decisiones.
-   **PyMongo:** conexión entre Python y MongoDB.
-   **Streamlit:** interfaz web.
-   **Plotly:** gráficos y mapas interactivos.
-   **GeoJSON / GeoPandas:** información geográfica.
-   **Pytest:** pruebas.
-   **GitHub:** control de versiones y entrega del código.

Se recomienda Google Colab para desarrollar y probar análisis cuando
resulte conveniente, pero la aplicación final debe tener una forma
reproducible de ejecutarse. MongoDB satisface la alternativa tecnológica
de integración con MongoDB indicada para el proyecto; no es necesario
añadir AWS si no aporta valor al alcance.

## 6. Modelo de datos mínimo

### Base relacional --- SQLite

  Tabla                     Información principal
  ------------------------- -------------------------------------------
  `regiones`                Código y nombre de región
  `centros`                 Centro, región, zona y dependencia
  `estudiantes`             Código anónimo y datos académicos básicos
  `matriculas`              Estudiante, centro, grado y período
  `periodos`                Año y período académico
  `asistencias`             Fecha, estudiante y estado
  `calificaciones`          Estudiante, asignatura, nota y período
  `recursos_tecnologicos`   Internet y dispositivos por centro
  `indicadores`             Valores calculados por período
  `ejecuciones_etl`         Resultados del pipeline

### Base documental --- MongoDB Atlas

  Colección          Información principal
  ------------------ ---------------------------------------
  `observaciones`    Notas de seguimiento
  `alertas`          Clasificación, motivos y revisión
  `intervenciones`   Responsable, acción y evolución
  `decisiones`       Recomendaciones, aprobación y riesgos
  `auditoria`        Acciones relevantes del sistema

Todas las colecciones relacionadas con estudiantes deben usar el
identificador anónimo definido en SQL. Se recomienda emplear índices
únicos o claves de idempotencia para evitar documentos duplicados cuando
el pipeline se ejecute nuevamente.

## 7. Indicadores clave de desempeño (KPI)

  -----------------------------------------------------------------------
  KPI                                 Cálculo o criterio
  ----------------------------------- -----------------------------------
  Tasa de asistencia                  Días asistidos / días programados ×
                                      100

  Tasa de aprobación                  Estudiantes aprobados / estudiantes
                                      evaluados × 100

  Alertas prioritarias                Número de estudiantes clasificados
                                      para revisión prioritaria

  Conectividad escolar                Centros con internet / centros
                                      evaluados × 100

  Disponibilidad de dispositivos      Dispositivos funcionales /
                                      estudiantes matriculados

  Intervenciones realizadas           Casos con acción registrada / casos
                                      asignados × 100

  Alertas sin seguimiento             Alertas abiertas sin intervención
                                      registrada
  -----------------------------------------------------------------------

Cada KPI debe tener nombre, descripción, fórmula, fuente, periodicidad,
filtros aplicables y responsable de interpretación. Los indicadores no
deben calcularse a partir de valores escritos manualmente en el
dashboard.

## 8. Reglas de clasificación de alertas

Se propone una clasificación inicial transparente y configurable:

-   **Prioritario:** se cumple al menos un criterio crítico, por
    ejemplo, asistencia inferior al 75 %, promedio inferior a 60/100 o
    tres o más ausencias consecutivas.
-   **Preventivo:** no cumple un criterio crítico, pero presenta señales
    de atención, por ejemplo, asistencia inferior al 90 %, promedio
    inferior a 70/100 o dos ausencias consecutivas.
-   **Regular:** no cumple los criterios anteriores.

Estos umbrales son ilustrativos y deberán ajustarse y justificarse como
reglas del prototipo. No representan una política oficial de MEDUCA ni
un modelo predictivo validado.

Cada alerta debe mostrar los motivos que la activaron. El personal
responsable debe poder revisar, confirmar o descartar la alerta,
documentando la justificación. Deben considerarse las ausencias
justificadas, la calidad de los datos y el contexto del estudiante antes
de actuar.

## 9. Simulador de ejemplo para la demostración

**Caso: estudiante ficticio E-0042**

  Indicador                   Valor
  ------------------------ --------
  Asistencia                   72 %
  Promedio académico         58/100
  Ausencias consecutivas          3

Flujo demostrativo:

1.  Se carga un CSV con registros de asistencia y calificaciones.
2.  Python valida el contenido, calcula los KPI y almacena los
    registros.
3.  El motor identifica que el estudiante cumple criterios configurados
    de alerta prioritaria.
4.  La coordinadora verifica el caso, confirma la alerta y asigna un
    responsable.
5.  Se registra una tutoría académica en MongoDB con fecha de
    seguimiento.
6.  El dashboard muestra el estado del caso y posteriormente compara la
    evolución de los KPI.
7.  La dirección consulta los resultados y decide si mantiene, modifica
    o amplía el tipo de apoyo.

El objetivo no es mostrar muchas gráficas, sino demostrar que el proceso
completo funciona y que los datos pasan correctamente entre tecnologías.

## 10. Alineación de procesos, tecnologías y decisiones

Esta matriz debe ocupar un lugar central en el informe y en la
sustentación.

  -----------------------------------------------------------------------
  Etapa del proceso Funcionalidad     Tecnología        Decisión o
  TO-BE                                                 resultado
  ----------------- ----------------- ----------------- -----------------
  1\. Recopilar     F07--F13          Python, CSV,      Determinar
  datos                               JSON, GeoJSON     fuentes
                                                        disponibles

  2\. Validar y     F14--F22          Pipeline ETL      Aceptar o
  transformar                                           corregir
                                                        información

  3\. Consolidar    F23--F28          SQL y MongoDB     Disponer de
  registros                                             información
                                                        integrada

  4\. Monitorear    F29--F35          Python y SQL      Detectar señales
  indicadores                                           de riesgo

  5\. Revisar       F36--F38          Streamlit y       Confirmar casos y
  alertas                             MongoDB           asignar
                                                        responsables

  6\. Ejecutar      F39--F44          MongoDB           Registrar y
  seguimiento                                           evaluar
                                                        intervenciones

  7\. Analizar      F45--F56          SQL, Python y     Identificar
  contexto escolar                    GeoJSON           carencias y
                                                        brechas

  8\. Analizar      F57--F64          Dashboard         Interpretar
  resultados                                            tendencias y KPI

  9\. Decidir y     F65--F71          Reglas y registro Aprobar acciones
  priorizar                           gerencial         y evaluar riesgos

  10\. Controlar y  F72--F86          Auditoría y       Verificar calidad
  mejorar                             automatización    y continuidad
  -----------------------------------------------------------------------

El proceso no termina cuando el sistema genera una alerta. Termina
cuando la institución registra una acción, la evalúa y utiliza el
resultado para mejorar la siguiente decisión.

### Proceso actual (AS-IS)

Debe presentarse como escenario hipotético de referencia, salvo que el
equipo realice entrevistas o una investigación que confirme el proceso
en una institución concreta.

1.  Los docentes registran asistencia y calificaciones.
2.  Los datos pueden quedar dispersos en archivos o sistemas.
3.  El personal revisa manualmente los casos.
4.  Las intervenciones pueden ocurrir tardíamente.
5.  Resulta difícil evaluar el seguimiento realizado.

### Proceso mejorado (TO-BE)

1.  Los datos se integran mediante fuentes configuradas.
2.  El sistema valida y calcula indicadores.
3.  Se generan alertas con criterios verificables.
4.  El responsable revisa y asigna intervenciones.
5.  Se registra y evalúa la evolución del caso.
6.  La dirección consulta los resultados y documenta decisiones.

## 11. Riesgos y controles

  -----------------------------------------------------------------------
  Riesgo                  Posible consecuencia    Control propuesto
  ----------------------- ----------------------- -----------------------
  Datos académicos        Alertas incorrectas     Validaciones y reportes
  incompletos                                     de calidad

  Clasificación errónea   Estigmatización o       Revisión humana y
                          atención innecesaria    umbrales configurables

  Diferencias en          Comparaciones engañosas Indicadores
  registros regionales                            normalizados y análisis
                                                  de cobertura

  Exposición de           Vulneración de          Datos sintéticos,
  información estudiantil privacidad              controles de acceso y
                                                  anonimización

  Fallas del pipeline     Indicadores             Bitácora, pruebas y
                          desactualizados         manejo de errores

  Limitaciones de         Dificultad para operar  Exportación de reportes
  conectividad            el sistema              y actualización
                                                  diferida
  -----------------------------------------------------------------------

Cada riesgo debe relacionarse con su probabilidad, impacto, responsable,
medida preventiva y respuesta. La matriz de riesgos debe vincularse con
las decisiones gerenciales que el sistema registra.

## 12. Distribución del trabajo entre los tres integrantes

La profesora autorizó que el equipo esté conformado por tres personas.
Se propone la siguiente distribución:

  -----------------------------------------------------------------------
  Integrante              Responsabilidad de      Responsabilidad
                          desarrollo              gerencial
  ----------------------- ----------------------- -----------------------
  **Germán Carreño**      Arquitectura, pipeline  Director de Tecnología
                          ETL, SQLite,            (CIO); lidera la
                          integración técnica y   alineación del proceso
                          pruebas                 con la solución

  **Nathalia Rivera**     Dashboard, KPI,         Directora de
                          recursos tecnológicos,  Planificación
                          mapa regional y         Educativa; interpreta
                          reportes                indicadores y propone
                                                  prioridades

  **Alison Vargas**       Alertas, MongoDB,       Coordinadora de
                          intervenciones,         Seguimiento Académico;
                          recomendaciones y       valida alertas y
                          auditoría               gestiona intervenciones
  -----------------------------------------------------------------------

Los roles gerenciales son funciones simuladas para el proyecto. Las
responsabilidades de programación y documentación corresponden a las
tareas reales del equipo. Todos deben poder explicar el proceso completo
y la relación entre las tecnologías.

## 13. Orden de implementación recomendado

### Fase 1 --- Cimientos del SIG

-   Crear estructura del proyecto.
-   Preparar datos sintéticos.
-   Crear tablas SQL.
-   Configurar conexión MongoDB.
-   Implementar importación de fuentes.

**Referencia:** F01--F13 y F23--F27.

### Fase 2 --- Ingeniería y automatización

-   Construir y probar el pipeline ETL.
-   Implementar controles de calidad.
-   Calcular indicadores.
-   Crear bitácora de ejecución.

**Referencia:** F14--F22.

### Fase 3 --- Proceso gerencial principal

-   Implementar alertas.
-   Revisar y confirmar casos.
-   Asignar responsables.
-   Registrar intervenciones.
-   Implementar decisiones y riesgos.

**Referencia:** F28--F44 y F65--F71.

### Fase 4 --- Visualización y contexto

-   Desarrollar KPI y dashboard.
-   Implementar recursos tecnológicos.
-   Construir comparaciones regionales.
-   Incorporar filtros y reportes.

**Referencia:** F45--F64.

### Fase 5 --- Validación y entrega

-   Implementar controles de acceso proporcionados al alcance.
-   Completar auditoría.
-   Ejecutar pruebas.
-   Automatizar la ejecución final.
-   Documentar y publicar el repositorio.

**Referencia:** F72--F86.

## 14. Checklist de cumplimiento y aceptación

### Ingeniería de datos

-   [ ] Fuentes en al menos tres formatos: CSV, JSON y GeoJSON.
-   [ ] Extracción, limpieza, transformación y almacenamiento mediante
    ETL.
-   [ ] Orquestación de procesos y bitácora.
-   [ ] Integración tecnológica con MongoDB.
-   [ ] IA generativa u otras técnicas analíticas justificadas.
-   [ ] Automatización del cálculo y actualización de indicadores.

### Sistema gerencial

-   [ ] Base de datos estructurada y funcional.
-   [ ] KPI con fórmulas verificables.
-   [ ] Tendencias y comparaciones.
-   [ ] Dashboard interactivo.
-   [ ] Recomendaciones basadas en evidencia.
-   [ ] Evaluación de riesgos vinculada a decisiones.

### Entregables y demostración

-   [ ] Repositorio GitHub con código e instrucciones.
-   [ ] Documento del proyecto y referencias.
-   [ ] Presentación grupal.
-   [ ] Demostración funcional del flujo completo.
-   [ ] Participación y roles definidos para los tres integrantes.

### Criterios para declarar terminado el sistema

1.  El sistema se ejecuta desde el repositorio y carga correctamente los
    datos de prueba.
2.  El pipeline procesa los tres formatos, valida registros y actualiza
    las bases de datos.
3.  SQL y MongoDB almacenan y recuperan información real.
4.  Los KPI se calculan desde los datos.
5.  Las alertas identifican los motivos que justifican una revisión.
6.  Un responsable puede registrar una intervención y consultar su
    historial.
7.  Los módulos tecnológicos y regionales presentan comparaciones
    útiles.
8.  La dirección puede registrar una decisión, justificarla y evaluar
    sus riesgos.
9.  El sistema conserva evidencia de la ejecución de los procesos.
10. Los tres integrantes pueden explicar qué proceso mejora cada
    tecnología y qué decisión permite tomar.

------------------------------------------------------------------------

## 15. Recomendación final

Utilicen este catálogo como contrato funcional del desarrollo, pero
prioricen la calidad e integración del proceso completo por encima de la
cantidad de pantallas.

El programa estará verdaderamente alineado con los objetivos de Sistemas
de Información Gerencial cuando puedan demostrar, de principio a fin,
cómo una necesidad educativa se convierte en información, esa
información se analiza, la gerencia decide y la institución registra el
seguimiento de su decisión.

**Ese es el núcleo que debemos proteger durante todo el desarrollo de
EDU-ALERTA Panamá.**

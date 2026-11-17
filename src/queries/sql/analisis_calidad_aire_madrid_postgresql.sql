-- =============================================================================
-- PRACTICA A3 - CALIDAD DEL DATO Y EDA
-- ANALISIS DE CALIDAD DEL AIRE DE MADRID CON POSTGRESQL
-- =============================================================================
--
-- Base de datos:
--     curso_ia
--
-- Esquema:
--     aire_madrid
--
-- Tabla de entrada:
--     aire_madrid.mediciones_diarias
--
-- Este script:
--     1. Verifica la carga.
--     2. Crea indices para las consultas analiticas.
--     3. Crea vistas de calidad y EDA.
--     4. Ejecuta consultas de comprobacion.
--
-- No modifica los datos de mediciones_diarias.
-- =============================================================================


-- =============================================================================
-- 01. CONTEXTO
-- =============================================================================

SELECT
    current_database() AS base_datos,
    current_user AS usuario,
    current_schema() AS esquema_actual;


-- =============================================================================
-- 02. CONTROL GENERAL DE LA TABLA
-- =============================================================================

SELECT
    COUNT(*) AS registros,
    COUNT(DISTINCT estacion) AS estaciones,
    COUNT(DISTINCT magnitud) AS magnitudes,
    COUNT(DISTINCT punto_muestreo) AS puntos_muestreo,
    MIN(fecha) AS fecha_minima,
    MAX(fecha) AS fecha_maxima,
    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos_iqr
FROM aire_madrid.mediciones_diarias;


-- =============================================================================
-- 03. INDICES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_aire_fecha
    ON aire_madrid.mediciones_diarias (fecha);


CREATE INDEX IF NOT EXISTS idx_aire_magnitud
    ON aire_madrid.mediciones_diarias (magnitud);


CREATE INDEX IF NOT EXISTS idx_aire_estacion
    ON aire_madrid.mediciones_diarias (estacion);


CREATE INDEX IF NOT EXISTS idx_aire_punto_muestreo
    ON aire_madrid.mediciones_diarias (punto_muestreo);


CREATE INDEX IF NOT EXISTS idx_aire_magnitud_fecha
    ON aire_madrid.mediciones_diarias (
        magnitud,
        fecha
    );


CREATE INDEX IF NOT EXISTS idx_aire_estacion_magnitud_fecha
    ON aire_madrid.mediciones_diarias (
        estacion,
        magnitud,
        fecha
    );


-- =============================================================================
-- 04. ACTUALIZAR ESTADISTICAS DEL OPTIMIZADOR
-- =============================================================================

ANALYZE aire_madrid.mediciones_diarias;


-- =============================================================================
-- 05. VISTA DE CALIDAD DEL DATASET
-- =============================================================================

CREATE OR REPLACE VIEW aire_madrid.vw_calidad_datos AS

SELECT
    COUNT(*) AS registros,

    COUNT(*) FILTER (
        WHERE provincia IS NULL
    ) AS nulos_provincia,

    COUNT(*) FILTER (
        WHERE municipio IS NULL
    ) AS nulos_municipio,

    COUNT(*) FILTER (
        WHERE estacion IS NULL
    ) AS nulos_estacion,

    COUNT(*) FILTER (
        WHERE magnitud IS NULL
    ) AS nulos_magnitud,

    COUNT(*) FILTER (
        WHERE punto_muestreo IS NULL
    ) AS nulos_punto_muestreo,

    COUNT(*) FILTER (
        WHERE fecha IS NULL
    ) AS nulos_fecha,

    COUNT(*) FILTER (
        WHERE valor IS NULL
    ) AS nulos_valor,

    COUNT(*) FILTER (
        WHERE indicador_validez <> 'V'
    ) AS indicadores_no_validos,

    COUNT(*) FILTER (
        WHERE valor < 0
    ) AS valores_negativos,

    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos_iqr,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE es_atipico_iqr
        )
        / NULLIF(
            COUNT(*),
            0
        ),
        4
    ) AS porcentaje_atipicos

FROM aire_madrid.mediciones_diarias;


-- =============================================================================
-- 06. VISTA RESUMEN POR MAGNITUD
-- =============================================================================

CREATE OR REPLACE VIEW aire_madrid.vw_resumen_magnitudes AS

SELECT
    magnitud,

    COUNT(*) AS registros,

    COUNT(
        DISTINCT estacion
    ) AS estaciones,

    COUNT(
        DISTINCT punto_muestreo
    ) AS puntos_muestreo,

    ROUND(
        AVG(valor),
        4
    ) AS media,

    ROUND(
        STDDEV_SAMP(valor),
        4
    ) AS desviacion,

    MIN(valor) AS minimo,

    ROUND(
        PERCENTILE_CONT(0.25)
        WITHIN GROUP (
            ORDER BY valor
        )::numeric,
        4
    ) AS q1,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY valor
        )::numeric,
        4
    ) AS mediana,

    ROUND(
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (
            ORDER BY valor
        )::numeric,
        4
    ) AS q3,

    MAX(valor) AS maximo,

    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos_iqr,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE es_atipico_iqr
        )
        / NULLIF(
            COUNT(*),
            0
        ),
        4
    ) AS porcentaje_atipicos

FROM aire_madrid.mediciones_diarias

GROUP BY
    magnitud;


-- =============================================================================
-- 07. VISTA EVOLUCION MENSUAL
-- =============================================================================

CREATE OR REPLACE VIEW aire_madrid.vw_evolucion_mensual AS

SELECT
    anio,
    mes,
    magnitud,

    COUNT(*) AS registros,

    COUNT(
        DISTINCT estacion
    ) AS estaciones,

    ROUND(
        AVG(valor),
        4
    ) AS media,

    ROUND(
        PERCENTILE_CONT(0.50)
        WITHIN GROUP (
            ORDER BY valor
        )::numeric,
        4
    ) AS mediana,

    MIN(valor) AS minimo,

    MAX(valor) AS maximo,

    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos_iqr

FROM aire_madrid.mediciones_diarias

GROUP BY
    anio,
    mes,
    magnitud;


-- =============================================================================
-- 08. VISTA DE ATIPICOS
-- =============================================================================

CREATE OR REPLACE VIEW aire_madrid.vw_atipicos AS

SELECT
    magnitud,

    COUNT(*) AS registros,

    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos,

    COUNT(*) FILTER (
        WHERE NOT es_atipico_iqr
    ) AS no_atipicos,

    ROUND(
        100.0
        * COUNT(*) FILTER (
            WHERE es_atipico_iqr
        )
        / NULLIF(
            COUNT(*),
            0
        ),
        4
    ) AS porcentaje_atipicos

FROM aire_madrid.mediciones_diarias

GROUP BY
    magnitud;


-- =============================================================================
-- 09. VISTA RANKING DE ESTACIONES
-- =============================================================================

CREATE OR REPLACE VIEW aire_madrid.vw_ranking_estaciones AS

WITH resumen AS (

    SELECT
        magnitud,
        estacion,

        COUNT(*) AS registros,

        ROUND(
            AVG(valor),
            4
        ) AS media,

        ROUND(
            PERCENTILE_CONT(0.50)
            WITHIN GROUP (
                ORDER BY valor
            )::numeric,
            4
        ) AS mediana,

        MAX(valor) AS maximo,

        COUNT(*) FILTER (
            WHERE es_atipico_iqr
        ) AS atipicos_iqr

    FROM aire_madrid.mediciones_diarias

    GROUP BY
        magnitud,
        estacion
)

SELECT
    magnitud,
    estacion,
    registros,
    media,
    mediana,
    maximo,
    atipicos_iqr,

    DENSE_RANK() OVER (
        PARTITION BY magnitud
        ORDER BY media DESC
    ) AS ranking_media_magnitud

FROM resumen;


-- =============================================================================
-- 10. VERIFICAR VISTAS
-- =============================================================================

SELECT
    table_schema,
    table_name
FROM information_schema.views
WHERE table_schema = 'aire_madrid'
ORDER BY table_name;


-- =============================================================================
-- 11. CALIDAD GENERAL
-- =============================================================================

SELECT *
FROM aire_madrid.vw_calidad_datos;


-- =============================================================================
-- 12. DESCRIPTIVOS POR MAGNITUD
-- =============================================================================

SELECT *
FROM aire_madrid.vw_resumen_magnitudes
ORDER BY magnitud;


-- =============================================================================
-- 13. ATIPICOS POR MAGNITUD
-- =============================================================================

SELECT *
FROM aire_madrid.vw_atipicos
ORDER BY porcentaje_atipicos DESC;


-- =============================================================================
-- 14. EVOLUCION MENSUAL
-- =============================================================================

SELECT *
FROM aire_madrid.vw_evolucion_mensual
ORDER BY
    magnitud,
    anio,
    mes;


-- =============================================================================
-- 15. TOP ESTACIONES POR MAGNITUD
-- =============================================================================

SELECT *
FROM aire_madrid.vw_ranking_estaciones
WHERE ranking_media_magnitud <= 3
ORDER BY
    magnitud,
    ranking_media_magnitud,
    estacion;


-- =============================================================================
-- 16. CONTROL DE DUPLICADOS
-- =============================================================================

SELECT
    punto_muestreo,
    fecha,
    COUNT(*) AS registros

FROM aire_madrid.mediciones_diarias

GROUP BY
    punto_muestreo,
    fecha

HAVING COUNT(*) > 1

ORDER BY
    registros DESC,
    punto_muestreo,
    fecha;


-- =============================================================================
-- 17. CONTROL TEMPORAL
-- =============================================================================

SELECT
    anio,
    mes,

    MIN(fecha) AS fecha_minima,
    MAX(fecha) AS fecha_maxima,

    COUNT(*) AS mediciones,

    COUNT(
        DISTINCT fecha
    ) AS dias_con_datos,

    COUNT(
        DISTINCT estacion
    ) AS estaciones

FROM aire_madrid.mediciones_diarias

GROUP BY
    anio,
    mes

ORDER BY
    anio,
    mes;


-- =============================================================================
-- 18. CONTROL FINAL
-- =============================================================================

SELECT
    'mediciones_diarias' AS objeto,
    COUNT(*) AS registros
FROM aire_madrid.mediciones_diarias

UNION ALL

SELECT
    'vw_resumen_magnitudes',
    COUNT(*)
FROM aire_madrid.vw_resumen_magnitudes

UNION ALL

SELECT
    'vw_evolucion_mensual',
    COUNT(*)
FROM aire_madrid.vw_evolucion_mensual

UNION ALL

SELECT
    'vw_atipicos',
    COUNT(*)
FROM aire_madrid.vw_atipicos

UNION ALL

SELECT
    'vw_ranking_estaciones',
    COUNT(*)
FROM aire_madrid.vw_ranking_estaciones

ORDER BY objeto;


-- =============================================================================
-- FIN
-- =============================================================================

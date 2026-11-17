/*
===============================================================================
DASHBOARD EJECUTIVO ANUAL DE TAXIS - 2024
===============================================================================

Origen:
    nyc_taxi.viajes_limpios

Granularidad de la vista:
    mes + borough + tipo_pago + proveedor

Compatible con:
    - Grafana
    - Metabase
    - Apache Superset

La vista conserva sumas y contadores auxiliares para calcular correctamente
medias y porcentajes cuando se aplican filtros.
===============================================================================
*/


-- ============================================================================
-- 1. ELIMINACIÓN DE LA VISTA MATERIALIZADA ANTERIOR
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS
    nyc_taxi.mv_dashboard_ejecutivo_2024;


-- ============================================================================
-- 2. CREACIÓN DE LA VISTA MATERIALIZADA
-- ============================================================================

CREATE MATERIALIZED VIEW
    nyc_taxi.mv_dashboard_ejecutivo_2024
AS
SELECT
    -- ------------------------------------------------------------------------
    -- DIMENSIONES
    -- ------------------------------------------------------------------------

    DATE_TRUNC(
        'month',
        tpep_pickup_datetime
    )::date AS mes,

    EXTRACT(
        MONTH FROM tpep_pickup_datetime
    )::integer AS mes_num,

    TO_CHAR(
        tpep_pickup_datetime,
        'YYYY-MM'
    ) AS periodo,

    CASE EXTRACT(MONTH FROM tpep_pickup_datetime)::integer
        WHEN 1  THEN 'Enero'
        WHEN 2  THEN 'Febrero'
        WHEN 3  THEN 'Marzo'
        WHEN 4  THEN 'Abril'
        WHEN 5  THEN 'Mayo'
        WHEN 6  THEN 'Junio'
        WHEN 7  THEN 'Julio'
        WHEN 8  THEN 'Agosto'
        WHEN 9  THEN 'Septiembre'
        WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'
        WHEN 12 THEN 'Diciembre'
    END AS nombre_mes,

    COALESCE(
        borough_origen,
        'Desconocido'
    ) AS borough,

    COALESCE(
        vendor_id,
        -1
    ) AS proveedor_id,

    CASE COALESCE(vendor_id, -1)
        WHEN 1 THEN 'Creative Mobile Technologies'
        WHEN 2 THEN 'Curb Mobility'
        WHEN 6 THEN 'Myle Technologies'
        WHEN 7 THEN 'Helix'
        ELSE 'Proveedor desconocido'
    END AS proveedor,

    COALESCE(
        payment_type,
        -1
    ) AS tipo_pago_id,

    CASE COALESCE(payment_type, -1)
        WHEN 0 THEN 'Flex Fare'
        WHEN 1 THEN 'Tarjeta'
        WHEN 2 THEN 'Efectivo'
        WHEN 3 THEN 'Sin cargo'
        WHEN 4 THEN 'Disputa'
        WHEN 5 THEN 'Desconocido'
        WHEN 6 THEN 'Viaje anulado'
        ELSE 'Pago desconocido'
    END AS tipo_pago,

    -- ------------------------------------------------------------------------
    -- CONTADORES
    -- ------------------------------------------------------------------------

    COUNT(*)::bigint AS numero_viajes,

    COUNT(*) FILTER (
        WHERE tip_amount > 0
    )::bigint AS viajes_con_propina,

    -- ------------------------------------------------------------------------
    -- SUMAS NECESARIAS PARA KPI Y MEDIAS PONDERADAS
    -- ------------------------------------------------------------------------

    SUM(
        total_amount
    )::double precision AS suma_importe_total,

    SUM(
        trip_distance
    )::double precision AS suma_distancia,

    SUM(
        duracion_min
    )::double precision AS suma_duracion_min,

    SUM(
        tip_amount
    )::double precision AS suma_propina,

    SUM(
        passenger_count
    )::double precision AS suma_pasajeros,

    -- ------------------------------------------------------------------------
    -- CONTADORES NO NULOS
    --
    -- Son necesarios porque AVG() ignora valores NULL.
    -- ------------------------------------------------------------------------

    COUNT(
        total_amount
    )::bigint AS registros_importe,

    COUNT(
        trip_distance
    )::bigint AS registros_distancia,

    COUNT(
        duracion_min
    )::bigint AS registros_duracion,

    COUNT(
        tip_amount
    )::bigint AS registros_propina,

    COUNT(
        passenger_count
    )::bigint AS registros_pasajeros

FROM
    nyc_taxi.viajes_limpios

WHERE
    tpep_pickup_datetime >= TIMESTAMP '2024-01-01 00:00:00'

    AND tpep_pickup_datetime < TIMESTAMP '2025-01-01 00:00:00'

GROUP BY
    DATE_TRUNC(
        'month',
        tpep_pickup_datetime
    )::date,

    EXTRACT(
        MONTH FROM tpep_pickup_datetime
    )::integer,

    TO_CHAR(
        tpep_pickup_datetime,
        'YYYY-MM'
    ),

    CASE EXTRACT(MONTH FROM tpep_pickup_datetime)::integer
        WHEN 1  THEN 'Enero'
        WHEN 2  THEN 'Febrero'
        WHEN 3  THEN 'Marzo'
        WHEN 4  THEN 'Abril'
        WHEN 5  THEN 'Mayo'
        WHEN 6  THEN 'Junio'
        WHEN 7  THEN 'Julio'
        WHEN 8  THEN 'Agosto'
        WHEN 9  THEN 'Septiembre'
        WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'
        WHEN 12 THEN 'Diciembre'
    END,

    COALESCE(
        borough_origen,
        'Desconocido'
    ),

    COALESCE(
        vendor_id,
        -1
    ),

    CASE COALESCE(vendor_id, -1)
        WHEN 1 THEN 'Creative Mobile Technologies'
        WHEN 2 THEN 'Curb Mobility'
        WHEN 6 THEN 'Myle Technologies'
        WHEN 7 THEN 'Helix'
        ELSE 'Proveedor desconocido'
    END,

    COALESCE(
        payment_type,
        -1
    ),

    CASE COALESCE(payment_type, -1)
        WHEN 0 THEN 'Flex Fare'
        WHEN 1 THEN 'Tarjeta'
        WHEN 2 THEN 'Efectivo'
        WHEN 3 THEN 'Sin cargo'
        WHEN 4 THEN 'Disputa'
        WHEN 5 THEN 'Desconocido'
        WHEN 6 THEN 'Viaje anulado'
        ELSE 'Pago desconocido'
    END;


-- ============================================================================
-- 3. ÍNDICES
-- ============================================================================

CREATE UNIQUE INDEX
    idx_mv_dashboard_ejecutivo_2024_unico
ON
    nyc_taxi.mv_dashboard_ejecutivo_2024 (
        mes,
        borough,
        proveedor_id,
        tipo_pago_id
    );


CREATE INDEX
    idx_mv_dashboard_ejecutivo_2024_mes
ON
    nyc_taxi.mv_dashboard_ejecutivo_2024 (
        mes
    );


CREATE INDEX
    idx_mv_dashboard_ejecutivo_2024_borough
ON
    nyc_taxi.mv_dashboard_ejecutivo_2024 (
        borough
    );


CREATE INDEX
    idx_mv_dashboard_ejecutivo_2024_pago
ON
    nyc_taxi.mv_dashboard_ejecutivo_2024 (
        tipo_pago_id
    );


CREATE INDEX
    idx_mv_dashboard_ejecutivo_2024_proveedor
ON
    nyc_taxi.mv_dashboard_ejecutivo_2024 (
        proveedor_id
    );


-- ============================================================================
-- 4. ESTADÍSTICAS DE POSTGRESQL
-- ============================================================================

ANALYZE nyc_taxi.mv_dashboard_ejecutivo_2024;

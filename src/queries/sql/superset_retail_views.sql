-- =============================================================================
-- PRACTICA 5 - APACHE SUPERSET
-- Dataset: Online Retail II
-- Base de datos: curso_ia
-- Esquema origen: retail
-- Tabla origen: retail.online_retail_ii
--
-- Objetivo:
-- Crear las vistas analiticas que se utilizaran como datasets en Superset.
-- =============================================================================


-- =============================================================================
-- 0. ELIMINACION DE VISTAS PREVIAS
-- Permite ejecutar este script varias veces de forma reproducible.
-- =============================================================================

DROP VIEW IF EXISTS retail.vw_clientes_recurrentes;
DROP VIEW IF EXISTS retail.vw_cancelaciones;
DROP VIEW IF EXISTS retail.vw_top_productos;
DROP VIEW IF EXISTS retail.vw_ventas_pais;
DROP VIEW IF EXISTS retail.vw_ventas_mensuales;


-- =============================================================================
-- 1. VENTAS MENSUALES
--
-- Uso en Superset:
--   - Serie temporal mensual
--   - KPI ventas
--   - Evolucion de facturas
--   - Evolucion de clientes
--
-- Solo se consideran ventas NO canceladas.
-- =============================================================================

CREATE VIEW retail.vw_ventas_mensuales AS
SELECT
    DATE_TRUNC('month', invoice_date)::date AS fecha_mes,
    invoice_year AS anio,
    invoice_month AS mes,

    COUNT(DISTINCT invoice_no) AS numero_facturas,
    COUNT(DISTINCT customer_id)
        FILTER (WHERE customer_id IS NOT NULL) AS clientes_unicos,

    SUM(quantity) AS unidades_vendidas,

    SUM(total_amount) AS ventas_net_as,

    AVG(total_amount) AS importe_medio_linea

FROM retail.online_retail_ii

WHERE is_cancelled IS FALSE
  AND quantity > 0
  AND unit_price >= 0
  AND invoice_date IS NOT NULL

GROUP BY
    DATE_TRUNC('month', invoice_date)::date,
    invoice_year,
    invoice_month;


-- =============================================================================
-- 2. VENTAS POR PAIS
--
-- Uso en Superset:
--   - Grafico de barras por pais
--   - Ranking geografico
--   - KPI por pais
-- =============================================================================

CREATE VIEW retail.vw_ventas_pais AS
SELECT
    country AS pais,

    COUNT(DISTINCT invoice_no) AS numero_facturas,

    COUNT(DISTINCT customer_id)
        FILTER (WHERE customer_id IS NOT NULL) AS clientes_unicos,

    SUM(quantity) AS unidades_vendidas,

    SUM(total_amount) AS ventas_net_as,

    CASE
        WHEN COUNT(DISTINCT invoice_no) = 0 THEN 0
        ELSE
            SUM(total_amount)
            / COUNT(DISTINCT invoice_no)
    END AS ticket_medio

FROM retail.online_retail_ii

WHERE is_cancelled IS FALSE
  AND quantity > 0
  AND unit_price >= 0
  AND country IS NOT NULL

GROUP BY country;


-- =============================================================================
-- 3. TOP PRODUCTOS
--
-- Uso en Superset:
--   - Top productos por facturacion
--   - Top productos por unidades
--   - Comparacion entre productos
-- =============================================================================

CREATE VIEW retail.vw_top_productos AS
SELECT
    stock_code AS codigo_producto,
    description AS producto,

    COUNT(DISTINCT invoice_no) AS numero_facturas,

    SUM(quantity) AS unidades_vendidas,

    SUM(total_amount) AS ventas_net_as,

    AVG(unit_price) AS precio_medio

FROM retail.online_retail_ii

WHERE is_cancelled IS FALSE
  AND quantity > 0
  AND unit_price >= 0
  AND stock_code IS NOT NULL

GROUP BY
    stock_code,
    description;


-- =============================================================================
-- 4. CANCELACIONES Y DEVOLUCIONES
--
-- Uso en Superset:
--   - Analisis de cancelaciones
--   - Importe devuelto
--   - Unidades devueltas
--   - Distribucion por pais/producto/anio
--
-- Conservamos dimensiones para poder aplicar filtros en Superset.
-- =============================================================================

CREATE VIEW retail.vw_cancelaciones AS
SELECT
    invoice_no,

    invoice_date,

    invoice_year AS anio,
    invoice_month AS mes,

    country AS pais,

    stock_code AS codigo_producto,
    description AS producto,

    customer_id,

    quantity,

    unit_price,

    total_amount,

    is_cancelled AS cancelada,

    ABS(quantity) AS unidades_afectadas,

    ABS(total_amount) AS importe_afectado

FROM retail.online_retail_ii

WHERE is_cancelled IS TRUE
   OR quantity < 0;


-- =============================================================================
-- 5. CLIENTES RECURRENTES
--
-- Un cliente recurrente se define como aquel que tiene mas de una factura
-- de venta valida.
--
-- Uso en Superset:
--   - Numero de clientes recurrentes
--   - Facturacion de clientes recurrentes
--   - Ranking de clientes
-- =============================================================================

CREATE VIEW retail.vw_clientes_recurrentes AS
SELECT
    customer_id,

    COUNT(DISTINCT invoice_no) AS numero_facturas,

    COUNT(DISTINCT invoice_year) AS anios_activo,

    MIN(invoice_date) AS primera_compra,

    MAX(invoice_date) AS ultima_compra,

    SUM(quantity) AS unidades_compradas,

    SUM(total_amount) AS ventas_net_as,

    CASE
        WHEN COUNT(DISTINCT invoice_no) = 0 THEN 0
        ELSE
            SUM(total_amount)
            / COUNT(DISTINCT invoice_no)
    END AS ticket_medio

FROM retail.online_retail_ii

WHERE customer_id IS NOT NULL
  AND is_cancelled IS FALSE
  AND quantity > 0
  AND unit_price >= 0

GROUP BY customer_id

HAVING COUNT(DISTINCT invoice_no) > 1;


-- =============================================================================
-- 6. COMPROBACIONES
-- =============================================================================

SELECT
    'vw_ventas_mensuales' AS vista,
    COUNT(*) AS filas
FROM retail.vw_ventas_mensuales

UNION ALL

SELECT
    'vw_ventas_pais',
    COUNT(*)
FROM retail.vw_ventas_pais

UNION ALL

SELECT
    'vw_top_productos',
    COUNT(*)
FROM retail.vw_top_productos

UNION ALL

SELECT
    'vw_cancelaciones',
    COUNT(*)
FROM retail.vw_cancelaciones

UNION ALL

SELECT
    'vw_clientes_recurrentes',
    COUNT(*)
FROM retail.vw_clientes_recurrentes

ORDER BY vista;


-- =============================================================================
-- 7. COMPROBACION DE VENTAS TOTALES
-- Esta cifra sera posteriormente contrastada con Superset, Python y R.
-- =============================================================================

SELECT
    ROUND(SUM(total_amount)::numeric, 2) AS ventas_net_as_postgresql
FROM retail.online_retail_ii
WHERE is_cancelled IS FALSE
  AND quantity > 0
  AND unit_price >= 0;


-- =============================================================================
-- 8. LISTADO FINAL DE VISTAS SUPERSET
-- =============================================================================

SELECT
    table_schema,
    table_name
FROM information_schema.views
WHERE table_schema = 'retail'
  AND table_name LIKE 'vw_%'
ORDER BY table_name;

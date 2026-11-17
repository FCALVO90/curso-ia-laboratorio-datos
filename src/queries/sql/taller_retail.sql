-- ============================================================
-- CLASE 04 - TALLER DE QUERIES SQL
-- BASE DE DATOS: curso_ia
-- TABLA: online_retail_ii
-- MOTORES: POSTGRESQL / MARIADB
-- ============================================================

-- ============================================================
-- EJERCICIO 1
-- Mostrar los primeros 10 registros de la tabla.
-- Objetivo: practicar SELECT y LIMIT.
-- ============================================================

SELECT *
FROM retail.online_retail_ii
LIMIT 10;


-- ============================================================
-- EJERCICIO 2
-- Contar el numero total de registros.
-- Objetivo: practicar COUNT.
-- ============================================================

SELECT COUNT(*) AS total_registros
FROM retail.online_retail_ii;


-- ============================================================
-- EJERCICIO 3
-- Obtener todos los paises diferentes.
-- Ordenarlos alfabeticamente.
-- Objetivo: practicar DISTINCT y ORDER BY.
-- ============================================================

SELECT DISTINCT country
FROM retail.online_retail_ii
ORDER BY country;


-- ============================================================
-- EJERCICIO 4
-- Mostrar las primeras 10 operaciones realizadas
-- en United Kingdom.
-- Objetivo: practicar WHERE.
-- ============================================================

SELECT *
FROM retail.online_retail_ii
WHERE country = 'United Kingdom'
LIMIT 10;


-- ============================================================
-- EJERCICIO 5
-- Buscar operaciones cuya cantidad sea superior a 20.
-- Objetivo: practicar operadores de comparacion.
-- ============================================================

SELECT *
FROM retail.online_retail_ii
WHERE quantity > 20
LIMIT 10;


-- ============================================================
-- EJERCICIO 6
-- Buscar operaciones de United Kingdom cuya cantidad
-- sea superior a 20.
-- Objetivo: combinar condiciones utilizando AND.
-- ============================================================

SELECT *
FROM retail.online_retail_ii
WHERE country = 'United Kingdom'
  AND quantity > 20
LIMIT 10;


-- ============================================================
-- EJERCICIO 7
-- Contar cuantas operaciones existen por pais.
-- Ordenar de mayor a menor numero de operaciones.
-- Objetivo: practicar GROUP BY + COUNT + ORDER BY.
-- ============================================================

SELECT
    country,
    COUNT(*) AS operaciones
FROM retail.online_retail_ii
GROUP BY country
ORDER BY operaciones DESC;


-- ============================================================
-- EJERCICIO 8
-- Obtener los 10 paises con mayor facturacion.
-- Objetivo: practicar GROUP BY + SUM + ORDER BY + LIMIT.
-- ============================================================

SELECT
    country,
    SUM(total_amount) AS facturacion
FROM retail.online_retail_ii
GROUP BY country
ORDER BY facturacion DESC
LIMIT 10;


-- ============================================================
-- EJERCICIO 9
-- Obtener estadisticas de ventas para cada pais:
--   - numero de operaciones
--   - facturacion total
--   - importe medio
--   - importe minimo
--   - importe maximo
--
-- Objetivo:
-- practicar COUNT, SUM, AVG, MIN y MAX.
-- ============================================================

SELECT
    country,
    COUNT(*) AS operaciones,
    SUM(total_amount) AS facturacion,
    AVG(total_amount) AS importe_medio,
    MIN(total_amount) AS importe_minimo,
    MAX(total_amount) AS importe_maximo
FROM retail.online_retail_ii
GROUP BY country
ORDER BY facturacion DESC;


-- ============================================================
-- EJERCICIO 10 - RETO FINAL
--
-- Obtener los 10 clientes con mayor facturacion.
--
-- Para cada cliente mostrar:
--   - customer_id
--   - numero de operaciones
--   - cantidad total de productos
--   - facturacion total
--   - importe medio
--
-- Excluir registros sin customer_id.
--
-- Objetivo:
-- combinar WHERE, GROUP BY, COUNT, SUM, AVG,
-- ORDER BY y LIMIT.
-- ============================================================

SELECT
    customer_id,
    COUNT(*) AS operaciones,
    SUM(quantity) AS productos,
    SUM(total_amount) AS facturacion,
    AVG(total_amount) AS importe_medio
FROM retail.online_retail_ii
WHERE customer_id IS NOT NULL
GROUP BY customer_id
ORDER BY facturacion DESC
LIMIT 10;


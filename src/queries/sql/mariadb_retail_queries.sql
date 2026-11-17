-- ============================================================
-- mariadb - online retail ii
-- base de datos : curso_ia
-- tabla         : online_retail_ii
-- adaptado desde postgresql
-- ============================================================

use curso_ia;

-- ============================================================
-- 01. muestra del dataset
-- ============================================================
select
    invoice_no,
    stockcode,
    description,
    quantity,
    invoice_date,
    unit_price,
    customer_id,
    country,
    hoja_origen,
    is_cancelled,
    total_amount,
    year,
    month,
    day,
    hour
from curso_ia.online_retail_ii
order by invoice_date desc
limit 20;

-- ============================================================
-- 02. resumen general del dataset
-- ============================================================
select
    count(*) as total_lineas,
    count(distinct invoice_no) as total_facturas,
    count(distinct stockcode) as total_productos,
    count(distinct customer_id) as total_clientes,
    count(distinct country) as total_paises,
    min(invoice_date) as primera_fecha,
    max(invoice_date) as ultima_fecha,
    round(sum(total_amount), 2) as facturacion_total
from curso_ia.online_retail_ii;

-- ============================================================
-- 03. calidad de datos - nulos
-- ============================================================
select
    count(*) as total_filas,
    sum(case when invoice_no is null then 1 else 0 end) as invoice_no_nulos,
    sum(case when stockcode is null then 1 else 0 end) as stock_code_nulos,
    sum(case when description is null then 1 else 0 end) as description_nulos,
    sum(case when quantity is null then 1 else 0 end) as quantity_nulos,
    sum(case when invoice_date is null then 1 else 0 end) as invoice_date_nulos,
    sum(case when unit_price is null then 1 else 0 end) as unit_price_nulos,
    sum(case when customer_id is null then 1 else 0 end) as customer_id_nulos,
    sum(case when country is null then 1 else 0 end) as country_nulos,
    sum(case when total_amount is null then 1 else 0 end) as total_amount_nulos
from curso_ia.online_retail_ii;

-- ============================================================
-- 04. calidad de datos - valores anomalos
-- ============================================================
select
    count(*) as total_filas,
    sum(case when quantity < 0 then 1 else 0 end) as cantidad_negativa,
    sum(case when quantity = 0 then 1 else 0 end) as cantidad_cero,
    sum(case when unit_price < 0 then 1 else 0 end) as precio_negativo,
    sum(case when unit_price = 0 then 1 else 0 end) as precio_cero,
    sum(case when total_amount < 0 then 1 else 0 end) as importe_negativo,
    sum(case when is_cancelled = 1 then 1 else 0 end) as lineas_canceladas
from curso_ia.online_retail_ii;

-- ============================================================
-- 05. facturacion por pais
-- ============================================================
select country, count(*) as total_lineas,
       count(distinct invoice_no) as total_facturas,
       count(distinct customer_id) as total_clientes,
       sum(quantity) as unidades,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by country
order by facturacion desc;

-- ============================================================
-- 06. top 20 productos por facturacion
-- ============================================================
select stockcode, description, sum(quantity) as unidades_vendidas,
       count(distinct invoice_no) as numero_facturas,
       round(avg(unit_price), 2) as precio_medio,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by stockcode, description
order by facturacion desc
limit 20;

-- ============================================================
-- 07. top 20 productos por unidades
-- ============================================================
select stockcode, description, sum(quantity) as unidades_vendidas,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0
group by stockcode, description
order by unidades_vendidas desc
limit 20;

-- ============================================================
-- 08. top 20 clientes
-- ============================================================
select customer_id, count(distinct invoice_no) as numero_facturas,
       count(distinct stockcode) as productos_distintos,
       sum(quantity) as unidades,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where customer_id is not null and is_cancelled = 0
  and quantity > 0 and total_amount > 0
group by customer_id
order by facturacion desc
limit 20;

-- ============================================================
-- 09. facturacion anual
-- ============================================================
select year as anio, count(distinct invoice_no) as facturas,
       count(distinct customer_id) as clientes, sum(quantity) as unidades,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by year
order by year;

-- ============================================================
-- 10. facturacion mensual
-- ============================================================
select cast(date_format(invoice_date, '%y-%m-01') as date) as mes,
       count(distinct invoice_no) as facturas,
       count(distinct customer_id) as clientes,
       sum(quantity) as unidades,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by cast(date_format(invoice_date, '%y-%m-01') as date)
order by mes;

-- ============================================================
-- 11. facturacion por anio y mes
-- ============================================================
select year as anio, month as mes,
       count(distinct invoice_no) as facturas,
       sum(quantity) as unidades, round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by year, month
order by year, month;

-- ============================================================
-- 12. actividad por hora
-- ============================================================
select hour as hora, count(distinct invoice_no) as facturas,
       count(*) as lineas, sum(quantity) as unidades,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by hour
order by hour;

-- ============================================================
-- 13. cancelaciones
-- ============================================================
select is_cancelled, count(*) as lineas,
       count(distinct invoice_no) as facturas,
       sum(quantity) as cantidad, round(sum(total_amount), 2) as importe
from curso_ia.online_retail_ii
group by is_cancelled
order by is_cancelled;

-- ============================================================
-- 14. cancelaciones por pais
-- ============================================================
select country,
       sum(case when is_cancelled = 1 then 1 else 0 end) as lineas_canceladas,
       count(distinct case when is_cancelled = 1 then invoice_no end) as facturas_canceladas,
       round(sum(case when is_cancelled = 1 then total_amount else 0 end), 2) as importe_cancelado
from curso_ia.online_retail_ii
group by country
order by lineas_canceladas desc;

-- ============================================================
-- 15. devoluciones
-- ============================================================
select invoice_no, invoice_date, customer_id, stockcode, description,
       country, quantity, unit_price, total_amount, is_cancelled
from curso_ia.online_retail_ii
where quantity < 0
order by invoice_date desc
limit 100;

-- ============================================================
-- 16. ticket por factura
-- ============================================================
select invoice_no, min(invoice_date) as fecha_factura, customer_id, country,
       sum(quantity) as unidades, count(*) as lineas,
       count(distinct stockcode) as productos_distintos,
       round(sum(total_amount), 2) as total_factura
from curso_ia.online_retail_ii
where is_cancelled = 0 and quantity > 0 and total_amount > 0
group by invoice_no, customer_id, country
order by total_factura desc
limit 50;

-- ============================================================
-- 17. ticket medio
-- ============================================================
with facturas as (
    select invoice_no, sum(total_amount) as total_factura
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by invoice_no
)
select count(*) as numero_facturas,
       round(avg(total_factura), 2) as ticket_medio,
       round(min(total_factura), 2) as ticket_minimo,
       round(max(total_factura), 2) as ticket_maximo
from facturas;

-- ============================================================
-- 18. ticket medio por pais
-- ============================================================
with facturas as (
    select country, invoice_no, sum(total_amount) as total_factura
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by country, invoice_no
)
select country, count(*) as numero_facturas,
       round(avg(total_factura), 2) as ticket_medio,
       round(sum(total_factura), 2) as facturacion
from facturas
group by country
order by facturacion desc;

-- ============================================================
-- 19. clientes por pais
-- ============================================================
select country, count(distinct customer_id) as clientes,
       count(distinct invoice_no) as facturas,
       round(sum(total_amount), 2) as facturacion
from curso_ia.online_retail_ii
where customer_id is not null and is_cancelled = 0 and total_amount > 0
group by country
order by clientes desc;

-- ============================================================
-- 20. top 5 productos por pais
-- ============================================================
with productos_pais as (
    select country, stockcode, description,
           sum(quantity) as unidades_vendidas,
           sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by country, stockcode, description
),
ranking_productos as (
    select country, stockcode, description, unidades_vendidas, facturacion,
           row_number() over (partition by country order by facturacion desc) as posicion
    from productos_pais
)
select country, posicion, stockcode, description, unidades_vendidas,
       round(facturacion, 2) as facturacion
from ranking_productos
where posicion <= 5
order by country, posicion;

-- ============================================================
-- 21. ranking de paises
-- ============================================================
with ventas_pais as (
    select country, sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by country
)
select dense_rank() over (order by facturacion desc) as posicion,
       country, round(facturacion, 2) as facturacion
from ventas_pais
order by posicion;

-- ============================================================
-- 22. evolucion mensual con mes anterior
-- ============================================================
with ventas_mensuales as (
    select cast(date_format(invoice_date, '%y-%m-01') as date) as mes,
           sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by cast(date_format(invoice_date, '%y-%m-01') as date)
)
select mes, round(facturacion, 2) as facturacion,
       round(lag(facturacion) over (order by mes), 2) as facturacion_mes_anterior
from ventas_mensuales
order by mes;

-- ============================================================
-- 23. crecimiento mensual porcentual
-- ============================================================
with ventas_mensuales as (
    select cast(date_format(invoice_date, '%y-%m-01') as date) as mes,
           sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by cast(date_format(invoice_date, '%y-%m-01') as date)
),
comparacion as (
    select mes, facturacion,
           lag(facturacion) over (order by mes) as facturacion_anterior
    from ventas_mensuales
)
select mes, round(facturacion, 2) as facturacion,
       round(facturacion_anterior, 2) as facturacion_anterior,
       round((facturacion - facturacion_anterior) /
             nullif(facturacion_anterior, 0) * 100, 2) as crecimiento_porcentaje
from comparacion
order by mes;

-- ============================================================
-- 24. facturacion acumulada
-- ============================================================
with ventas_mensuales as (
    select cast(date_format(invoice_date, '%y-%m-01') as date) as mes,
           sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where is_cancelled = 0 and quantity > 0 and total_amount > 0
    group by cast(date_format(invoice_date, '%y-%m-01') as date)
)
select mes, round(facturacion, 2) as facturacion_mensual,
       round(sum(facturacion) over (
           order by mes rows between unbounded preceding and current row
       ), 2) as facturacion_acumulada
from ventas_mensuales
order by mes;

-- ============================================================
-- 25. ranking global de clientes
-- ============================================================
with clientes as (
    select customer_id, count(distinct invoice_no) as facturas,
           sum(total_amount) as facturacion
    from curso_ia.online_retail_ii
    where customer_id is not null and is_cancelled = 0
      and quantity > 0 and total_amount > 0
    group by customer_id
)
select row_number() over (order by facturacion desc) as posicion,
       customer_id, facturas, round(facturacion, 2) as facturacion
from clientes
order by posicion
limit 100;

-- ============================================================
-- 26. clientes recurrentes
-- ============================================================
select customer_id, count(distinct invoice_no) as numero_facturas,
       min(invoice_date) as primera_compra, max(invoice_date) as ultima_compra,
       round(sum(total_amount), 2) as facturacion_total
from curso_ia.online_retail_ii
where customer_id is not null and is_cancelled = 0
  and quantity > 0 and total_amount > 0
group by customer_id
having count(distinct invoice_no) > 1
order by numero_facturas desc;

-- ============================================================
-- 27. resumen por hoja de origen
-- ============================================================
select hoja_origen, count(*) as total_lineas,
       count(distinct invoice_no) as facturas,
       count(distinct customer_id) as clientes,
       count(distinct stockcode) as productos,
       min(invoice_date) as primera_fecha, max(invoice_date) as ultima_fecha,
       round(sum(total_amount), 2) as importe_total
from curso_ia.online_retail_ii
group by hoja_origen
order by hoja_origen;

-- ============================================================
-- 28. distribucion de precios
-- mediana calculada con row_number para compatibilidad mariadb
-- ============================================================
with precios_ordenados as (
    select unit_price,
           row_number() over (order by unit_price) as posicion,
           count(*) over () as total_registros
    from curso_ia.online_retail_ii
    where unit_price > 0
),
mediana as (
    select avg(unit_price) as valor_mediana
    from precios_ordenados
    where posicion in (
        floor((total_registros + 1) / 2),
        floor((total_registros + 2) / 2)
    )
)
select count(*) as numero_registros,
       round(min(unit_price), 2) as precio_minimo,
       round(avg(unit_price), 2) as precio_medio,
       round(max(unit_price), 2) as precio_maximo,
       round((select valor_mediana from mediana), 2) as mediana
from curso_ia.online_retail_ii
where unit_price > 0;

-- ============================================================
-- 29. top 20 precios unitarios
-- ============================================================
select stockcode, description, unit_price, invoice_no, invoice_date, country
from curso_ia.online_retail_ii
where unit_price > 0
order by unit_price desc
limit 20;

-- ============================================================
-- 30. resumen final por anio
-- ============================================================
select year as anio,
       count(*) as lineas,
       count(distinct invoice_no) as facturas,
       count(distinct customer_id) as clientes,
       count(distinct stockcode) as productos,
       count(distinct country) as paises,
       sum(case when is_cancelled = 0 and quantity > 0 then quantity else 0 end) as unidades_vendidas,
       count(distinct case when is_cancelled = 1 then invoice_no end) as facturas_canceladas,
       round(sum(case when is_cancelled = 0 and total_amount > 0 then total_amount else 0 end), 2) as facturacion
from curso_ia.online_retail_ii
group by year
order by year;

-- ============================================================
-- fin mariadb
-- ============================================================

-- ============================================================
-- postgresql - online retail ii
-- base de datos : curso_ia
-- schema        : retail
-- tabla         : online_retail_ii
-- ============================================================

set search_path to retail, public;


-- ============================================================
-- 01. muestra del dataset
-- ============================================================

select
    invoice_no,
    stock_code,
    description,
    quantity,
    invoice_date,
    unit_price,
    customer_id,
    country,
    hoja_origen,
    is_cancelled,
    total_amount,
    invoice_year,
    invoice_month,
    invoice_day,
    invoice_hour
from retail.online_retail_ii
order by invoice_date desc
limit 20;


-- ============================================================
-- 02. resumen general del dataset
-- ============================================================

select
    count(*) as total_lineas,
    count(distinct invoice_no) as total_facturas,
    count(distinct stock_code) as total_productos,
    count(distinct customer_id) as total_clientes,
    count(distinct country) as total_paises,
    min(invoice_date) as primera_fecha,
    max(invoice_date) as ultima_fecha,
    round(sum(total_amount)::numeric, 2) as facturacion_total
from retail.online_retail_ii;


-- ============================================================
-- 03. calidad de datos - nulos
-- ============================================================

select
    count(*) as total_filas,

    count(*) filter (
        where invoice_no is null
    ) as invoice_no_nulos,

    count(*) filter (
        where stock_code is null
    ) as stock_code_nulos,

    count(*) filter (
        where description is null
    ) as description_nulos,

    count(*) filter (
        where quantity is null
    ) as quantity_nulos,

    count(*) filter (
        where invoice_date is null
    ) as invoice_date_nulos,

    count(*) filter (
        where unit_price is null
    ) as unit_price_nulos,

    count(*) filter (
        where customer_id is null
    ) as customer_id_nulos,

    count(*) filter (
        where country is null
    ) as country_nulos,

    count(*) filter (
        where total_amount is null
    ) as total_amount_nulos

from retail.online_retail_ii;


-- ============================================================
-- 04. calidad de datos - valores anomalos
-- ============================================================

select
    count(*) as total_filas,

    count(*) filter (where quantity < 0)
        as cantidad_negativa,

    count(*) filter (where quantity = 0)
        as cantidad_cero,

    count(*) filter (where unit_price < 0)
        as precio_negativo,

    count(*) filter (where unit_price = 0)
        as precio_cero,

    count(*) filter (where total_amount < 0)
        as importe_negativo,

    count(*) filter (where is_cancelled is true)
        as lineas_canceladas

from retail.online_retail_ii;


-- ============================================================
-- 05. facturacion por pais
-- ============================================================

select
    country,
    count(*) as total_lineas,
    count(distinct invoice_no) as total_facturas,
    count(distinct customer_id) as total_clientes,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by country
order by facturacion desc;


-- ============================================================
-- 06. top 20 productos por facturacion
-- ============================================================

select
    stock_code,
    description,
    sum(quantity) as unidades_vendidas,
    count(distinct invoice_no) as numero_facturas,
    round(avg(unit_price)::numeric, 2) as precio_medio,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by stock_code, description
order by facturacion desc
limit 20;


-- ============================================================
-- 07. top 20 productos por unidades
-- ============================================================

select
    stock_code,
    description,
    sum(quantity) as unidades_vendidas,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
group by stock_code, description
order by unidades_vendidas desc
limit 20;


-- ============================================================
-- 08. top 20 clientes
-- ============================================================

select
    customer_id,
    count(distinct invoice_no) as numero_facturas,
    count(distinct stock_code) as productos_distintos,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where customer_id is not null
  and is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by customer_id
order by facturacion desc
limit 20;


-- ============================================================
-- 09. facturacion anual
-- ============================================================

select
    invoice_year as anio,
    count(distinct invoice_no) as facturas,
    count(distinct customer_id) as clientes,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by invoice_year
order by invoice_year;


-- ============================================================
-- 10. facturacion mensual
-- ============================================================

select
    date_trunc('month', invoice_date) as mes,
    count(distinct invoice_no) as facturas,
    count(distinct customer_id) as clientes,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by date_trunc('month', invoice_date)
order by mes;


-- ============================================================
-- 11. facturacion por anio y mes
-- ============================================================

select
    invoice_year as anio,
    invoice_month as mes,
    count(distinct invoice_no) as facturas,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by invoice_year, invoice_month
order by invoice_year, invoice_month;


-- ============================================================
-- 12. actividad por hora
-- ============================================================

select
    invoice_hour as hora,
    count(distinct invoice_no) as facturas,
    count(*) as lineas,
    sum(quantity) as unidades,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by invoice_hour
order by invoice_hour;


-- ============================================================
-- 13. cancelaciones
-- ============================================================

select
    is_cancelled,
    count(*) as lineas,
    count(distinct invoice_no) as facturas,
    sum(quantity) as cantidad,
    round(sum(total_amount)::numeric, 2) as importe
from retail.online_retail_ii
group by is_cancelled
order by is_cancelled;


-- ============================================================
-- 14. cancelaciones por pais
-- ============================================================

select
    country,

    count(*) filter (
        where is_cancelled is true
    ) as lineas_canceladas,

    count(distinct invoice_no) filter (
        where is_cancelled is true
    ) as facturas_canceladas,

    round(
        (
            sum(total_amount) filter (
                where is_cancelled is true
            )
        )::numeric,
        2
    ) as importe_cancelado

from retail.online_retail_ii
group by country
order by lineas_canceladas desc;


-- ============================================================
-- 15. devoluciones
-- ============================================================

select
    invoice_no,
    invoice_date,
    customer_id,
    stock_code,
    description,
    country,
    quantity,
    unit_price,
    total_amount,
    is_cancelled
from retail.online_retail_ii
where quantity < 0
order by invoice_date desc
limit 100;


-- ============================================================
-- 16. ticket por factura
-- ============================================================

select
    invoice_no,
    min(invoice_date) as fecha_factura,
    customer_id,
    country,
    sum(quantity) as unidades,
    count(*) as lineas,
    count(distinct stock_code) as productos_distintos,
    round(sum(total_amount)::numeric, 2) as total_factura
from retail.online_retail_ii
where is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by invoice_no, customer_id, country
order by total_factura desc
limit 50;


-- ============================================================
-- 17. ticket medio
-- ============================================================

with facturas as
(
    select
        invoice_no,
        sum(total_amount) as total_factura
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by invoice_no
)
select
    count(*) as numero_facturas,
    round(avg(total_factura)::numeric, 2) as ticket_medio,
    round(min(total_factura)::numeric, 2) as ticket_minimo,
    round(max(total_factura)::numeric, 2) as ticket_maximo
from facturas;


-- ============================================================
-- 18. ticket medio por pais
-- ============================================================

with facturas as
(
    select
        country,
        invoice_no,
        sum(total_amount) as total_factura
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by country, invoice_no
)
select
    country,
    count(*) as numero_facturas,
    round(avg(total_factura)::numeric, 2) as ticket_medio,
    round(sum(total_factura)::numeric, 2) as facturacion
from facturas
group by country
order by facturacion desc;


-- ============================================================
-- 19. clientes por pais
-- ============================================================

select
    country,
    count(distinct customer_id) as clientes,
    count(distinct invoice_no) as facturas,
    round(sum(total_amount)::numeric, 2) as facturacion
from retail.online_retail_ii
where customer_id is not null
  and is_cancelled is false
  and total_amount > 0
group by country
order by clientes desc;


-- ============================================================
-- 20. top 5 productos por pais
-- ============================================================

with productos_pais as
(
    select
        country,
        stock_code,
        description,
        sum(quantity) as unidades_vendidas,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by country, stock_code, description
),
ranking_productos as
(
    select
        country,
        stock_code,
        description,
        unidades_vendidas,
        facturacion,
        row_number() over (
            partition by country
            order by facturacion desc
        ) as posicion
    from productos_pais
)
select
    country,
    posicion,
    stock_code,
    description,
    unidades_vendidas,
    round(facturacion::numeric, 2) as facturacion
from ranking_productos
where posicion <= 5
order by country, posicion;


-- ============================================================
-- 21. ranking de paises
-- ============================================================

with ventas_pais as
(
    select
        country,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by country
)
select
    dense_rank() over (
        order by facturacion desc
    ) as posicion,
    country,
    round(facturacion::numeric, 2) as facturacion
from ventas_pais
order by posicion;


-- ============================================================
-- 22. evolucion mensual con mes anterior
-- ============================================================

with ventas_mensuales as
(
    select
        date_trunc('month', invoice_date) as mes,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by date_trunc('month', invoice_date)
)
select
    mes,
    round(facturacion::numeric, 2) as facturacion,
    round(
        lag(facturacion) over (
            order by mes
        )::numeric,
        2
    ) as facturacion_mes_anterior
from ventas_mensuales
order by mes;


-- ============================================================
-- 23. crecimiento mensual porcentual
-- ============================================================

with ventas_mensuales as
(
    select
        date_trunc('month', invoice_date) as mes,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by date_trunc('month', invoice_date)
),
comparacion as
(
    select
        mes,
        facturacion,
        lag(facturacion) over (
            order by mes
        ) as facturacion_anterior
    from ventas_mensuales
)
select
    mes,
    round(facturacion::numeric, 2) as facturacion,
    round(facturacion_anterior::numeric, 2)
        as facturacion_anterior,
    round(
        (
            (facturacion - facturacion_anterior)
            / nullif(facturacion_anterior, 0)
            * 100
        )::numeric,
        2
    ) as crecimiento_porcentaje
from comparacion
order by mes;


-- ============================================================
-- 24. facturacion acumulada
-- ============================================================

with ventas_mensuales as
(
    select
        date_trunc('month', invoice_date) as mes,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by date_trunc('month', invoice_date)
)
select
    mes,
    round(facturacion::numeric, 2) as facturacion_mensual,
    round(
        sum(facturacion) over (
            order by mes
            rows between unbounded preceding and current row
        )::numeric,
        2
    ) as facturacion_acumulada
from ventas_mensuales
order by mes;


-- ============================================================
-- 25. ranking global de clientes
-- ============================================================

with clientes as
(
    select
        customer_id,
        count(distinct invoice_no) as facturas,
        sum(total_amount) as facturacion
    from retail.online_retail_ii
    where customer_id is not null
      and is_cancelled is false
      and quantity > 0
      and total_amount > 0
    group by customer_id
)
select
    row_number() over (
        order by facturacion desc
    ) as posicion,
    customer_id,
    facturas,
    round(facturacion::numeric, 2) as facturacion
from clientes
order by posicion
limit 100;


-- ============================================================
-- 26. clientes recurrentes
-- ============================================================

select
    customer_id,
    count(distinct invoice_no) as numero_facturas,
    min(invoice_date) as primera_compra,
    max(invoice_date) as ultima_compra,
    round(sum(total_amount)::numeric, 2) as facturacion_total
from retail.online_retail_ii
where customer_id is not null
  and is_cancelled is false
  and quantity > 0
  and total_amount > 0
group by customer_id
having count(distinct invoice_no) > 1
order by numero_facturas desc;


-- ============================================================
-- 27. resumen por hoja de origen
-- ============================================================

select
    hoja_origen,
    count(*) as total_lineas,
    count(distinct invoice_no) as facturas,
    count(distinct customer_id) as clientes,
    count(distinct stock_code) as productos,
    min(invoice_date) as primera_fecha,
    max(invoice_date) as ultima_fecha,
    round(sum(total_amount)::numeric, 2) as importe_total
from retail.online_retail_ii
group by hoja_origen
order by hoja_origen;


-- ============================================================
-- 28. distribucion de precios
-- ============================================================

select
    count(*) as numero_registros,
    round(min(unit_price)::numeric, 2) as precio_minimo,
    round(avg(unit_price)::numeric, 2) as precio_medio,
    round(max(unit_price)::numeric, 2) as precio_maximo,
    round(
        percentile_cont(0.50)
        within group (order by unit_price)::numeric,
        2
    ) as mediana
from retail.online_retail_ii
where unit_price > 0;


-- ============================================================
-- 29. top 20 precios unitarios
-- ============================================================

select
    stock_code,
    description,
    unit_price,
    invoice_no,
    invoice_date,
    country
from retail.online_retail_ii
where unit_price > 0
order by unit_price desc
limit 20;


-- ============================================================
-- 30. resumen final por anio
-- ============================================================

select
    invoice_year as anio,
    count(*) as lineas,
    count(distinct invoice_no) as facturas,
    count(distinct customer_id) as clientes,
    count(distinct stock_code) as productos,
    count(distinct country) as paises,

    sum(quantity) filter (
        where is_cancelled is false
          and quantity > 0
    ) as unidades_vendidas,

    count(distinct invoice_no) filter (
        where is_cancelled is true
    ) as facturas_canceladas,

    round(
        (
            sum(total_amount) filter (
                where is_cancelled is false
                  and total_amount > 0
            )
        )::numeric,
        2
    ) as facturacion

from retail.online_retail_ii
group by invoice_year
order by invoice_year;


-- ============================================================
-- fin postgresql
-- ============================================================
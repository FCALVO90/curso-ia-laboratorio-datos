# ============================================================
# ONLINE RETAIL II
# ANALISIS DESCRIPTIVO + VISUALIZACION + CARGA EN MARIADB
# ============================================================

library(readxl)
library(dplyr)
library(ggplot2)
library(DBI)
library(RMariaDB)

cat("============================================================\n")
cat(" ONLINE RETAIL II - R + MARIADB\n")
cat("============================================================\n")

# ============================================================
# 1. RUTAS
# ============================================================

archivo <- file.path(
  Sys.getenv("HOME"),
  "curso_ia",
  "datos",
  "raw",
  "retail",
  "online_retail_II.xlsx"
)

salida <- file.path(
  Sys.getenv("HOME"),
  "curso_ia",
  "salidas",
  "retail",
  "r",
  "graficos"
)

dir.create(salida, recursive = TRUE, showWarnings = FALSE)

if (!file.exists(archivo)) {
  stop(paste("NO EXISTE:", archivo))
}

cat("\nArchivo encontrado:\n")
cat(archivo, "\n")

# ============================================================
# 2. LEER TODAS LAS HOJAS
# ============================================================

hojas <- excel_sheets(archivo)

cat("\nHOJAS DEL EXCEL:\n")
print(hojas)

lista <- lapply(hojas, function(hoja) {

  cat("\nLeyendo:", hoja, "\n")

  x <- read_excel(
    archivo,
    sheet = hoja,
    guess_max = 100000
  )

  x$hoja_origen <- hoja

  return(x)
})

df <- bind_rows(lista)

cat("\n============================================================\n")
cat(" DATASET CARGADO EN R\n")
cat("============================================================\n")

cat("Filas:", nrow(df), "\n")
cat("Columnas:", ncol(df), "\n")

# ============================================================
# 3. NORMALIZAR COLUMNAS
# ============================================================

names(df) <- tolower(names(df))
names(df) <- gsub(" ", "_", names(df))
names(df) <- gsub("\\.", "_", names(df))

if ("invoice" %in% names(df)) {
  names(df)[names(df) == "invoice"] <- "invoice_no"
}

if ("invoicedate" %in% names(df)) {
  names(df)[names(df) == "invoicedate"] <- "invoice_date"
}

if ("price" %in% names(df)) {
  names(df)[names(df) == "price"] <- "unit_price"
}

cat("\nCOLUMNAS:\n")
print(names(df))

# ============================================================
# 4. CONVERSIONES
# ============================================================

df$invoice_no <- as.character(df$invoice_no)
df$stockcode <- as.character(df$stockcode)
df$description <- as.character(df$description)
df$customer_id <- as.character(df$customer_id)
df$country <- as.character(df$country)

df$quantity <- as.numeric(df$quantity)
df$unit_price <- as.numeric(df$unit_price)

df$invoice_date <- as.POSIXct(
  df$invoice_date,
  tz = "UTC"
)

# ============================================================
# 5. VARIABLES DERIVADAS
# ============================================================

df <- df %>%
  mutate(
    is_cancelled = grepl("^C", toupper(invoice_no)),
    total_amount = quantity * unit_price,
    year = as.integer(format(invoice_date, "%Y")),
    month = as.integer(format(invoice_date, "%m")),
    day = as.integer(format(invoice_date, "%d")),
    hour = as.integer(format(invoice_date, "%H"))
  )

# ============================================================
# 6. ANALISIS DESCRIPTIVO
# ============================================================

cat("\n============================================================\n")
cat(" ESTRUCTURA\n")
cat("============================================================\n")

str(df)

cat("\n============================================================\n")
cat(" PRIMERAS FILAS\n")
cat("============================================================\n")

print(head(df, 10))

cat("\n============================================================\n")
cat(" RESUMEN\n")
cat("============================================================\n")

print(summary(df))

cat("\n============================================================\n")
cat(" VALORES NULOS\n")
cat("============================================================\n")

nulos <- sort(
  colSums(is.na(df)),
  decreasing = TRUE
)

print(nulos)

cat("\n============================================================\n")
cat(" DUPLICADOS\n")
cat("============================================================\n")

cat(
  "Duplicados:",
  sum(duplicated(df)),
  "\n"
)

cat("\n============================================================\n")
cat(" INDICADORES\n")
cat("============================================================\n")

cat(
  "Facturas:",
  length(unique(na.omit(df$invoice_no))),
  "\n"
)

cat(
  "Productos:",
  length(unique(na.omit(df$stockcode))),
  "\n"
)

cat(
  "Clientes:",
  length(unique(na.omit(df$customer_id))),
  "\n"
)

cat(
  "Paises:",
  length(unique(na.omit(df$country))),
  "\n"
)

cat(
  "Cancelaciones:",
  sum(df$is_cancelled, na.rm = TRUE),
  "\n"
)

cat(
  "Cantidades negativas:",
  sum(df$quantity < 0, na.rm = TRUE),
  "\n"
)

cat(
  "Precios negativos:",
  sum(df$unit_price < 0, na.rm = TRUE),
  "\n"
)

# ============================================================
# 7. DATASET DE VENTAS VALIDAS PARA VISUALIZACIONES
# ============================================================

ventas <- df %>%
  filter(
    !is_cancelled,
    quantity > 0,
    unit_price > 0,
    !is.na(invoice_date)
  )

# ============================================================
# 8. PLOT 1 - DISTRIBUCION DE PRECIOS
# ============================================================

limite <- quantile(
  ventas$unit_price,
  0.99,
  na.rm = TRUE
)

p1 <- ventas %>%
  filter(unit_price <= limite) %>%
  ggplot(aes(x = unit_price)) +
  geom_histogram(
    bins = 50,
    fill = "steelblue",
    color = "white"
  ) +
  theme_minimal() +
  labs(
    title = "Distribucion del precio unitario",
    subtitle = "Hasta el percentil 99",
    x = "Precio unitario",
    y = "Frecuencia"
  )

print(p1)

ggsave(
  file.path(salida, "01_distribucion_precios.png"),
  p1,
  width = 12,
  height = 6
)

# ============================================================
# 9. PLOT 2 - TOP PAISES
# ============================================================

paises <- ventas %>%
  count(country, sort = TRUE) %>%
  slice_head(n = 15)

p2 <- ggplot(
  paises,
  aes(
    x = reorder(country, n),
    y = n
  )
) +
  geom_col(fill = "darkorange") +
  coord_flip() +
  theme_minimal() +
  labs(
    title = "Top 15 paises",
    x = "Pais",
    y = "Numero de registros"
  )

print(p2)

ggsave(
  file.path(salida, "02_top_paises.png"),
  p2,
  width = 12,
  height = 7
)

# ============================================================
# 10. PLOT 3 - FACTURACION MENSUAL
# ============================================================

mensual <- ventas %>%
  mutate(
    periodo = as.Date(
      format(invoice_date, "%Y-%m-01")
    )
  ) %>%
  group_by(periodo) %>%
  summarise(
    facturacion = sum(
      total_amount,
      na.rm = TRUE
    ),
    .groups = "drop"
  )

p3 <- ggplot(
  mensual,
  aes(
    x = periodo,
    y = facturacion
  )
) +
  geom_line(
    color = "darkgreen",
    linewidth = 1
  ) +
  geom_point(
    color = "darkgreen"
  ) +
  theme_minimal() +
  labs(
    title = "Evolucion mensual de la facturacion",
    x = "Mes",
    y = "Facturacion"
  )

print(p3)

ggsave(
  file.path(salida, "03_facturacion_mensual.png"),
  p3,
  width = 14,
  height = 6
)

# ============================================================
# 11. PLOT 4 - TOP PRODUCTOS
# ============================================================

productos <- ventas %>%
  filter(
    !is.na(description),
    description != ""
  ) %>%
  group_by(description) %>%
  summarise(
    unidades = sum(
      quantity,
      na.rm = TRUE
    ),
    .groups = "drop"
  ) %>%
  arrange(desc(unidades)) %>%
  slice_head(n = 15)

p4 <- ggplot(
  productos,
  aes(
    x = reorder(description, unidades),
    y = unidades
  )
) +
  geom_col(fill = "purple") +
  coord_flip() +
  theme_minimal() +
  labs(
    title = "Top 15 productos por unidades",
    x = "Producto",
    y = "Unidades"
  )

print(p4)

ggsave(
  file.path(salida, "04_top_productos.png"),
  p4,
  width = 13,
  height = 8
)

cat("\nGraficos creados en:\n")
cat(salida, "\n")

# ============================================================
# 12. CONEXION MARIADB
# ============================================================

cat("\n============================================================\n")
cat(" CONECTANDO CON MARIADB\n")
cat("============================================================\n")

con <- dbConnect(
  RMariaDB::MariaDB(),
  host = "127.0.0.1",
  port = 3306,
  dbname = "curso_ia",
  user = "curso_ia",
  password = {
    mariadb_password <- Sys.getenv("MARIADB_PASSWORD")

    if (mariadb_password == "") {
        stop("ERROR: debes definir MARIADB_PASSWORD antes de ejecutar este script")
    }

    mariadb_password
  }
)

cat("Conexion MariaDB OK\n")

# ============================================================
# 13. CARGA DE DATOS
# ============================================================

cat("\nCargando datos en MariaDB...\n")

dbWriteTable(
  con,
  "online_retail_ii",
  df,
  overwrite = TRUE,
  row.names = FALSE
)

cat("Carga terminada.\n")

# ============================================================
# 14. VERIFICACION
# ============================================================

resultado <- dbGetQuery(
  con,
  "
  SELECT COUNT(*) AS filas
  FROM online_retail_ii
  "
)

cat("\n============================================================\n")
cat(" VALIDACION FINAL\n")
cat("============================================================\n")

print(resultado)

cat(
  "Filas R:",
  nrow(df),
  "\n"
)

cat(
  "Filas MariaDB:",
  resultado$filas[1],
  "\n"
)

cat(
  "Coincidencia:",
  nrow(df) == resultado$filas[1],
  "\n"
)

dbDisconnect(con)

cat("\n============================================================\n")
cat(" PROCESO FINALIZADO CORRECTAMENTE\n")
cat("============================================================\n")

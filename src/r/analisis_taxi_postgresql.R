#!/usr/bin/env Rscript

# =====================================================================
# ANALISIS VISUAL, ESTADISTICO Y MODELADO DE NYC TAXI DESDE POSTGRESQL
# =====================================================================
# No modifica la base de datos.
#
# Salidas:
#   CSV  -> salidas/taxi/r/csv
#   JSON -> salidas/taxi/r/json
#   PNG  -> salidas/taxi/r/graficos
# =====================================================================

options(stringsAsFactors = FALSE, scipen = 999)

# ---------------------------------------------------------------------
# 01. PAQUETES
# ---------------------------------------------------------------------

required_packages <- c(
  "DBI", "RPostgres", "ggplot2", "data.table", "scales", "jsonlite"
)

missing_packages <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing_packages) > 0) {
  stop(
    "Faltan paquetes R: ", paste(missing_packages, collapse = ", "),
    "\nInstala con: conda install -c conda-forge ",
    "r-dbi r-rpostgres r-ggplot2 r-data.table r-scales r-jsonlite -y"
  )
}

suppressPackageStartupMessages({
  library(DBI)
  library(RPostgres)
  library(ggplot2)
  library(data.table)
  library(scales)
  library(jsonlite)
})

# ---------------------------------------------------------------------
# 02. DIRECTORIOS Y CONFIGURACION
# ---------------------------------------------------------------------

proyecto_dir <- file.path(path.expand("~"), "curso_ia")
salidas_dir <- file.path(proyecto_dir, "salidas", "taxi", "r")

csv_dir <- file.path(salidas_dir, "csv")
json_dir <- file.path(salidas_dir, "json")
graficos_dir <- file.path(salidas_dir, "graficos")

for (directorio in c(csv_dir, json_dir, graficos_dir)) {
  dir.create(directorio, recursive = TRUE, showWarnings = FALSE)
  cat("[OK] Directorio preparado:", normalizePath(directorio, mustWork = FALSE), "\n")
}

schema <- Sys.getenv("PGSCHEMA", "nyc_taxi")
tabla <- Sys.getenv("PGTABLE", "viajes_limpios")
host <- Sys.getenv("PGHOST", "localhost")
port <- as.integer(Sys.getenv("PGPORT", "5432"))
db <- Sys.getenv("PGDATABASE", "curso_ia")
user <- Sys.getenv("PGUSER", "postgres")
password <- Sys.getenv("PGPASSWORD")

if (password == "") {
  stop("ERROR: debes definir PGPASSWORD antes de ejecutar este script")
}

max_rows <- as.integer(Sys.getenv("TAXI_MAX_ROWS_R", "120000"))
seed <- as.integer(Sys.getenv("TAXI_SEED", "42"))
sample_pct <- as.numeric(Sys.getenv("TAXI_SAMPLE_PCT_R", "0.35"))

set.seed(seed)

cat("\n", strrep("=", 70), "\n", sep = "")
cat(" ANALISIS NYC TAXI DESDE POSTGRESQL CON R\n")
cat(strrep("=", 70), "\n", sep = "")
cat("[INFO] Tabla:", paste0(schema, ".", tabla), "\n")
cat("[INFO] Muestra maxima:", format(max_rows, big.mark = "."), "\n")
cat("[INFO] TABLESAMPLE:", sample_pct, "%\n")
cat("[INFO] Semilla:", seed, "\n")

# ---------------------------------------------------------------------
# 03. FUNCIONES AUXILIARES
# ---------------------------------------------------------------------

section <- function(number, title) {
  cat("\n", strrep("=", 70), "\n", sep = "")
  cat(sprintf(" %02d. %s\n", number, title))
  cat(strrep("=", 70), "\n", sep = "")
}

save_csv <- function(data, name) {
  output_file <- file.path(csv_dir, name)
  cat(sprintf("[CSV] Exportando %s (%s filas x %s columnas)...\n",
              name, format(nrow(data), big.mark = "."), ncol(data)))
  fwrite(data, output_file)
  cat("[OK] CSV guardado:", output_file, "\n")
}

save_plot <- function(plot, name, width = 10, height = 6) {
  output_file <- file.path(graficos_dir, name)
  cat("[GRAFICO] Generando:", name, "\n")
  ggsave(output_file, plot = plot, width = width, height = height, dpi = 160)
  cat("[OK] Grafico guardado:", output_file, "\n")
}

safe_auc <- function(y, probability) {
  y <- as.integer(y)
  n_positive <- sum(y == 1)
  n_negative <- sum(y == 0)

  if (n_positive == 0 || n_negative == 0) {
    return(NA_real_)
  }

  ranks <- rank(probability, ties.method = "average")
  (sum(ranks[y == 1]) - n_positive * (n_positive + 1) / 2) /
    (n_positive * n_negative)
}

# ---------------------------------------------------------------------
# 04. CONEXION Y COLUMNAS
# ---------------------------------------------------------------------

section(4, "CONEXION Y DETECCION DE COLUMNAS")
cat("[INFO] Conectando con PostgreSQL...\n")

con <- dbConnect(
  RPostgres::Postgres(),
  host = host,
  port = port,
  dbname = db,
  user = user,
  password = password
)

on.exit({
  if (dbIsValid(con)) {
    dbDisconnect(con)
    cat("[OK] Conexion PostgreSQL cerrada.\n")
  }
}, add = TRUE)

cat("[OK] Conexion establecida.\n")

quote_identifier <- function(value) {
  as.character(dbQuoteIdentifier(con, value))
}

full_table <- paste0(quote_identifier(schema), ".", quote_identifier(tabla))

columnas <- dbGetQuery(
  con,
  paste(
    "SELECT column_name",
    "FROM information_schema.columns",
    "WHERE table_schema = $1 AND table_name = $2",
    "ORDER BY ordinal_position"
  ),
  params = list(schema, tabla)
)$column_name

if (!length(columnas)) {
  stop("No existe la tabla ", schema, ".", tabla, " o no se puede consultar.")
}

cat("[OK] Columnas detectadas:", length(columnas), "\n")

pick_column <- function(...) {
  candidates <- c(...)
  matches <- match(tolower(candidates), tolower(columnas))
  matches <- matches[!is.na(matches)]

  if (!length(matches)) {
    stop("Falta columna. Nombres buscados: ", paste(candidates, collapse = ", "))
  }

  quote_identifier(columnas[matches[1]])
}

pickup <- pick_column("tpep_pickup_datetime", "pickup_datetime")
dropoff <- pick_column("tpep_dropoff_datetime", "dropoff_datetime")
dist <- pick_column("trip_distance")
fare <- pick_column("fare_amount")
tip <- pick_column("tip_amount")
total <- pick_column("total_amount")
pay <- pick_column("payment_type")
pu <- pick_column("PULocationID", "pulocationid", "pu_location_id")
dest <- pick_column("DOLocationID", "dolocationid", "do_location_id")
passengers <- pick_column("passenger_count")
vendor <- pick_column("VendorID", "vendorid", "vendor_id")

valid <- sprintf(
  paste(
    "%s >= TIMESTAMP '2024-01-01'",
    "AND %s < TIMESTAMP '2025-01-01'",
    "AND %s > 0 AND %s <= 100",
    "AND %s > 0 AND %s > 0",
    "AND %s >= 0",
    "AND %s > %s"
  ),
  pickup, pickup, dist, dist, fare, total, tip, dropoff, pickup
)

query_dt <- function(sql, label = "consulta") {
  cat("[SQL] Ejecutando:", label, "...\n")
  started <- Sys.time()
  result <- as.data.table(dbGetQuery(con, sql))
  elapsed <- round(as.numeric(difftime(Sys.time(), started, units = "secs")), 2)
  cat(sprintf("[OK] %s: %s filas en %.2f s.\n", label,
              format(nrow(result), big.mark = "."), elapsed))
  result
}

# ---------------------------------------------------------------------
# 05. AGREGADOS DESCRIPTIVOS
# ---------------------------------------------------------------------

section(5, "AGREGADOS DESCRIPTIVOS")

daily <- query_dt(
  sprintf(
    paste(
      "SELECT %s::date AS fecha, COUNT(*) AS viajes,",
      "AVG(%s) AS importe_medio, AVG(%s) AS propina_media,",
      "AVG(%s) AS distancia_media",
      "FROM %s WHERE %s GROUP BY 1 ORDER BY 1"
    ),
    pickup, total, tip, dist, full_table, valid
  ),
  "serie diaria"
)

daily[, fecha := as.Date(fecha)]
save_csv(daily, "01_serie_diaria_r.csv")

plot_daily <- ggplot(daily, aes(fecha, viajes)) +
  geom_line(color = "#2C7FB8", linewidth = 0.45) +
  geom_smooth(method = "loess", se = FALSE, color = "#D95F0E", span = 0.15) +
  scale_y_continuous(labels = comma) +
  labs(title = "Demanda diaria y tendencia", x = NULL, y = "Viajes") +
  theme_minimal()

save_plot(plot_daily, "01_demanda_diaria.png", 11, 5)

payment <- query_dt(
  sprintf(
    paste(
      "SELECT %s AS tipo_pago, COUNT(*) AS viajes,",
      "AVG(%s) AS importe_medio, AVG(%s) AS propina_media,",
      "AVG(%s) AS distancia_media",
      "FROM %s WHERE %s GROUP BY 1 ORDER BY 1"
    ),
    pay, total, tip, dist, full_table, valid
  ),
  "resumen por pago"
)

save_csv(payment, "02_pago_resumen_r.csv")

plot_payment <- ggplot(payment, aes(factor(tipo_pago), viajes, fill = factor(tipo_pago))) +
  geom_col(show.legend = FALSE) +
  scale_y_continuous(labels = comma) +
  labs(title = "Viajes por tipo de pago", x = "Tipo", y = "Viajes") +
  theme_minimal()

save_plot(plot_payment, "02_tipos_pago.png", 8, 5)

weekday <- query_dt(
  sprintf(
    paste(
      "SELECT EXTRACT(ISODOW FROM %s)::int AS dia, COUNT(*) AS viajes,",
      "AVG(%s) AS importe_medio, AVG(%s) AS distancia_media,",
      "AVG(%s / NULLIF(%s, 0)) AS propina_relativa",
      "FROM %s WHERE %s GROUP BY 1 ORDER BY 1"
    ),
    pickup, total, dist, tip, fare, full_table, valid
  ),
  "resumen por dia semanal"
)

weekday[, nombre := factor(dia, levels = 1:7, labels = c("L", "M", "X", "J", "V", "S", "D"))]
save_csv(weekday, "03_resumen_dia_semana_r.csv")

plot_weekday <- ggplot(weekday, aes(nombre, viajes, fill = nombre)) +
  geom_col(show.legend = FALSE) +
  scale_y_continuous(labels = comma) +
  labs(title = "Viajes por dia de la semana", x = "Dia", y = "Viajes") +
  theme_minimal()

save_plot(plot_weekday, "03_viajes_dia_semana.png", 8, 5)

# ---------------------------------------------------------------------
# 06. ANALISIS POR ZONA
# ---------------------------------------------------------------------

section(6, "ANALISIS POR ZONA")

zone <- query_dt(
  sprintf(
    paste(
      "SELECT %s AS zona_origen, COUNT(*) AS viajes,",
      "AVG(%s) AS importe_medio, AVG(%s) AS distancia_media,",
      "AVG(EXTRACT(EPOCH FROM (%s - %s)) / 60.0) AS duracion_media",
      "FROM %s WHERE %s GROUP BY 1",
      "HAVING COUNT(*) >= 1000 ORDER BY viajes DESC"
    ),
    pu, total, dist, dropoff, pickup, full_table, valid
  ),
  "eficiencia por zona"
)

zone[, velocidad_media := distancia_media / (duracion_media / 60)]
zone[!is.finite(velocidad_media), velocidad_media := NA_real_]
save_csv(zone, "04_eficiencia_zonas_r.csv")

top_zone <- zone[order(-viajes)][1:min(30, .N)]

plot_speed <- ggplot(
  top_zone,
  aes(reorder(factor(zona_origen), velocidad_media), velocidad_media, fill = viajes)
) +
  geom_col() + coord_flip() + scale_fill_viridis_c(labels = comma) +
  labs(title = "Velocidad media en zonas de alta demanda",
       x = "Zona", y = "Velocidad media", fill = "Viajes") +
  theme_minimal()

save_plot(plot_speed, "04_eficiencia_zonas.png", 10, 8)

plot_zone_amount <- ggplot(
  top_zone,
  aes(reorder(factor(zona_origen), importe_medio), importe_medio, fill = viajes)
) +
  geom_col() + coord_flip() + scale_fill_viridis_c(labels = comma) +
  labs(title = "Importe medio en zonas de alta demanda",
       x = "Zona", y = "Importe medio", fill = "Viajes") +
  theme_minimal()

save_plot(plot_zone_amount, "05_importe_zonas.png", 10, 8)

# ---------------------------------------------------------------------
# 07. MUESTRA PARA EDA Y GLM
# ---------------------------------------------------------------------

section(7, "EXTRACCION DE MUESTRA")

select_features <- sprintf(
  paste(
    "%s AS vendor_id, COALESCE(%s, 1) AS passenger_count,",
    "%s AS trip_distance, %s AS payment_type,",
    "%s AS pu_location_id, %s AS do_location_id,",
    "EXTRACT(HOUR FROM %s)::int AS hora,",
    "EXTRACT(ISODOW FROM %s)::int AS dia_semana,",
    "EXTRACT(EPOCH FROM (%s - %s)) / 60.0 AS duracion_min,",
    "%s AS fare_amount, %s AS tip_amount, %s AS total_amount"
  ),
  vendor, passengers, dist, pay, pu, dest, pickup, pickup,
  dropoff, pickup, fare, tip, total
)

sample_sql <- sprintf(
  paste(
    "SELECT %s FROM %s TABLESAMPLE SYSTEM (%s)",
    "REPEATABLE (%d) WHERE %s LIMIT %d"
  ),
  select_features, full_table, format(sample_pct, scientific = FALSE),
  seed, valid, max_rows
)

taxi_sample <- query_dt(sample_sql, "muestra TABLESAMPLE")

if (nrow(taxi_sample) < 5000) {
  cat("[WARN] TABLESAMPLE insuficiente. Ejecutando consulta alternativa...\n")
  fallback_sql <- sprintf(
    "SELECT %s FROM %s WHERE %s LIMIT %d",
    select_features, full_table, valid, max_rows
  )
  taxi_sample <- query_dt(fallback_sql, "muestra alternativa")
}

if (nrow(taxi_sample) < 5000) {
  stop("Muestra insuficiente: ", nrow(taxi_sample), " registros.")
}

cat("[OK] Muestra lista:", format(nrow(taxi_sample), big.mark = "."), "registros.\n")

# Descriptivos numericos de la muestra.
descriptivos <- rbindlist(
  lapply(names(taxi_sample), function(variable) {
    values <- taxi_sample[[variable]]

    if (!is.numeric(values)) {
      return(NULL)
    }

    data.table(
      variable = variable,
      n = sum(!is.na(values)),
      nulos = sum(is.na(values)),
      media = mean(values, na.rm = TRUE),
      desviacion = sd(values, na.rm = TRUE),
      minimo = min(values, na.rm = TRUE),
      p25 = quantile(values, 0.25, na.rm = TRUE),
      mediana = median(values, na.rm = TRUE),
      p75 = quantile(values, 0.75, na.rm = TRUE),
      maximo = max(values, na.rm = TRUE)
    )
  }),
  fill = TRUE
)

save_csv(descriptivos, "05_descriptivos_muestra_r.csv")

# ---------------------------------------------------------------------
# 08. VISUALIZACIONES DE LA MUESTRA
# ---------------------------------------------------------------------

section(8, "VISUALIZACIONES DE LA MUESTRA")

plots <- list(
  list(
    ggplot(taxi_sample[trip_distance <= 30], aes(trip_distance)) +
      geom_histogram(bins = 60, fill = "#2C7FB8", color = "white") +
      labs(title = "Distribucion de distancia", x = "Distancia", y = "Frecuencia") +
      theme_minimal(),
    "06_distribucion_distancia.png", 9, 5
  ),
  list(
    ggplot(taxi_sample[duracion_min <= 120], aes(duracion_min)) +
      geom_density(fill = "#D95F0E", alpha = 0.55) +
      labs(title = "Densidad de duracion", x = "Minutos", y = "Densidad") +
      theme_minimal(),
    "07_densidad_duracion.png", 9, 5
  ),
  list(
    ggplot(taxi_sample[total_amount <= 200], aes(total_amount)) +
      geom_histogram(bins = 70, fill = "#31A354", color = "white") +
      scale_y_log10() +
      labs(title = "Distribucion del importe total", x = "Importe", y = "Frecuencia") +
      theme_minimal(),
    "08_distribucion_importe.png", 9, 5
  ),
  list(
    ggplot(taxi_sample[trip_distance <= 30 & fare_amount <= 200],
           aes(trip_distance, fare_amount)) +
      geom_point(alpha = 0.05, size = 0.35) +
      geom_smooth(method = "loess", se = FALSE, color = "#D95F0E") +
      labs(title = "Distancia frente a tarifa", x = "Distancia", y = "Tarifa") +
      theme_minimal(),
    "09_distancia_tarifa.png", 9, 5
  ),
  list(
    ggplot(taxi_sample[trip_distance <= 30 & duracion_min <= 120],
           aes(trip_distance, duracion_min)) +
      geom_point(alpha = 0.05, size = 0.35) +
      geom_smooth(method = "loess", se = FALSE, color = "#2C7FB8") +
      labs(title = "Distancia frente a duracion", x = "Distancia", y = "Minutos") +
      theme_minimal(),
    "10_distancia_duracion.png", 9, 5
  ),
  list(
    ggplot(taxi_sample[fare_amount <= 100], aes(factor(payment_type), fare_amount)) +
      geom_boxplot(outlier.shape = NA) +
      coord_cartesian(ylim = c(0, 100)) +
      labs(title = "Tarifa por tipo de pago", x = "Tipo", y = "Tarifa") +
      theme_minimal(),
    "11_boxplot_tarifa_pago.png", 9, 5
  )
)

for (plot_item in plots) {
  save_plot(plot_item[[1]], plot_item[[2]], plot_item[[3]], plot_item[[4]])
}

# ---------------------------------------------------------------------
# 09. GLM: PROPINA ALTA
# ---------------------------------------------------------------------

section(9, "MODELO LOGISTICO DE PROPINA ALTA")

model_data <- taxi_sample[
  payment_type == 1 &
    fare_amount > 0 &
    complete.cases(
      trip_distance, fare_amount, passenger_count,
      hora, dia_semana, vendor_id, tip_amount
    )
]

model_data[, propina_alta := as.integer(tip_amount / fare_amount >= 0.20)]
model_data[, `:=`(
  hora = factor(hora),
  dia_semana = factor(dia_semana),
  vendor_id = factor(vendor_id)
)]

if (nrow(model_data) < 5000) {
  stop("Muestra insuficiente para GLM: ", nrow(model_data))
}

if (length(unique(model_data$propina_alta)) < 2) {
  stop("La variable propina_alta solo contiene una clase.")
}

cat("[MODELO] Registros validos:", format(nrow(model_data), big.mark = "."), "\n")

train_index <- sample.int(nrow(model_data), floor(0.8 * nrow(model_data)))
train_data <- model_data[train_index]
test_data <- model_data[-train_index]

cat("[INFO] Train:", nrow(train_data), "\n")
cat("[INFO] Test :", nrow(test_data), "\n")
cat("[MODELO] Entrenando GLM binomial...\n")

model <- glm(
  propina_alta ~ log1p(trip_distance) + log1p(fare_amount) +
    passenger_count + hora + dia_semana + vendor_id,
  data = train_data,
  family = binomial()
)

cat("[OK] GLM entrenado.\n")

probability <- predict(model, newdata = test_data, type = "response")
prediction <- as.integer(probability >= 0.5)

tn <- sum(test_data$propina_alta == 0 & prediction == 0)
fp <- sum(test_data$propina_alta == 0 & prediction == 1)
fn <- sum(test_data$propina_alta == 1 & prediction == 0)
tp <- sum(test_data$propina_alta == 1 & prediction == 1)

precision <- ifelse(tp + fp > 0, tp / (tp + fp), NA_real_)
recall <- ifelse(tp + fn > 0, tp / (tp + fn), NA_real_)
specificity <- ifelse(tn + fp > 0, tn / (tn + fp), NA_real_)
f1 <- ifelse(is.finite(precision + recall) && precision + recall > 0,
             2 * precision * recall / (precision + recall), NA_real_)

metrics <- data.table(
  n = nrow(model_data),
  n_train = nrow(train_data),
  n_test = nrow(test_data),
  prevalencia = mean(model_data$propina_alta),
  accuracy = mean(prediction == test_data$propina_alta),
  balanced_accuracy = mean(c(recall, specificity), na.rm = TRUE),
  precision = precision,
  recall = recall,
  specificity = specificity,
  F1 = f1,
  auc = safe_auc(test_data$propina_alta, probability),
  TP = tp, TN = tn, FP = fp, FN = fn,
  AIC = AIC(model),
  deviance = model$deviance,
  null_deviance = model$null.deviance
)

save_csv(metrics, "06_metricas_glm_propina_r.csv")

confusion <- data.table(
  real = c(0, 0, 1, 1),
  predicho = c(0, 1, 0, 1),
  n = c(tn, fp, fn, tp)
)

save_csv(confusion, "07_matriz_confusion_glm_r.csv")

cat("\n[RESULTADOS GLM]\n")
print(metrics)

# ---------------------------------------------------------------------
# 10. COEFICIENTES Y ODDS RATIOS
# ---------------------------------------------------------------------

section(10, "COEFICIENTES Y ODDS RATIOS")

coefficients <- as.data.table(coef(summary(model)), keep.rownames = "variable")
setnames(coefficients, c("variable", "estimacion", "error_std", "z", "p_valor"))
coefficients[, `:=`(
  odds_ratio = exp(estimacion),
  ic95_inferior = exp(estimacion - 1.96 * error_std),
  ic95_superior = exp(estimacion + 1.96 * error_std)
)]

save_csv(coefficients, "08_coeficientes_odds_ratio_glm_r.csv")

coefficients_plot <- coefficients[
  variable != "(Intercept)" & is.finite(odds_ratio)
][order(-abs(estimacion))][1:min(20, .N)]

plot_odds <- ggplot(
  coefficients_plot,
  aes(reorder(variable, odds_ratio), odds_ratio,
      ymin = ic95_inferior, ymax = ic95_superior,
      color = odds_ratio > 1)
) +
  geom_pointrange() + geom_hline(yintercept = 1, linetype = 2) +
  coord_flip() + scale_y_log10() +
  scale_color_manual(values = c("#2C7FB8", "#D95F0E"), guide = "none") +
  labs(title = "Odds ratios e intervalos de confianza del 95 %",
       x = NULL, y = "Odds ratio") +
  theme_minimal()

save_plot(plot_odds, "12_odds_ratio_ic95.png", 10, 8)

# ---------------------------------------------------------------------
# 11. CALIBRACION, ROC Y DIAGNOSTICOS
# ---------------------------------------------------------------------

section(11, "CALIBRACION, ROC Y DIAGNOSTICOS")

test_data[, probabilidad := probability]
probability_breaks <- unique(quantile(probability, seq(0, 1, 0.1), na.rm = TRUE))

if (length(probability_breaks) >= 2) {
  test_data[, decil_prob := cut(
    probabilidad,
    breaks = probability_breaks,
    include.lowest = TRUE
  )]

  calibration <- test_data[
    !is.na(decil_prob),
    .(real = mean(propina_alta), predicha = mean(probabilidad), n = .N),
    by = decil_prob
  ]

  calibration[, decil := seq_len(.N)]
  save_csv(calibration, "09_calibracion_glm_r.csv")

  calibration_long <- melt(
    calibration,
    id.vars = c("decil_prob", "decil", "n"),
    measure.vars = c("real", "predicha"),
    variable.name = "serie",
    value.name = "proporcion"
  )

  plot_calibration <- ggplot(
    calibration_long,
    aes(decil, proporcion, color = serie)
  ) +
    geom_line(linewidth = 1) + geom_point() +
    scale_color_manual(values = c(real = "#2C7FB8", predicha = "#D95F0E")) +
    labs(title = "Calibracion del GLM", x = "Decil", y = "Proporcion", color = NULL) +
    theme_minimal()

  save_plot(plot_calibration, "13_calibracion_glm.png", 9, 5)
} else {
  warning("No se pudo generar la calibracion: probabilidades insuficientes.")
  calibration <- data.table()
}

roc_data <- rbindlist(
  lapply(seq(0, 1, length.out = 201), function(threshold) {
    data.table(
      umbral = threshold,
      TPR = mean(probability[test_data$propina_alta == 1] >= threshold),
      FPR = mean(probability[test_data$propina_alta == 0] >= threshold)
    )
  })
)

save_csv(roc_data, "10_curva_roc_glm_r.csv")

plot_roc <- ggplot(roc_data, aes(FPR, TPR)) +
  geom_line(color = "#2C7FB8", linewidth = 1) +
  geom_abline(linetype = 2) + coord_equal() +
  labs(title = sprintf("Curva ROC del GLM, AUC %.3f", metrics$auc), x = "FPR", y = "TPR") +
  theme_minimal()

save_plot(plot_roc, "14_curva_roc_glm.png", 7, 6)

diagnostics <- data.table(
  ajustado = fitted(model),
  residuo_deviance = residuals(model, type = "deviance"),
  residuo_pearson = residuals(model, type = "pearson"),
  leverage = hatvalues(model),
  cooks = cooks.distance(model)
)

diagnostic_sample <- diagnostics[sample(.N, min(10000, .N))]
save_csv(diagnostic_sample, "11_diagnosticos_glm_muestra_r.csv")

plot_residuals <- ggplot(diagnostics, aes(ajustado, residuo_deviance)) +
  geom_point(alpha = 0.08, size = 0.4) +
  geom_hline(yintercept = 0, linetype = 2, color = "red") +
  labs(title = "Residuos de deviance del GLM", x = "Probabilidad ajustada", y = "Residuo") +
  theme_minimal()

save_plot(plot_residuals, "15_residuos_glm.png", 9, 5)

plot_probabilities <- ggplot(
  test_data,
  aes(probabilidad, fill = factor(propina_alta))
) +
  geom_density(alpha = 0.45) +
  labs(title = "Probabilidades estimadas por clase real",
       x = "Probabilidad", y = "Densidad", fill = "Clase") +
  theme_minimal()

save_plot(plot_probabilities, "16_probabilidades_glm.png", 9, 5)

# ---------------------------------------------------------------------
# 12. EFECTO ESTIMADO DE LA TARIFA
# ---------------------------------------------------------------------

section(12, "EFECTO ESTIMADO DE LA TARIFA")

mode_level <- function(x) {
  names(sort(table(x), decreasing = TRUE))[1]
}

new_data <- data.table(
  trip_distance = median(train_data$trip_distance),
  fare_amount = seq(
    quantile(train_data$fare_amount, 0.05),
    quantile(train_data$fare_amount, 0.95),
    length.out = 100
  ),
  passenger_count = median(train_data$passenger_count),
  hora = factor(mode_level(train_data$hora), levels = levels(train_data$hora)),
  dia_semana = factor(
    mode_level(train_data$dia_semana),
    levels = levels(train_data$dia_semana)
  ),
  vendor_id = factor(
    mode_level(train_data$vendor_id),
    levels = levels(train_data$vendor_id)
  )
)

new_data[, probabilidad := predict(model, newdata = new_data, type = "response")]
save_csv(new_data, "12_efecto_tarifa_glm_r.csv")

plot_fare_effect <- ggplot(new_data, aes(fare_amount, probabilidad)) +
  geom_line(color = "#D95F0E", linewidth = 1.1) +
  labs(title = "Efecto estimado de la tarifa sobre propina alta",
       x = "Tarifa", y = "Probabilidad estimada") +
  theme_minimal()

save_plot(plot_fare_effect, "17_efecto_tarifa_glm.png", 9, 5)

# ---------------------------------------------------------------------
# 13. RESUMEN JSON Y FINALIZACION
# ---------------------------------------------------------------------

section(13, "RESUMEN JSON Y FINALIZACION")

summary_json <- list(
  origen = list(motor = "PostgreSQL", tabla = paste0(schema, ".", tabla)),
  configuracion = list(max_rows = max_rows, sample_pct = sample_pct, seed = seed),
  datos = list(
    filas_muestra_original = nrow(taxi_sample),
    filas_modelo = nrow(model_data),
    filas_train = nrow(train_data),
    filas_test = nrow(test_data)
  ),
  modelo_propina = as.list(metrics[1])
)

json_file <- file.path(json_dir, "00_resumen_r.json")
write_json(summary_json, json_file, pretty = TRUE, auto_unbox = TRUE, na = "null")
cat("[OK] JSON guardado:", json_file, "\n")

cat("\n", strrep("=", 70), "\n", sep = "")
cat(" ANALISIS R FINALIZADO\n")
cat(strrep("=", 70), "\n", sep = "")
cat("[OK] CSVs     :", normalizePath(csv_dir, mustWork = FALSE), "\n")
cat("[OK] JSON     :", normalizePath(json_dir, mustWork = FALSE), "\n")
cat("[OK] Graficos :", normalizePath(graficos_dir, mustWork = FALSE), "\n")
cat("[FIN] Proceso completado correctamente.\n")

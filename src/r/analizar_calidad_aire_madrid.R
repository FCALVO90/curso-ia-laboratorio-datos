#!/usr/bin/env Rscript

# =============================================================================
# EDA - CALIDAD DEL AIRE DE MADRID
# =============================================================================
#
# Entrada:
#   datos/processed/aire_madrid/calidad_aire_madrid_procesado.csv
#
# Salidas:
#   salidas/aire_madrid/r/csv/
#   salidas/aire_madrid/r/graficos/
#   salidas/aire_madrid/r/json/
#   salidas/aire_madrid/r/logs/
#
# IMPORTANTE:
#   - No se modifica el RAW.
#   - No se modifica el dataset procesado.
#   - Se analiza exactamente el mismo dataset usado por Python.
#   - Los atípicos IQR se estudian, pero NO se eliminan.
#   - Se usa R base para reducir dependencias externas.
# =============================================================================


# =============================================================================
# 1. CONFIGURACIÓN
# =============================================================================

proyecto <- file.path(
  path.expand("~"),
  "curso_ia"
)

entrada <- file.path(
  proyecto,
  "datos",
  "processed",
  "aire_madrid",
  "calidad_aire_madrid_procesado.csv"
)

salida_base <- file.path(
  proyecto,
  "salidas",
  "aire_madrid",
  "r"
)

csv_dir <- file.path(
  salida_base,
  "csv"
)

graficos_dir <- file.path(
  salida_base,
  "graficos"
)

json_dir <- file.path(
  salida_base,
  "json"
)

logs_dir <- file.path(
  salida_base,
  "logs"
)

log_file <- file.path(
  logs_dir,
  "01_analizar_calidad_aire_madrid_r.log"
)


# =============================================================================
# 2. CREACIÓN DE DIRECTORIOS
# =============================================================================

directorios <- c(
  csv_dir,
  graficos_dir,
  json_dir,
  logs_dir
)

for (directorio in directorios) {

  if (!dir.exists(directorio)) {

    dir.create(
      directorio,
      recursive = TRUE,
      showWarnings = FALSE
    )
  }
}


# =============================================================================
# 3. LOGGING
# =============================================================================

if (file.exists(log_file)) {

  file.remove(
    log_file
  )
}


log_msg <- function(...) {

  mensaje <- paste0(...)

  linea <- sprintf(
    "%s | INFO | %s",
    format(
      Sys.time(),
      "%Y-%m-%d %H:%M:%S"
    ),
    mensaje
  )

  cat(
    linea,
    "\n"
  )

  cat(
    linea,
    "\n",
    file = log_file,
    append = TRUE
  )
}


guardar_csv <- function(
    datos,
    nombre
) {

  ruta <- file.path(
    csv_dir,
    nombre
  )

  write.csv(
    datos,
    ruta,
    row.names = FALSE,
    fileEncoding = "UTF-8"
  )

  log_msg(
    "CSV generado: ",
    ruta
  )
}


guardar_png <- function(
    nombre,
    ancho = 1800,
    alto = 1200,
    res = 150
) {

  ruta <- file.path(
    graficos_dir,
    nombre
  )

  png(
    filename = ruta,
    width = ancho,
    height = alto,
    res = res
  )

  return(
    ruta
  )
}


cerrar_png <- function(
    ruta
) {

  dev.off()

  log_msg(
    "Gráfico generado: ",
    ruta
  )
}


# =============================================================================
# 4. INICIO
# =============================================================================

inicio <- Sys.time()

log_msg(
  paste(
    rep("=", 79),
    collapse = ""
  )
)

log_msg(
  "INICIO DEL EDA EN R - CALIDAD DEL AIRE DE MADRID"
)

log_msg(
  paste(
    rep("=", 79),
    collapse = ""
  )
)


# =============================================================================
# 5. COMPROBACIÓN DE ENTRADA
# =============================================================================

if (!file.exists(entrada)) {

  stop(
    paste(
      "No existe el dataset procesado:",
      entrada
    )
  )
}

log_msg(
  "Dataset procesado: ",
  entrada
)


# =============================================================================
# 6. LECTURA
# =============================================================================

datos <- read.csv(
  entrada,
  stringsAsFactors = FALSE,
  check.names = FALSE,
  encoding = "UTF-8"
)

datos$fecha <- as.Date(
  datos$fecha,
  format = "%Y-%m-%d"
)

datos$valor <- as.numeric(
  datos$valor
)

datos$es_atipico_iqr <- tolower(
  as.character(
    datos$es_atipico_iqr
  )
) == "true"


# =============================================================================
# 7. VALIDACIONES INICIALES
# =============================================================================

columnas_esperadas <- c(
  "provincia",
  "municipio",
  "estacion",
  "magnitud",
  "punto_muestreo",
  "anio",
  "mes",
  "dia",
  "fecha",
  "valor",
  "indicador_validez",
  "es_atipico_iqr"
)

if (!identical(
  names(datos),
  columnas_esperadas
)) {

  stop(
    "Las columnas del dataset no coinciden con las esperadas."
  )
}


if (any(is.na(datos$fecha))) {

  stop(
    "Existen fechas no válidas."
  )
}


if (any(is.na(datos$valor))) {

  stop(
    "Existen valores no numéricos."
  )
}


if (!all(
  datos$indicador_validez == "V"
)) {

  stop(
    "Existen observaciones con indicador de validez distinto de V."
  )
}


registros <- nrow(
  datos
)

estaciones_n <- length(
  unique(
    datos$estacion
  )
)

magnitudes_n <- length(
  unique(
    datos$magnitud
  )
)

puntos_n <- length(
  unique(
    datos$punto_muestreo
  )
)

atipicos_n <- sum(
  datos$es_atipico_iqr
)

porcentaje_atipicos <- (
  atipicos_n
  / registros
  * 100
)


log_msg(
  "Registros: ",
  registros
)

log_msg(
  "Estaciones: ",
  estaciones_n
)

log_msg(
  "Magnitudes: ",
  magnitudes_n
)

log_msg(
  "Puntos de muestreo: ",
  puntos_n
)

log_msg(
  "Atípicos IQR conservados: ",
  atipicos_n
)

log_msg(
  "Porcentaje de atípicos: ",
  round(
    porcentaje_atipicos,
    4
  ),
  "%"
)


# =============================================================================
# 8. TABLA 01 - DESCRIPTIVOS POR MAGNITUD
# =============================================================================

magnitudes <- sort(
  unique(
    datos$magnitud
  )
)


descriptivos_lista <- lapply(
  magnitudes,
  function(magnitud_actual) {

    x <- datos[
      datos$magnitud == magnitud_actual,
    ]

    data.frame(
      magnitud = magnitud_actual,

      registros = nrow(
        x
      ),

      estaciones = length(
        unique(
          x$estacion
        )
      ),

      puntos_muestreo = length(
        unique(
          x$punto_muestreo
        )
      ),

      media = mean(
        x$valor
      ),

      desviacion = sd(
        x$valor
      ),

      minimo = min(
        x$valor
      ),

      q1 = as.numeric(
        quantile(
          x$valor,
          0.25
        )
      ),

      mediana = median(
        x$valor
      ),

      q3 = as.numeric(
        quantile(
          x$valor,
          0.75
        )
      ),

      maximo = max(
        x$valor
      ),

      atipicos_iqr = sum(
        x$es_atipico_iqr
      ),

      porcentaje_atipicos = (
        mean(
          x$es_atipico_iqr
        )
        * 100
      )
    )
  }
)


descriptivos <- do.call(
  rbind,
  descriptivos_lista
)


columnas_decimal <- c(
  "media",
  "desviacion",
  "minimo",
  "q1",
  "mediana",
  "q3",
  "maximo",
  "porcentaje_atipicos"
)


descriptivos[
  columnas_decimal
] <- round(
  descriptivos[
    columnas_decimal
  ],
  4
)


guardar_csv(
  descriptivos,
  "01_descriptivos_por_magnitud_r.csv"
)


# =============================================================================
# 9. TABLA 02 - EVOLUCIÓN MENSUAL
# =============================================================================

combinaciones_mensuales <- unique(
  datos[
    c(
      "anio",
      "mes",
      "magnitud"
    )
  ]
)


mensual_lista <- lapply(
  seq_len(
    nrow(
      combinaciones_mensuales
    )
  ),
  function(i) {

    anio_actual <- combinaciones_mensuales$anio[i]
    mes_actual <- combinaciones_mensuales$mes[i]
    magnitud_actual <- combinaciones_mensuales$magnitud[i]

    x <- datos[
      datos$anio == anio_actual &
      datos$mes == mes_actual &
      datos$magnitud == magnitud_actual,
    ]

    data.frame(
      anio = anio_actual,
      mes = mes_actual,
      magnitud = magnitud_actual,
      registros = nrow(
        x
      ),
      estaciones = length(
        unique(
          x$estacion
        )
      ),
      media = mean(
        x$valor
      ),
      mediana = median(
        x$valor
      ),
      minimo = min(
        x$valor
      ),
      maximo = max(
        x$valor
      ),
      atipicos_iqr = sum(
        x$es_atipico_iqr
      )
    )
  }
)


mensual <- do.call(
  rbind,
  mensual_lista
)


mensual <- mensual[
  order(
    mensual$magnitud,
    mensual$anio,
    mensual$mes
  ),
]


mensual[
  c(
    "media",
    "mediana",
    "minimo",
    "maximo"
  )
] <- round(
  mensual[
    c(
      "media",
      "mediana",
      "minimo",
      "maximo"
    )
  ],
  4
)


guardar_csv(
  mensual,
  "02_evolucion_mensual_r.csv"
)


# =============================================================================
# 10. TABLA 03 - RESUMEN POR ESTACIÓN
# =============================================================================

estaciones <- sort(
  unique(
    datos$estacion
  )
)


estaciones_lista <- lapply(
  estaciones,
  function(estacion_actual) {

    x <- datos[
      datos$estacion == estacion_actual,
    ]

    data.frame(
      estacion = estacion_actual,

      registros = nrow(
        x
      ),

      magnitudes = length(
        unique(
          x$magnitud
        )
      ),

      puntos_muestreo = length(
        unique(
          x$punto_muestreo
        )
      ),

      primera_fecha = min(
        x$fecha
      ),

      ultima_fecha = max(
        x$fecha
      ),

      atipicos_iqr = sum(
        x$es_atipico_iqr
      ),

      porcentaje_atipicos = (
        mean(
          x$es_atipico_iqr
        )
        * 100
      )
    )
  }
)


resumen_estaciones <- do.call(
  rbind,
  estaciones_lista
)


resumen_estaciones$porcentaje_atipicos <- round(
  resumen_estaciones$porcentaje_atipicos,
  4
)


resumen_estaciones <- resumen_estaciones[
  order(
    -resumen_estaciones$registros,
    resumen_estaciones$estacion
  ),
]


guardar_csv(
  resumen_estaciones,
  "03_resumen_estaciones_r.csv"
)


# =============================================================================
# 11. TABLA 04 - ATÍPICOS POR MAGNITUD
# =============================================================================

atipicos_tabla <- data.frame(
  magnitud = descriptivos$magnitud,
  registros = descriptivos$registros,
  atipicos = descriptivos$atipicos_iqr,
  no_atipicos = (
    descriptivos$registros
    - descriptivos$atipicos_iqr
  ),
  porcentaje_atipicos = descriptivos$porcentaje_atipicos
)


guardar_csv(
  atipicos_tabla,
  "04_atipicos_por_magnitud_r.csv"
)


# =============================================================================
# 12. TABLA 05 - RANKING ESTACIÓN / MAGNITUD
# =============================================================================

combinaciones_estacion <- unique(
  datos[
    c(
      "magnitud",
      "estacion"
    )
  ]
)


ranking_lista <- lapply(
  seq_len(
    nrow(
      combinaciones_estacion
    )
  ),
  function(i) {

    magnitud_actual <- combinaciones_estacion$magnitud[i]
    estacion_actual <- combinaciones_estacion$estacion[i]

    x <- datos[
      datos$magnitud == magnitud_actual &
      datos$estacion == estacion_actual,
    ]

    data.frame(
      magnitud = magnitud_actual,
      estacion = estacion_actual,
      registros = nrow(
        x
      ),
      media = mean(
        x$valor
      ),
      mediana = median(
        x$valor
      ),
      maximo = max(
        x$valor
      ),
      atipicos_iqr = sum(
        x$es_atipico_iqr
      )
    )
  }
)


ranking <- do.call(
  rbind,
  ranking_lista
)


ranking$ranking_media_magnitud <- ave(
  -ranking$media,
  ranking$magnitud,
  FUN = function(x) {
    rank(
      x,
      ties.method = "min"
    )
  }
)


ranking$ranking_media_magnitud <- as.integer(
  ranking$ranking_media_magnitud
)


ranking[
  c(
    "media",
    "mediana",
    "maximo"
  )
] <- round(
  ranking[
    c(
      "media",
      "mediana",
      "maximo"
    )
  ],
  4
)


ranking <- ranking[
  order(
    ranking$magnitud,
    ranking$ranking_media_magnitud,
    ranking$estacion
  ),
]


guardar_csv(
  ranking,
  "05_ranking_estaciones_magnitud_r.csv"
)


# =============================================================================
# 13. GRÁFICO 01 - HISTOGRAMAS
# =============================================================================

ruta_png <- guardar_png(
  "01_distribucion_magnitudes_r.png",
  ancho = 1800,
  alto = 1800
)


par(
  mfrow = c(
    4,
    3
  ),
  mar = c(
    4,
    4,
    3,
    1
  ),
  oma = c(
    0,
    0,
    4,
    0
  )
)


for (magnitud_actual in magnitudes) {

  x <- datos$valor[
    datos$magnitud == magnitud_actual
  ]

  hist(
    x,
    breaks = 30,
    col = "#4E79A7",
    border = "white",
    main = paste(
      "Magnitud",
      magnitud_actual
    ),
    xlab = "Valor",
    ylab = "Frecuencia"
  )

  abline(
    v = median(
      x
    ),
    col = "#D62728",
    lwd = 2,
    lty = 2
  )

  legend(
    "topright",
    legend = paste(
      "Mediana:",
      round(
        median(
          x
        ),
        2
      )
    ),
    col = "#D62728",
    lty = 2,
    lwd = 2,
    cex = 0.75,
    bty = "n"
  )
}


mtext(
  "Distribución de valores por magnitud - R",
  outer = TRUE,
  cex = 1.6,
  font = 2
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 14. GRÁFICO 02 - BOXPLOTS
# =============================================================================

ruta_png <- guardar_png(
  "02_boxplot_magnitudes_r.png",
  ancho = 1800,
  alto = 1800
)


par(
  mfrow = c(
    4,
    3
  ),
  mar = c(
    3,
    4,
    3,
    1
  ),
  oma = c(
    0,
    0,
    4,
    0
  )
)


for (magnitud_actual in magnitudes) {

  x <- datos$valor[
    datos$magnitud == magnitud_actual
  ]

  boxplot(
    x,
    col = "#6BAED6",
    border = "#1F4E79",
    main = paste(
      "Magnitud",
      magnitud_actual
    ),
    ylab = "Valor",
    xaxt = "n"
  )
}


mtext(
  "Dispersión por magnitud - R",
  outer = TRUE,
  cex = 1.6,
  font = 2
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 15. GRÁFICO 03 - EVOLUCIÓN MENSUAL NORMALIZADA
# =============================================================================

indice_mensual <- mensual


for (magnitud_actual in magnitudes) {

  posiciones <- which(
    indice_mensual$magnitud == magnitud_actual
  )

  posiciones <- posiciones[
    order(
      indice_mensual$mes[
        posiciones
      ]
    )
  ]

  valor_base <- indice_mensual$mediana[
    posiciones[1]
  ]

  if (valor_base != 0) {

    indice_mensual$indice_base_100[
      posiciones
    ] <- (
      indice_mensual$mediana[
        posiciones
      ]
      / valor_base
      * 100
    )

  } else {

    indice_mensual$indice_base_100[
      posiciones
    ] <- NA
  }
}


ruta_png <- guardar_png(
  "03_evolucion_mensual_r.png",
  ancho = 1800,
  alto = 1000
)


colores <- rainbow(
  length(
    magnitudes
  )
)


limite_y <- range(
  indice_mensual$indice_base_100,
  na.rm = TRUE
)


plot(
  NA,
  xlim = range(
    indice_mensual$mes
  ),
  ylim = limite_y,
  xlab = "Mes de 2024",
  ylab = "Índice base 100",
  main = paste(
    "Evolución mensual de la mediana por magnitud",
    "Índice enero = 100",
    sep = "\n"
  ),
  xaxt = "n"
)


axis(
  1,
  at = sort(
    unique(
      indice_mensual$mes
    )
  )
)


abline(
  h = 100,
  lty = 2,
  col = "grey40"
)


grid(
  col = "grey90"
)


for (i in seq_along(
  magnitudes
)) {

  magnitud_actual <- magnitudes[i]

  x <- indice_mensual[
    indice_mensual$magnitud == magnitud_actual,
  ]

  x <- x[
    order(
      x$mes
    ),
  ]

  lines(
    x$mes,
    x$indice_base_100,
    type = "o",
    pch = 16,
    cex = 0.7,
    lwd = 2,
    col = colores[i]
  )
}


legend(
  "topright",
  legend = paste(
    "Magnitud",
    magnitudes
  ),
  col = colores,
  lty = 1,
  pch = 16,
  cex = 0.8,
  ncol = 2,
  bty = "n"
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 16. GRÁFICO 04 - ATÍPICOS
# =============================================================================

atipicos_ordenados <- atipicos_tabla[
  order(
    atipicos_tabla$porcentaje_atipicos
  ),
]


ruta_png <- guardar_png(
  "04_atipicos_por_magnitud_r.png",
  ancho = 1600,
  alto = 1000
)


par(
  mar = c(
    5,
    6,
    4,
    5
  )
)


posiciones <- barplot(
  atipicos_ordenados$porcentaje_atipicos,
  names.arg = atipicos_ordenados$magnitud,
  horiz = TRUE,
  las = 1,
  col = "#F28E2B",
  border = "#8C4A00",
  xlab = "Porcentaje de registros marcados",
  ylab = "Magnitud",
  main = "Posibles atípicos IQR por magnitud - R",
  xlim = c(
    0,
    max(
      atipicos_ordenados$porcentaje_atipicos
    ) * 1.2
  )
)


text(
  x = atipicos_ordenados$porcentaje_atipicos,
  y = posiciones,
  labels = paste0(
    round(
      atipicos_ordenados$porcentaje_atipicos,
      2
    ),
    "% (",
    atipicos_ordenados$atipicos,
    ")"
  ),
  pos = 4,
  cex = 0.8
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 17. GRÁFICO 05 - SERIES TEMPORALES REPRESENTATIVAS
# =============================================================================

agregado_diario <- aggregate(
  valor ~ fecha + magnitud,
  data = datos,
  FUN = median
)


ruta_png <- guardar_png(
  "05_evolucion_diaria_r.png",
  ancho = 1800,
  alto = 1800
)


par(
  mfrow = c(
    4,
    3
  ),
  mar = c(
    4,
    4,
    3,
    1
  ),
  oma = c(
    0,
    0,
    4,
    0
  )
)


for (magnitud_actual in magnitudes) {

  x <- agregado_diario[
    agregado_diario$magnitud == magnitud_actual,
  ]

  x <- x[
    order(
      x$fecha
    ),
  ]

  plot(
    x$fecha,
    x$valor,
    type = "l",
    col = "#2878B5",
    lwd = 1,
    xlab = "Fecha",
    ylab = "Mediana diaria",
    main = paste(
      "Magnitud",
      magnitud_actual
    )
  )


  media_movil <- stats::filter(
    x$valor,
    rep(
      1 / 14,
      14
    ),
    sides = 1
  )


  lines(
    x$fecha,
    media_movil,
    col = "#D1495B",
    lwd = 2
  )


  legend(
    "topright",
    legend = c(
      "Mediana diaria",
      "Media móvil 14 días"
    ),
    col = c(
      "#2878B5",
      "#D1495B"
    ),
    lty = 1,
    lwd = c(
      1,
      2
    ),
    cex = 0.65,
    bty = "n"
  )
}


mtext(
  "Evolución diaria por magnitud - R",
  outer = TRUE,
  cex = 1.6,
  font = 2
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 18. GRÁFICO 06 - PANEL RESUMEN
# =============================================================================

ruta_png <- guardar_png(
  "06_panel_eda_calidad_aire_r.png",
  ancho = 2000,
  alto = 1400
)


layout(
  matrix(
    c(
      1, 2, 3, 4,
      5, 5, 6, 6,
      7, 7, 7, 8
    ),
    nrow = 3,
    byrow = TRUE
  ),
  heights = c(
    1,
    2.5,
    2.5
  )
)


# KPI 1
par(
  mar = c(
    0,
    0,
    2,
    0
  )
)

plot.new()

text(
  0.5,
  0.65,
  format(
    registros,
    big.mark = ".",
    scientific = FALSE
  ),
  cex = 2,
  font = 2,
  col = "#1F4E79"
)

text(
  0.5,
  0.25,
  "Mediciones válidas",
  cex = 0.9
)


# KPI 2
plot.new()

text(
  0.5,
  0.65,
  estaciones_n,
  cex = 2,
  font = 2,
  col = "#1F4E79"
)

text(
  0.5,
  0.25,
  "Estaciones",
  cex = 0.9
)


# KPI 3
plot.new()

text(
  0.5,
  0.65,
  magnitudes_n,
  cex = 2,
  font = 2,
  col = "#1F4E79"
)

text(
  0.5,
  0.25,
  "Magnitudes",
  cex = 0.9
)


# KPI 4
plot.new()

text(
  0.5,
  0.65,
  paste0(
    round(
      porcentaje_atipicos,
      2
    ),
    "%"
  ),
  cex = 2,
  font = 2,
  col = "#D1495B"
)

text(
  0.5,
  0.25,
  paste(
    "Atípicos IQR:",
    atipicos_n
  ),
  cex = 0.9
)


# Registros por magnitud
par(
  mar = c(
    5,
    5,
    4,
    2
  )
)

barplot(
  descriptivos$registros,
  names.arg = descriptivos$magnitud,
  col = "#4E79A7",
  border = NA,
  xlab = "Magnitud",
  ylab = "Registros",
  main = "Número de mediciones por magnitud"
)


# Atípicos
barplot(
  atipicos_tabla$porcentaje_atipicos,
  names.arg = atipicos_tabla$magnitud,
  col = "#F28E2B",
  border = NA,
  xlab = "Magnitud",
  ylab = "Porcentaje",
  main = "Porcentaje de atípicos por magnitud"
)


# Evolución mensual
plot(
  NA,
  xlim = range(
    indice_mensual$mes
  ),
  ylim = limite_y,
  xlab = "Mes",
  ylab = "Índice",
  main = "Evolución mensual normalizada",
  xaxt = "n"
)

axis(
  1,
  at = sort(
    unique(
      indice_mensual$mes
    )
  )
)

abline(
  h = 100,
  lty = 2,
  col = "grey40"
)


for (i in seq_along(
  magnitudes
)) {

  magnitud_actual <- magnitudes[i]

  x <- indice_mensual[
    indice_mensual$magnitud == magnitud_actual,
  ]

  x <- x[
    order(
      x$mes
    ),
  ]

  lines(
    x$mes,
    x$indice_base_100,
    type = "o",
    pch = 16,
    cex = 0.5,
    col = colores[i]
  )
}


legend(
  "topright",
  legend = magnitudes,
  title = "Magnitud",
  col = colores,
  lty = 1,
  pch = 16,
  ncol = 3,
  cex = 0.6,
  bty = "n"
)


# Top estaciones
top_estaciones <- head(
  resumen_estaciones,
  10
)

top_estaciones <- top_estaciones[
  order(
    top_estaciones$registros
  ),
]


barplot(
  top_estaciones$registros,
  names.arg = top_estaciones$estacion,
  horiz = TRUE,
  las = 1,
  col = "#59A14F",
  border = NA,
  xlab = "Registros",
  ylab = "Estación",
  main = "Top 10 estaciones"
)


cerrar_png(
  ruta_png
)


# =============================================================================
# 19. JSON SIN DEPENDENCIAS EXTERNAS
# =============================================================================

magnitud_mas_atipicos <- atipicos_tabla[
  which.max(
    atipicos_tabla$atipicos
  ),
]


magnitud_mayor_porcentaje <- atipicos_tabla[
  which.max(
    atipicos_tabla$porcentaje_atipicos
  ),
]


json_file <- file.path(
  json_dir,
  "01_resumen_eda_r.json"
)


json_text <- paste0(
  "{\n",
  '  "dataset": {\n',
  '    "fichero": "',
  entrada,
  '",\n',
  '    "registros": ',
  registros,
  ",\n",
  '    "estaciones": ',
  estaciones_n,
  ",\n",
  '    "magnitudes": ',
  magnitudes_n,
  ",\n",
  '    "puntos_muestreo": ',
  puntos_n,
  "\n",
  "  },\n",

  '  "cobertura": {\n',
  '    "fecha_minima": "',
  min(
    datos$fecha
  ),
  '",\n',
  '    "fecha_maxima": "',
  max(
    datos$fecha
  ),
  '"\n',
  "  },\n",

  '  "atipicos_iqr": {\n',
  '    "total": ',
  atipicos_n,
  ",\n",
  '    "porcentaje": ',
  round(
    porcentaje_atipicos,
    4
  ),
  ",\n",
  '    "eliminados": 0,\n',
  '    "magnitud_con_mas_atipicos": ',
  magnitud_mas_atipicos$magnitud,
  ",\n",
  '    "cantidad_maxima": ',
  magnitud_mas_atipicos$atipicos,
  ",\n",
  '    "magnitud_con_mayor_porcentaje": ',
  magnitud_mayor_porcentaje$magnitud,
  ",\n",
  '    "mayor_porcentaje": ',
  magnitud_mayor_porcentaje$porcentaje_atipicos,
  "\n",
  "  },\n",

  '  "salidas": {\n',
  '    "csv_generados": 5,\n',
  '    "graficos_generados": 6\n',
  "  }\n",
  "}\n"
)


writeLines(
  json_text,
  json_file,
  useBytes = TRUE
)


log_msg(
  "JSON generado: ",
  json_file
)


# =============================================================================
# 20. FINAL
# =============================================================================

fin <- Sys.time()

duracion <- as.numeric(
  difftime(
    fin,
    inicio,
    units = "secs"
  )
)


log_msg(
  paste(
    rep("=", 79),
    collapse = ""
  )
)

log_msg(
  "EDA EN R COMPLETADO CORRECTAMENTE"
)

log_msg(
  "Registros analizados: ",
  registros
)

log_msg(
  "Tablas CSV generadas: 5"
)

log_msg(
  "Gráficos PNG generados: 6"
)

log_msg(
  "Atípicos conservados: ",
  atipicos_n
)

log_msg(
  "Duración: ",
  round(
    duracion,
    2
  ),
  " segundos"
)

log_msg(
  paste(
    rep("=", 79),
    collapse = ""
  )
)

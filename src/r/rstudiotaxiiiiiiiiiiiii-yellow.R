#!/usr/bin/env Rscript

# =====================================================================
# VISUALIZADOR GENERAL DE RESULTADOS PARA RSTUDIO
# PROYECTO curso_ia
# =====================================================================
#
# Este script NO consulta ni modifica las bases de datos.
#
# Lee los resultados ya generados en:
#
#   salidas/
#   ├── csvs/
#   ├── json/
#   ├── graficos/
#   └── graficos_r/
#
# Está pensado para trabajar cómodamente desde RStudio:
#
#   - Los CSV quedan cargados como data.frames/data.tables.
#   - Los objetos aparecen en el panel Environment.
#   - Las tablas se pueden abrir con View().
#   - Los JSON quedan cargados como listas R.
#   - Los gráficos PNG pueden mostrarse desde RStudio.
#   - Se identifican métricas, modelos, importancias y coeficientes.
#
# =====================================================================


# =====================================================================
# 01. CONFIGURACIÓN GENERAL
# =====================================================================

options(
  stringsAsFactors = FALSE,
  scipen = 999
)

cat("\n")
cat(strrep("=", 75), "\n")
cat(" VISUALIZADOR GENERAL DE RESULTADOS - RSTUDIO\n")
cat(strrep("=", 75), "\n")


# =====================================================================
# 02. COMPROBACIÓN DE PAQUETES
# =====================================================================

cat("\n[INFO] Comprobando paquetes necesarios...\n")

required_packages <- c(
  "data.table",
  "jsonlite"
)

missing_packages <- required_packages[
  !vapply(
    required_packages,
    requireNamespace,
    logical(1),
    quietly = TRUE
  )
]

if (length(missing_packages) > 0) {
  
  cat("\n[ERROR] Faltan paquetes:\n")
  
  for (package in missing_packages) {
    cat("        -", package, "\n")
  }
  
  stop(
    "\nInstálalos antes de continuar.\n"
  )
}

suppressPackageStartupMessages({
  library(data.table)
  library(jsonlite)
})

cat("[OK] Paquetes disponibles.\n")


# =====================================================================
# 03. LOCALIZACIÓN DEL PROYECTO
# =====================================================================

cat("\n")
cat(strrep("=", 75), "\n")
cat(" 03. LOCALIZACIÓN DEL PROYECTO\n")
cat(strrep("=", 75), "\n")


# Se asume la estructura utilizada durante las prácticas:
#
# ~/curso_ia/

project_dir <- file.path(
  path.expand("~"),
  "curso_ia"
)

salidas_dir <- file.path(
  project_dir,
  "salidas",
  "taxi"
)

python_dir <- file.path(
  salidas_dir,
  "python"
)

r_dir <- file.path(
  salidas_dir,
  "r"
)

csv_dir <- file.path(
  python_dir,
  "csv"
)

json_dir <- file.path(
  python_dir,
  "json"
)

graficos_python_dir <- file.path(
  python_dir,
  "graficos"
)

graficos_r_dir <- file.path(
  r_dir,
  "graficos"
)


cat("[INFO] Proyecto        :", project_dir, "\n")
cat("[INFO] CSV             :", csv_dir, "\n")
cat("[INFO] JSON            :", json_dir, "\n")
cat("[INFO] Gráficos Python :", graficos_python_dir, "\n")
cat("[INFO] Gráficos R      :", graficos_r_dir, "\n")


# =====================================================================
# 04. COMPROBACIÓN DE DIRECTORIOS
# =====================================================================

cat("\n")
cat(strrep("=", 75), "\n")
cat(" 04. COMPROBACIÓN DE DIRECTORIOS\n")
cat(strrep("=", 75), "\n")


directories <- list(
  CSV = csv_dir,
  JSON = json_dir,
  GRAFICOS_PYTHON = graficos_python_dir,
  GRAFICOS_R = graficos_r_dir
)


for (name in names(directories)) {
  
  directory <- directories[[name]]
  
  if (dir.exists(directory)) {
    
    cat(
      sprintf(
        "[OK] %-17s -> %s\n",
        name,
        directory
      )
    )
    
  } else {
    
    cat(
      sprintf(
        "[WARN] %-15s -> NO EXISTE: %s\n",
        name,
        directory
      )
    )
  }
}


# =====================================================================
# 05. FUNCIÓN PARA MOSTRAR CABECERAS
# =====================================================================

section <- function(title) {
  
  cat("\n")
  cat(strrep("=", 75), "\n")
  cat(" ", title, "\n", sep = "")
  cat(strrep("=", 75), "\n")
}


# =====================================================================
# 06. INVENTARIO DE FICHEROS
# =====================================================================

section("06. INVENTARIO DE RESULTADOS")


csv_files <- list.files(
  csv_dir,
  pattern = "\\.csv$",
  full.names = TRUE
)

json_files <- list.files(
  json_dir,
  pattern = "\\.json$",
  full.names = TRUE
)

python_images <- list.files(
  graficos_python_dir,
  pattern = "\\.png$",
  full.names = TRUE
)

r_images <- list.files(
  graficos_r_dir,
  pattern = "\\.png$",
  full.names = TRUE
)


# Ordenamos los resultados para facilitar su revisión.

csv_files <- sort(csv_files)
json_files <- sort(json_files)
python_images <- sort(python_images)
r_images <- sort(r_images)


cat(
  "[INFO] CSV encontrados            :",
  length(csv_files),
  "\n"
)

cat(
  "[INFO] JSON encontrados           :",
  length(json_files),
  "\n"
)

cat(
  "[INFO] Gráficos Python encontrados:",
  length(python_images),
  "\n"
)

cat(
  "[INFO] Gráficos R encontrados     :",
  length(r_images),
  "\n"
)


# =====================================================================
# 07. CARGA DE TODOS LOS CSV
# =====================================================================

section("07. CARGA DE TODOS LOS CSV")


# Todos los CSV se almacenan en esta lista.
#
# En RStudio aparecerá como un objeto dentro de Environment.

dataframes <- list()


for (file in csv_files) {
  
  name <- tools::file_path_sans_ext(
    basename(file)
  )
  
  cat("\n[CSV] Cargando:", basename(file), "\n")
  
  tryCatch({
    
    dataframe <- fread(
      file
    )
    
    dataframes[[name]] <- dataframe
    
    cat(
      "[OK]",
      format(
        nrow(dataframe),
        big.mark = ".",
        decimal.mark = ","
      ),
      "filas x",
      ncol(dataframe),
      "columnas\n"
    )
    
  }, error = function(error) {
    
    cat(
      "[ERROR]",
      basename(file),
      "->",
      conditionMessage(error),
      "\n"
    )
  })
}


cat(
  "\n[OK] DataFrames cargados:",
  length(dataframes),
  "\n"
)


# =====================================================================
# 08. CREACIÓN DE OBJETOS INDIVIDUALES EN RSTUDIO
# =====================================================================

section("08. CREACIÓN DE OBJETOS EN ENVIRONMENT")


# Además de mantener la lista dataframes, creamos cada tabla como
# una variable independiente en el Global Environment.
#
# Ejemplo:
#
#   01_resumen_mensual_python.csv
#
# se convierte en un objeto con un nombre válido para R.


for (name in names(dataframes)) {
  
  safe_name <- make.names(
    name,
    unique = TRUE
  )
  
  assign(
    safe_name,
    dataframes[[name]],
    envir = .GlobalEnv
  )
  
  cat(
    "[OK] Variable creada:",
    safe_name,
    "\n"
  )
}


# =====================================================================
# 09. TABLA RESUMEN DE TODOS LOS CSV
# =====================================================================

section("09. RESUMEN DE TABLAS")


csv_summary <- data.table(
  tabla = character(),
  filas = integer(),
  columnas = integer()
)


for (name in names(dataframes)) {
  
  dataframe <- dataframes[[name]]
  
  csv_summary <- rbind(
    csv_summary,
    data.table(
      tabla = name,
      filas = nrow(dataframe),
      columnas = ncol(dataframe)
    )
  )
}


if (nrow(csv_summary) > 0) {
  
  setorder(
    csv_summary,
    tabla
  )
  
  print(
    csv_summary
  )
  
} else {
  
  cat("[WARN] No hay CSV disponibles.\n")
}


# =====================================================================
# 10. DETECCIÓN DE TABLAS ANALÍTICAS
# =====================================================================

section("10. MÉTRICAS, MODELOS Y TABLAS ANALÍTICAS")


keywords <- c(
  "metrica",
  "modelo",
  "importancia",
  "coeficiente",
  "odds",
  "confusion",
  "calibracion",
  "roc",
  "diagnostico",
  "residuo"
)


important_tables <- list()


for (name in names(dataframes)) {
  
  lower_name <- tolower(name)
  
  is_important <- any(
    vapply(
      keywords,
      function(keyword) {
        grepl(
          keyword,
          lower_name,
          fixed = TRUE
        )
      },
      logical(1)
    )
  )
  
  if (is_important) {
    
    important_tables[[name]] <- dataframes[[name]]
    
    cat("\n")
    cat(strrep("-", 75), "\n")
    cat("[TABLA]", name, "\n")
    cat(strrep("-", 75), "\n")
    
    print(
      head(
        dataframes[[name]],
        20
      )
    )
  }
}


cat(
  "\n[INFO] Tablas analíticas detectadas:",
  length(important_tables),
  "\n"
)


# =====================================================================
# 11. CARGA DE JSON
# =====================================================================

section("11. RESÚMENES JSON")


json_data <- list()


for (file in json_files) {
  
  name <- tools::file_path_sans_ext(
    basename(file)
  )
  
  cat("\n[JSON] Cargando:", basename(file), "\n")
  
  tryCatch({
    
    data <- fromJSON(
      file,
      simplifyVector = TRUE
    )
    
    json_data[[name]] <- data
    
    cat("[OK] JSON cargado.\n")
    
    print(data)
    
  }, error = function(error) {
    
    cat(
      "[ERROR]",
      basename(file),
      "->",
      conditionMessage(error),
      "\n"
    )
  })
}


# =====================================================================
# 12. MÉTRICAS PYTHON
# =====================================================================

section("12. MÉTRICAS DE LOS MODELOS PYTHON")


for (name in names(dataframes)) {
  
  lower_name <- tolower(name)
  
  if (
    grepl("python", lower_name) &&
    grepl("metric", lower_name)
  ) {
    
    cat("\n[MODELO PYTHON]", name, "\n")
    
    print(
      dataframes[[name]]
    )
  }
}


# =====================================================================
# 13. MÉTRICAS R
# =====================================================================

section("13. MÉTRICAS DE LOS MODELOS R")


for (name in names(dataframes)) {
  
  lower_name <- tolower(name)
  
  if (
    grepl("metric", lower_name) &&
    grepl("_r$", lower_name)
  ) {
    
    cat("\n[MODELO R]", name, "\n")
    
    print(
      dataframes[[name]]
    )
  }
}


# =====================================================================
# 14. IMPORTANCIA DE VARIABLES
# =====================================================================

section("14. IMPORTANCIA DE VARIABLES")


for (name in names(dataframes)) {
  
  if (
    grepl(
      "importancia",
      tolower(name)
    )
  ) {
    
    cat(
      "\n[IMPORTANCIA]",
      name,
      "\n"
    )
    
    print(
      head(
        dataframes[[name]],
        20
      )
    )
  }
}


# =====================================================================
# 15. COEFICIENTES Y ODDS RATIOS
# =====================================================================

section("15. COEFICIENTES Y ODDS RATIOS")


for (name in names(dataframes)) {
  
  lower_name <- tolower(name)
  
  if (
    grepl("coeficiente", lower_name) ||
    grepl("odds", lower_name)
  ) {
    
    cat(
      "\n[GLM]",
      name,
      "\n"
    )
    
    print(
      head(
        dataframes[[name]],
        30
      )
    )
  }
}


# =====================================================================
# 16. FUNCIÓN PARA ABRIR UNA IMAGEN
# =====================================================================

show_image <- function(file) {
  
  cat(
    "[GRAFICO] Mostrando:",
    basename(file),
    "\n"
  )
  
  image <- tryCatch(
    png::readPNG(file),
    error = function(error) {
      
      cat(
        "[ERROR] No se pudo abrir:",
        basename(file),
        "\n"
      )
      
      return(NULL)
    }
  )
  
  if (is.null(image)) {
    return(invisible(NULL))
  }
  
  grid::grid.newpage()
  
  grid::grid.raster(
    image
  )
}


# =====================================================================
# 17. COMPROBACIÓN DEL PAQUETE PNG
# =====================================================================

section("17. PREPARACIÓN DEL VISOR DE GRÁFICOS")


png_available <- requireNamespace(
  "png",
  quietly = TRUE
)


if (png_available) {
  
  cat(
    "[OK] Paquete png disponible. ",
    "Se pueden visualizar los PNG desde RStudio.\n",
    sep = ""
  )
  
} else {
  
  cat(
    "[WARN] No está instalado el paquete 'png'.\n"
  )
  
  cat(
    "[WARN] Los nombres de las imágenes se mostrarán, ",
    "pero no se abrirán automáticamente.\n",
    sep = ""
  )
  
  cat(
    "[INFO] Instálalo con:\n"
  )
  
  cat(
    "       conda install -c conda-forge r-png -y\n"
  )
}


# =====================================================================
# 18. GRÁFICOS GENERADOS CON R
# =====================================================================

section("18. GRÁFICOS GENERADOS CON R")


if (length(r_images) == 0) {
  
  cat(
    "[WARN] No hay gráficos R disponibles.\n"
  )
  
} else {
  
  for (index in seq_along(r_images)) {
    
    file <- r_images[index]
    
    cat(
      sprintf(
        "[GRAFICO R] %02d/%02d -> %s\n",
        index,
        length(r_images),
        basename(file)
      )
    )
    
    # Si png está instalado se muestra la imagen
    # directamente en el panel Plots de RStudio.
    
    if (png_available) {
      
      show_image(
        file
      )
    }
  }
}


# =====================================================================
# 19. GRÁFICOS GENERADOS CON PYTHON
# =====================================================================

section("19. GRÁFICOS GENERADOS CON PYTHON")


if (length(python_images) == 0) {
  
  cat(
    "[WARN] No hay gráficos Python disponibles.\n"
  )
  
} else {
  
  for (index in seq_along(python_images)) {
    
    file <- python_images[index]
    
    cat(
      sprintf(
        "[GRAFICO PYTHON] %02d/%02d -> %s\n",
        index,
        length(python_images),
        basename(file)
      )
    )
    
    if (png_available) {
      
      show_image(
        file
      )
    }
  }
}


# =====================================================================
# 20. AYUDA PARA TRABAJAR DESDE RSTUDIO
# =====================================================================

section("20. OBJETOS DISPONIBLES EN RSTUDIO")


cat(
  "
Después de ejecutar este script, revisa el panel Environment.

OBJETOS PRINCIPALES

  dataframes

      Lista que contiene todos los CSV.


  csv_summary

      Inventario de todos los CSV encontrados.


  important_tables

      Métricas, coeficientes, importancias,
      matrices de confusión, calibración, ROC, etc.


  json_data

      Resúmenes JSON de Python y R.


  python_images

      Lista de imágenes generadas con Python.


  r_images

      Lista de imágenes generadas con R.


EJEMPLOS EN LA CONSOLA DE RSTUDIO

  names(dataframes)

  names(json_data)

  csv_summary

  View(csv_summary)

  View(dataframes[[1]])

  names(important_tables)

  View(important_tables[[1]])

"
)


# =====================================================================
# 21. RESUMEN FINAL
# =====================================================================

section("21. VISUALIZACIÓN FINALIZADA")


cat(
  "[OK] CSV cargados      :",
  length(dataframes),
  "\n"
)

cat(
  "[OK] JSON cargados     :",
  length(json_data),
  "\n"
)

cat(
  "[OK] Gráficos Python   :",
  length(python_images),
  "\n"
)

cat(
  "[OK] Gráficos R        :",
  length(r_images),
  "\n"
)

cat(
  "[OK] Tablas analíticas :",
  length(important_tables),
  "\n"
)

cat(
  "\n[FIN] Resultados preparados para su revisión en RStudio.\n"
)
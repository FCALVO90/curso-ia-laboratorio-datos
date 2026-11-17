#!/usr/bin/env Rscript

# ============================================================
# INSPECCION DATASET NYC YELLOW TAXI
# ============================================================
#
# OBJETIVOS:
#
# - Localizar todos los meses disponibles.
# - Inspeccionar los Parquet.
# - Mostrar numero de filas y columnas.
# - Mostrar estructura y tipos.
# - Mostrar muestras del dataset.
# - Analizar valores nulos.
# - Mostrar estadisticas descriptivas.
# - Inspeccionar taxi_zone_lookup.csv.
#
# Proyecto:
# ~/curso_ia
#
# Ejecutar:
# Rscript src/r/inspeccionar_taxi.R
#
# ============================================================


cat("\n")
cat("======================================================================\n")
cat(" INSPECCION DEL DATASET NYC YELLOW TAXI CON R\n")
cat("======================================================================\n")


# ============================================================
# 1. COMPROBAR PAQUETE ARROW
# ============================================================

if (!requireNamespace("arrow", quietly = TRUE)) {

    stop(
        paste(
            "\n[ERROR] No esta instalado el paquete 'arrow'.",
            "\nEs necesario para leer archivos Parquet."
        )
    )
}


# ============================================================
# 2. RUTAS
# ============================================================

HOME <- path.expand("~")

PROYECTO <- file.path(
    HOME,
    "curso_ia"
)

DATA_DIR <- file.path(
    PROYECTO,
    "datos",
    "raw",
    "taxi"
)

LOOKUP <- file.path(
    DATA_DIR,
    "taxi_zone_lookup.csv"
)

cat("\n[INFO] Proyecto :", PROYECTO, "\n")
cat("[INFO] Datos    :", DATA_DIR, "\n")


# ============================================================
# 3. COMPROBAR DIRECTORIO
# ============================================================

if (!dir.exists(DATA_DIR)) {

    stop(
        paste(
            "[ERROR] No existe:",
            DATA_DIR
        )
    )
}

cat("\n[OK] Directorio localizado correctamente.\n")


# ============================================================
# 4. BUSCAR PARQUET
# ============================================================

archivos <- list.files(
    path = DATA_DIR,
    pattern = "^yellow_tripdata_2024-[0-9]{2}\\.parquet$",
    full.names = TRUE
)

archivos <- sort(archivos)


cat("\n")
cat("======================================================================\n")
cat(" FICHEROS PARQUET LOCALIZADOS\n")
cat("======================================================================\n")


if (length(archivos) == 0) {

    stop(
        "[ERROR] No se han encontrado ficheros Parquet."
    )
}


cat(
    "\n[OK] Ficheros encontrados:",
    length(archivos),
    "\n\n"
)


for (archivo in archivos) {

    info <- file.info(archivo)

    tam_mb <- info$size / 1024^2

    cat(
        sprintf(
            "  %-42s %10.2f MB\n",
            basename(archivo),
            tam_mb
        )
    )
}


# ============================================================
# 5. INSPECCION DEL PRIMER PARQUET
# ============================================================

primer_archivo <- archivos[1]


cat("\n")
cat("======================================================================\n")
cat(" INSPECCION DETALLADA DEL PRIMER MES\n")
cat("======================================================================\n")

cat(
    "\n[INFO] Cargando:",
    basename(primer_archivo),
    "\n"
)


datos <- arrow::read_parquet(
    primer_archivo
)

datos <- as.data.frame(datos)


cat("\n[OK] Dataset cargado correctamente.\n")


# ============================================================
# 6. DIMENSIONES
# ============================================================

cat("\n")
cat("---------------- DIMENSIONES ----------------\n")

cat(
    "Filas   :",
    format(
        nrow(datos),
        big.mark = "."
    ),
    "\n"
)

cat(
    "Columnas:",
    ncol(datos),
    "\n"
)


# ============================================================
# 7. COLUMNAS
# ============================================================

cat("\n")
cat("---------------- COLUMNAS ----------------\n\n")

for (i in seq_along(names(datos))) {

    cat(
        sprintf(
            "%02d. %s\n",
            i,
            names(datos)[i]
        )
    )
}


# ============================================================
# 8. ESTRUCTURA
# ============================================================

cat("\n")
cat("---------------- ESTRUCTURA ----------------\n\n")

str(datos)


# ============================================================
# 9. PRIMERAS FILAS
# ============================================================

cat("\n")
cat("---------------- PRIMERAS 10 FILAS ----------------\n\n")

print(
    head(
        datos,
        10
    )
)


# ============================================================
# 10. VALORES NULOS
# ============================================================

cat("\n")
cat("---------------- VALORES NULOS ----------------\n\n")

nulos <- colSums(
    is.na(datos)
)

nulos_encontrados <- nulos[nulos > 0]

if (length(nulos_encontrados) == 0) {

    cat("[OK] No se han encontrado valores NA.\n")

} else {

    print(
        sort(
            nulos_encontrados,
            decreasing = TRUE
        )
    )
}


# ============================================================
# 11. RESUMEN ESTADISTICO
# ============================================================

cat("\n")
cat("---------------- RESUMEN ESTADISTICO ----------------\n\n")

print(
    summary(datos)
)


# ============================================================
# 12. MEMORIA UTILIZADA
# ============================================================

cat("\n")
cat("---------------- MEMORIA ----------------\n\n")

memoria <- object.size(datos)

cat(
    "Tamano aproximado en memoria:",
    format(
        memoria,
        units = "auto"
    ),
    "\n"
)


# ============================================================
# 13. VARIABLES IMPORTANTES
# ============================================================

cat("\n")
cat("======================================================================\n")
cat(" VARIABLES IMPORTANTES PARA LOS EJERCICIOS\n")
cat("======================================================================\n\n")


variables <- c(
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "tip_amount",
    "total_amount"
)


for (variable in variables) {

    if (variable %in% names(datos)) {

        cat(
            "[OK] ",
            variable,
            "\n",
            sep = ""
        )

    } else {

        cat(
            "[NO ENCONTRADA] ",
            variable,
            "\n",
            sep = ""
        )
    }
}


# ============================================================
# 14. COMPROBAR TODOS LOS MESES
# ============================================================

cat("\n")
cat("======================================================================\n")
cat(" COMPROBACION DE TODOS LOS MESES\n")
cat("======================================================================\n\n")


resumen <- data.frame(
    archivo = character(),
    filas = numeric(),
    columnas = numeric(),
    tamano_mb = numeric(),
    stringsAsFactors = FALSE
)


for (archivo in archivos) {

    cat(
        "[INFO] Inspeccionando:",
        basename(archivo),
        "\n"
    )

    # Leer mediante Arrow.
    # Procesamos cada mes por separado y liberamos memoria despues.

    mes <- arrow::read_parquet(
        archivo
    )

    filas <- nrow(mes)

    columnas <- ncol(mes)

    tamano_mb <- file.info(archivo)$size / 1024^2


    resumen <- rbind(
        resumen,
        data.frame(
            archivo = basename(archivo),
            filas = filas,
            columnas = columnas,
            tamano_mb = round(tamano_mb, 2)
        )
    )


    cat(
        "       Filas   :",
        format(
            filas,
            big.mark = "."
        ),
        "\n"
    )

    cat(
        "       Columnas:",
        columnas,
        "\n"
    )

    cat(
        sprintf(
            "       Tamano   : %.2f MB\n",
            tamano_mb
        )
    )


    # Liberamos el objeto antes del siguiente mes.

    rm(mes)

    gc(verbose = FALSE)
}


# ============================================================
# 15. MOSTRAR RESUMEN
# ============================================================

cat("\n")
cat("======================================================================\n")
cat(" RESUMEN DE LOS DATASETS\n")
cat("======================================================================\n\n")

print(
    resumen,
    row.names = FALSE
)


cat("\nTotal registros encontrados: ")

cat(
    format(
        sum(resumen$filas),
        big.mark = "."
    )
)

cat("\n")


# ============================================================
# 16. TAXI ZONE LOOKUP
# ============================================================

cat("\n")
cat("======================================================================\n")
cat(" TAXI ZONE LOOKUP\n")
cat("======================================================================\n")


if (file.exists(LOOKUP)) {

    zonas <- read.csv(
        LOOKUP,
        stringsAsFactors = FALSE
    )

    cat("\n[OK] Lookup encontrado.\n")

    cat(
        "Filas   :",
        nrow(zonas),
        "\n"
    )

    cat(
        "Columnas:",
        ncol(zonas),
        "\n"
    )

    cat("\nNombres de columnas:\n")

    print(
        names(zonas)
    )

    cat("\nPrimeras 10 zonas:\n\n")

    print(
        head(
            zonas,
            10
        ),
        row.names = FALSE
    )

} else {

    cat(
        "\n[AVISO] No se ha encontrado taxi_zone_lookup.csv\n"
    )
}


# ============================================================
# 17. GUARDAR RESUMEN
# ============================================================

OUTPUT_DIR <- file.path(
    PROYECTO,
    "salidas",
    "taxi",
    "r",
    "csv"
)

dir.create(
    OUTPUT_DIR,
    recursive = TRUE,
    showWarnings = FALSE
)

salida <- file.path(
    OUTPUT_DIR,
    "resumen_datasets_taxi_R.csv"
)

write.csv(
    resumen,
    salida,
    row.names = FALSE
)


cat("\n")
cat("======================================================================\n")
cat(" INSPECCION R FINALIZADA\n")
cat("======================================================================\n")

cat(
    "\n[OK] Resumen guardado en:\n",
    salida,
    "\n",
    sep = ""
)

cat("\nYa tenemos el dataset preparado para construir R1-R8.\n")

cat(
    "======================================================================\n\n"
)

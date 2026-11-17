#!/usr/bin/env bash
#  conda activate base
# =====================================================================
# EJECUCIÓN COMPLETA DE LA PRÁCTICA NYC TAXI
# =====================================================================
#
# Ejecuta secuencialmente:
#
#   1. Inspección Python
#   2. Inspección R
#   3. Carga completa en BBDD
#   4. Ejercicios Python
#   5. Ejercicios R
#   6. Análisis + modelos Python
#   7. Análisis + modelos R
#
# Los logs se almacenan en:
#
#   salidas/taxi/python/logs/
#   salidas/taxi/r/logs/
#   salidas/taxi/bbdd/logs/
#
# =====================================================================

set -euo pipefail
EJECUTAR_CARGA=false

if [[ "${1:-}" == "--con-carga" ]]; then
    EJECUTAR_CARGA=true
fi

# =====================================================================
# 01. DIRECTORIO DEL PROYECTO
# =====================================================================

BASE="$HOME/curso_ia"

cd "$BASE"

echo
echo "======================================================================"
echo " EJECUCIÓN COMPLETA NYC TAXI"
echo "======================================================================"
echo
echo "[INFO] Proyecto: $BASE"


# =====================================================================
# 02. DIRECTORIOS DE SALIDA
# =====================================================================

mkdir -p \
    "$BASE/salidas/taxi/python/csv" \
    "$BASE/salidas/taxi/python/graficos" \
    "$BASE/salidas/taxi/python/html" \
    "$BASE/salidas/taxi/python/json" \
    "$BASE/salidas/taxi/python/logs" \
    "$BASE/salidas/taxi/r/csv" \
    "$BASE/salidas/taxi/r/graficos" \
    "$BASE/salidas/taxi/r/json" \
    "$BASE/salidas/taxi/r/logs" \
    "$BASE/salidas/taxi/bbdd/logs"

echo "[OK] Directorios de salida preparados."


# =====================================================================
# 03. CONFIGURACIÓN POSTGRESQL
# =====================================================================

export PGHOST="localhost"
export PGPORT="5432"
export PGDATABASE="curso_ia"
export PGUSER="postgres"
: "${PGPASSWORD:?ERROR: debes definir PGPASSWORD antes de ejecutar este script}"

export PGSCHEMA="nyc_taxi"
export PGTABLE="viajes_limpios"

export PG_DSN="postgresql+psycopg2://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"

echo "[OK] Variables PostgreSQL configuradas."


# =====================================================================
# 04. FUNCIÓN AUXILIAR
# =====================================================================

ejecutar() {

    local titulo="$1"
    local log_dir="$2"
    local log="$3"

    shift 3

    echo
    echo "======================================================================"
    echo " $titulo"
    echo "======================================================================"
    echo
    echo "[INFO] Log: $log_dir/$log"
    echo

    "$@" 2>&1 | tee "$log_dir/$log"

    echo
    echo "[OK] $titulo FINALIZADO"
}


# =====================================================================
# 05. INSPECCIÓN PYTHON
# =====================================================================

ejecutar \
    "01. INSPECCIÓN DEL DATASET CON PYTHON" \
    "$BASE/salidas/taxi/python/logs" \
    "01_inspeccionar_taxi_python.log" \
    python src/python/inspeccionar_taxi.py


# =====================================================================
# 06. INSPECCIÓN R
# =====================================================================

ejecutar \
    "02. INSPECCIÓN DEL DATASET CON R" \
    "$BASE/salidas/taxi/r/logs" \
    "02_inspeccionar_taxi_r.log" \
    conda run -n r-arrow --no-capture-output \
    Rscript src/r/inspeccionar_taxi.R


# =====================================================================
# 07. CARGA DE LOS 12 MESES EN LAS BBDD
# =====================================================================

if [[ "$EJECUTAR_CARGA" == true ]]; then

    echo
    echo "======================================================================"
    echo " 03. CARGA COMPLETA NYC TAXI EN BBDD, MES A MES"
    echo "======================================================================"

    for mes in $(seq -w 1 12); do

        echo
        echo "------------------------------------------------------------"
        echo " CARGANDO MES $mes"
        echo "------------------------------------------------------------"

        python src/python/cargar_taxi_bbdd.py \
            --mes "$mes" \
            2>&1 | tee "$BASE/salidas/taxi/bbdd/logs/03_carga_taxi_2024_${mes}.log"

        estado_python=${PIPESTATUS[0]}

        if [[ "$estado_python" -ne 0 ]]; then
            echo
            echo "[ERROR] Falló la carga del mes $mes."
            exit "$estado_python"
        fi

        echo "[OK] Mes $mes cargado correctamente."

        # Pequeña pausa y liberación de cachés del proceso ya terminado.
        sleep 2

    done

    echo
    echo "[OK] Los 12 meses se han procesado por separado."

else

    echo
    echo "======================================================================"
    echo " 03. CARGA COMPLETA NYC TAXI EN BBDD"
    echo "======================================================================"
    echo
    echo "[SKIP] Carga omitida porque las BBDD ya contienen los datos."
    echo "[INFO] Para reconstruirlas usa:"
    echo "       $0 --con-carga"

fi



# =====================================================================
# 08. EJERCICIOS PYTHON
# =====================================================================

ejecutar \
    "04. EJERCICIOS NYC TAXI CON PYTHON" \
    "$BASE/salidas/taxi/python/logs" \
    "04_solucion_ejercicios_python_taxi.log" \
    python src/python/solucion_ejercicios_python_taxi.py \
    --mes 01 \
    --solo P1 P2 P3 P4 P5 P6 P7 P8 \
    --muestra-modelo 100000


# =====================================================================
# 09. EJERCICIOS R
# =====================================================================

ejecutar \
    "05. EJERCICIOS NYC TAXI CON R" \
    "$BASE/salidas/taxi/r/logs" \
    "05_solucion_ejercicios_r_taxi.log" \
    conda run -n r-arrow --no-capture-output \
    Rscript src/r/solucion_ejercicios_r_taxi.R \
    --mes 01 \
    --solo R1,R2,R3,R4,R5,R6,R7,R8 \
    --muestra-modelo 100000


# =====================================================================
# 10. ANÁLISIS, VISUALIZACIÓN Y MODELOS PYTHON
# =====================================================================

ejecutar \
    "06. ANÁLISIS Y MODELOS NYC TAXI CON PYTHON" \
    "$BASE/salidas/taxi/python/logs" \
    "06_analisis_taxi_postgresql_python.log" \
    python src/python/analisis_taxi_postgresql.py


# =====================================================================
# 11. ANÁLISIS, VISUALIZACIÓN Y MODELOS R
# =====================================================================

ejecutar \
    "07. ANÁLISIS Y MODELOS NYC TAXI CON R" \
    "$BASE/salidas/taxi/r/logs" \
    "07_analisis_taxi_postgresql_r.log" \
    conda run -n r-arrow --no-capture-output \
    Rscript src/r/analisis_taxi_postgresql.R


# =====================================================================
# 12. RESUMEN FINAL
# =====================================================================

echo
echo "======================================================================"
echo " NYC TAXI COMPLETADO"
echo "======================================================================"
echo
echo "[OK] Python CSV     : $BASE/salidas/taxi/python/csv"
echo "[OK] Python JSON    : $BASE/salidas/taxi/python/json"
echo "[OK] Python gráficos: $BASE/salidas/taxi/python/graficos"
echo "[OK] Python HTML    : $BASE/salidas/taxi/python/html"
echo "[OK] Python logs    : $BASE/salidas/taxi/python/logs"
echo "[OK] R CSV          : $BASE/salidas/taxi/r/csv"
echo "[OK] R JSON         : $BASE/salidas/taxi/r/json"
echo "[OK] R gráficos     : $BASE/salidas/taxi/r/graficos"
echo "[OK] R logs         : $BASE/salidas/taxi/r/logs"
echo "[OK] BBDD logs      : $BASE/salidas/taxi/bbdd/logs"
echo
echo "[FIN] Pipeline NYC Taxi finalizado correctamente."
echo

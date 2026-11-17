#!/usr/bin/env bash

# ============================================================
# EXPORTACION DE CONSULTAS MARIADB
# PROYECTO      : ~/curso_ia
# BASE DE DATOS : curso_ia
# TABLA         : curso_ia.online_retail_ii
#
# ORIGEN:
# src/queries/sql/mariadb_retail_queries.sql
#
# SALIDAS:
# salidas/retail/queries/mariadb/csv
# salidas/retail/queries/mariadb/txt
#
# CSV -> DELIMITADO POR COMAS
# TXT -> DELIMITADO POR |
# ============================================================

set -Eeuo pipefail

BASE="${HOME}/curso_ia"

SQL_FILE="${BASE}/src/queries/sql/mariadb_retail_queries.sql"

OUTPUT_BASE="${BASE}/salidas/retail/queries/mariadb"
CSV_DIR="${OUTPUT_BASE}/csv"
TXT_DIR="${OUTPUT_BASE}/txt"
LOG_DIR="${OUTPUT_BASE}/logs"

TMP_DIR="$(mktemp -d)"

DB="curso_ia"

# TU ROOT DE MARIADB USA AUTENTICACION LOCAL.
# POR ESO USAMOS sudo mariadb Y NO mariadb -u root -p.
MARIADB=(
    sudo
    mariadb
)

QUERY_NAMES=(
    "muestra_dataset"
    "resumen_general"
    "calidad_datos_nulos"
    "calidad_datos_anomalias"
    "facturacion_por_pais"
    "top_productos_facturacion"
    "top_productos_unidades"
    "top_clientes"
    "facturacion_anual"
    "facturacion_mensual"
    "facturacion_anio_mes"
    "actividad_por_hora"
    "analisis_cancelaciones"
    "cancelaciones_por_pais"
    "devoluciones"
    "ticket_por_factura"
    "ticket_medio"
    "ticket_medio_por_pais"
    "clientes_por_pais"
    "top_productos_por_pais"
    "ranking_paises"
    "evolucion_mensual"
    "crecimiento_mensual"
    "facturacion_acumulada"
    "ranking_clientes"
    "clientes_recurrentes"
    "resumen_hoja_origen"
    "distribucion_precios"
    "top_precios_unitarios"
    "resumen_final_anual"
)

cleanup()
{
    rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

error_handler()
{
    local exit_code=$?
    local line_number=$1

    echo
    echo "============================================================"
    echo " ERROR EN EXPORTACION MARIADB"
    echo "============================================================"
    echo " Linea script   : ${line_number}"
    echo " Codigo salida  : ${exit_code}"
    echo "============================================================"

    exit "${exit_code}"
}

trap 'error_handler ${LINENO}' ERR


# ============================================================
# EXTRAER QUERY DEL SQL
# ============================================================

extract_query()
{
    local query_number="$1"
    local output_file="$2"

    awk -v query_number="${query_number}" '
        $0 ~ "^-- " query_number "\\." {
            capture = 1
            next
        }

        capture && $0 ~ "^-- [0-9][0-9]\\." {
            exit
        }

        capture {
            print
        }
    ' "${SQL_FILE}" \
    | sed \
        -e '/^[[:space:]]*--/d' \
        -e '/^[[:space:]]*$/d' \
        > "${output_file}"

    if [[ ! -s "${output_file}" ]]; then
        echo "ERROR: NO SE HA EXTRAIDO LA QUERY ${query_number}"
        return 1
    fi
}


# ============================================================
# EXPORTAR QUERY
# ============================================================

export_query()
{
    local query_number="$1"
    local query_name="$2"

    local query_file="${TMP_DIR}/query_${query_number}.sql"
    local tsv_file="${TMP_DIR}/query_${query_number}.tsv"

    local csv_file="${CSV_DIR}/${query_number}_${query_name}.csv"
    local txt_file="${TXT_DIR}/${query_number}_${query_name}.txt"

    echo
    echo "------------------------------------------------------------"
    echo "[${query_number}/30] ${query_name}"
    echo "------------------------------------------------------------"

    extract_query "${query_number}" "${query_file}"

    # --------------------------------------------------------
    # MARIADB -> TSV TEMPORAL
    # --batch genera salida tabulada con cabecera.
    # --------------------------------------------------------

    "${MARIADB[@]}" \
        --batch \
        --raw \
        --column-names \
        "${DB}" \
        < "${query_file}" \
        > "${tsv_file}"

    if [[ ! -s "${tsv_file}" ]]; then
        echo "ERROR: RESULTADO VACIO EN QUERY ${query_number}"
        return 1
    fi

    # --------------------------------------------------------
    # TSV -> CSV REAL
    # csv.writer ESCAPA COMAS, COMILLAS, ETC.
    # --------------------------------------------------------

    python3 - "${tsv_file}" "${csv_file}" <<'PY'
import csv
import sys

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "r", encoding="utf-8", newline="") as fin, \
     open(dst, "w", encoding="utf-8", newline="") as fout:

    reader = csv.reader(fin, delimiter="\t")
    writer = csv.writer(
        fout,
        delimiter=",",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n"
    )

    for row in reader:
        writer.writerow(row)
PY

    # --------------------------------------------------------
    # TSV -> TXT DELIMITADO POR |
    # --------------------------------------------------------

    python3 - "${tsv_file}" "${txt_file}" <<'PY'
import csv
import sys

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "r", encoding="utf-8", newline="") as fin, \
     open(dst, "w", encoding="utf-8", newline="") as fout:

    reader = csv.reader(fin, delimiter="\t")
    writer = csv.writer(
        fout,
        delimiter="|",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n"
    )

    for row in reader:
        writer.writerow(row)
PY

    csv_lines="$(wc -l < "${csv_file}")"
    txt_lines="$(wc -l < "${txt_file}")"

    echo "CSV OK : ${csv_file}"
    echo "         ${csv_lines} lineas"

    echo "TXT OK : ${txt_file}"
    echo "         ${txt_lines} lineas"
}


# ============================================================
# VALIDACIONES
# ============================================================

echo
echo "============================================================"
echo " EXPORTACION MARIADB"
echo "============================================================"
echo " Proyecto      : ${BASE}"
echo " Base de datos : ${DB}"
echo " Tabla         : curso_ia.online_retail_ii"
echo " SQL origen    : ${SQL_FILE}"
echo " CSV destino   : ${CSV_DIR}"
echo " TXT destino   : ${TXT_DIR}"
echo "============================================================"
echo

if [[ ! -f "${SQL_FILE}" ]]; then
    echo "ERROR: NO EXISTE:"
    echo "${SQL_FILE}"
    exit 1
fi

if ! command -v mariadb >/dev/null 2>&1; then
    echo "ERROR: NO SE ENCUENTRA EL COMANDO mariadb"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: NO SE ENCUENTRA python3"
    exit 1
fi

sudo -v

mkdir -p "${CSV_DIR}" "${TXT_DIR}" "${LOG_DIR}"

echo "[VALIDACION] CONEXION..."

"${MARIADB[@]}" \
    --batch \
    --skip-column-names \
    "${DB}" \
    -e "SELECT DATABASE(), CURRENT_USER();"

echo "[VALIDACION] TABLA..."

TABLE_EXISTS="$(
    "${MARIADB[@]}" \
        --batch \
        --skip-column-names \
        "${DB}" \
        -e "
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'curso_ia'
              AND TABLE_NAME = 'online_retail_ii';
        "
)"

if [[ "${TABLE_EXISTS}" -ne 1 ]]; then
    echo "ERROR: NO EXISTE curso_ia.online_retail_ii"
    exit 1
fi

TOTAL_ROWS="$(
    "${MARIADB[@]}" \
        --batch \
        --skip-column-names \
        "${DB}" \
        -e "
            SELECT COUNT(*)
            FROM online_retail_ii;
        "
)"

echo "[VALIDACION] TOTAL REGISTROS: ${TOTAL_ROWS}"

TOTAL_BLOCKS="$(
    grep -Ec '^-- [0-9][0-9]\.' "${SQL_FILE}" || true
)"

echo "[VALIDACION] BLOQUES SQL: ${TOTAL_BLOCKS}"

if [[ "${TOTAL_BLOCKS}" -lt 30 ]]; then
    echo "ERROR: SE ESPERABAN 30 BLOQUES."
    exit 1
fi


# ============================================================
# LIMPIEZA DE EXPORTACIONES ANTERIORES
# ============================================================

echo "[LIMPIEZA] BORRANDO CSV/TXT ANTERIORES..."

find "${CSV_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.csv' \
    -delete

find "${TXT_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.txt' \
    -delete


# ============================================================
# EJECUCION
# ============================================================

START_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
START_SECONDS="$(date +%s)"

for index in "${!QUERY_NAMES[@]}"
do
    query_number="$(printf '%02d' "$((index + 1))")"
    query_name="${QUERY_NAMES[$index]}"

    export_query "${query_number}" "${query_name}"
done


# ============================================================
# RESULTADO
# ============================================================

END_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
END_SECONDS="$(date +%s)"

DURATION="$((END_SECONDS - START_SECONDS))"

TOTAL_CSV="$(
    find "${CSV_DIR}" -maxdepth 1 -type f -name '*.csv' | wc -l
)"

TOTAL_TXT="$(
    find "${TXT_DIR}" -maxdepth 1 -type f -name '*.txt' | wc -l
)"

echo
echo "============================================================"
echo " EXPORTACION MARIADB FINALIZADA"
echo "============================================================"
echo " Inicio        : ${START_TIME}"
echo " Fin           : ${END_TIME}"
echo " Duracion      : ${DURATION} segundos"
echo " CSV generados : ${TOTAL_CSV}"
echo " TXT generados : ${TOTAL_TXT}"
echo "============================================================"

if [[ "${TOTAL_CSV}" -ne 30 || "${TOTAL_TXT}" -ne 30 ]]; then
    echo "ERROR: SE ESPERABAN 30 CSV Y 30 TXT"
    exit 1
fi

du -sh "${OUTPUT_BASE}"

echo
echo "PROCESO COMPLETADO CORRECTAMENTE"

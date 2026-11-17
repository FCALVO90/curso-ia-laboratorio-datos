#!/usr/bin/env bash

# ============================================================
# EXPORTACION MONGODB / MONGOSH
#
# PROYECTO       : ~/curso_ia
# BASE DE DATOS  : curso_ia
# COLECCION      : online_retail_ii
#
# MODELO REAL:
# invoice_no
# stockcode
# description
# quantity
# invoice_date
# unit_price
# customer_id
# country
# hoja_origen
# is_cancelled
# total_amount
# year
# month
# day
# hour
# ============================================================

set -Eeuo pipefail

BASE="${HOME}/curso_ia"

JS_FILE="${BASE}/src/queries/javascript/mongodb_retail_queries.js"

OUTPUT_BASE="${BASE}/salidas/retail/queries/mongodb"
CSV_DIR="${OUTPUT_BASE}/csv"
TXT_DIR="${OUTPUT_BASE}/txt"
JSON_DIR="${OUTPUT_BASE}/json"
LOG_DIR="${OUTPUT_BASE}/logs"

TMP_DIR="$(mktemp -d)"

MONGO_URI="${MONGO_URI:-mongodb://localhost:27017/curso_ia}"
DATABASE="curso_ia"
COLLECTION="online_retail_ii"

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
    echo " ERROR EN LA EXPORTACION MONGODB"
    echo "============================================================"
    echo " Linea del script : ${line_number}"
    echo " Codigo de salida : ${exit_code}"
    echo "============================================================"

    exit "${exit_code}"
}

trap 'error_handler ${LINENO}' ERR


# ============================================================
# EXTRAER UNA CONSULTA
# ============================================================

extract_query()
{
    local query_number="$1"
    local output_file="$2"

    awk -v query_number="${query_number}" '
        $0 ~ "^// " query_number "\\." {
            capture = 1
            next
        }

        capture && $0 ~ "^// [0-9][0-9]\\." {
            exit
        }

        capture && $0 ~ "^// FIN MONGODB" {
            exit
        }

        capture {
            print
        }
    ' "${JS_FILE}" \
    | sed \
        -e '/^[[:space:]]*\/\/ ===/d' \
        -e '/^[[:space:]]*$/d' \
        > "${output_file}"

    if [[ ! -s "${output_file}" ]]; then
        echo "ERROR: NO SE HA EXTRAIDO LA QUERY ${query_number}"
        return 1
    fi
}


# ============================================================
# VALIDACIONES
# ============================================================

echo
echo "============================================================"
echo " EXPORTACION MONGODB"
echo "============================================================"
echo " Proyecto       : ${BASE}"
echo " Base de datos  : ${DATABASE}"
echo " Coleccion      : ${COLLECTION}"
echo " JS origen      : ${JS_FILE}"
echo " CSV destino    : ${CSV_DIR}"
echo " TXT destino    : ${TXT_DIR}"
echo " JSON destino   : ${JSON_DIR}"
echo "============================================================"
echo

if [[ ! -f "${JS_FILE}" ]]; then
    echo "ERROR: NO EXISTE EL FICHERO:"
    echo "${JS_FILE}"
    exit 1
fi

if ! command -v mongosh >/dev/null 2>&1; then
    echo "ERROR: NO SE ENCUENTRA mongosh"
    exit 1
fi

mkdir -p "${CSV_DIR}" "${TXT_DIR}" "${JSON_DIR}" "${LOG_DIR}"

echo "[VALIDACION] COMPROBANDO CONEXION..."

MONGO_DATABASE="$(
    mongosh "${MONGO_URI}" \
        --quiet \
        --eval 'print(db.getName());'
)"

echo "[VALIDACION] BASE CONECTADA: ${MONGO_DATABASE}"

TOTAL_ROWS="$(
    mongosh "${MONGO_URI}" \
        --quiet \
        --eval 'print(db.online_retail_ii.countDocuments({}));'
)"

echo "[VALIDACION] TOTAL DOCUMENTOS: ${TOTAL_ROWS}"

COLLECTION_EXISTS="$(
    mongosh "${MONGO_URI}" \
        --quiet \
        --eval '
            print(
                db.getCollectionNames().includes(
                    "online_retail_ii"
                )
            );
        '
)"

if [[ "${COLLECTION_EXISTS}" != "true" ]]; then
    echo "ERROR: NO EXISTE LA COLECCION online_retail_ii"
    exit 1
fi

TOTAL_BLOCKS="$(
    grep -Ec '^// [0-9][0-9]\.' "${JS_FILE}" || true
)"

echo "[VALIDACION] BLOQUES JS DETECTADOS: ${TOTAL_BLOCKS}"

if [[ "${TOTAL_BLOCKS}" -lt 30 ]]; then
    echo "ERROR: SE ESPERABAN 30 BLOQUES JS"
    exit 1
fi


# ============================================================
# COMPROBAR NOMBRES ANTIGUOS
# ============================================================

if grep -Eq \
'stock_code|invoice_year|invoice_month|invoice_day|invoice_hour' \
"${JS_FILE}"
then
    echo
    echo "ERROR: EL JS TODAVIA CONTIENE CAMPOS DE POSTGRESQL."
    echo "REVISA:"
    echo "stock_code, invoice_year, invoice_month,"
    echo "invoice_day o invoice_hour."
    exit 1
fi


# ============================================================
# LIMPIEZA
# ============================================================

echo "[LIMPIEZA] ELIMINANDO EXPORTACIONES ANTERIORES..."

find "${TXT_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.txt' \
    -delete

find "${CSV_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.csv' \
    -delete

find "${JSON_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.json' \
    -delete


# ============================================================
# EJECUTAR LAS 30 CONSULTAS
# ============================================================

START_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
START_SECONDS="$(date +%s)"

for index in "${!QUERY_NAMES[@]}"
do
    query_number="$(printf '%02d' "$((index + 1))")"
    query_name="${QUERY_NAMES[$index]}"

    query_file="${TMP_DIR}/query_${query_number}.js"
    execution_file="${TMP_DIR}/execute_${query_number}.js"

    txt_file="${TXT_DIR}/${query_number}_${query_name}.txt"

    echo
    echo "------------------------------------------------------------"
    echo "[${query_number}/30] ${query_name}"
    echo "------------------------------------------------------------"

    extract_query "${query_number}" "${query_file}"

    {
        echo 'db = db.getSiblingDB("curso_ia");'
        cat "${query_file}"
    } > "${execution_file}"

    mongosh "${MONGO_URI}" \
        --quiet \
        "${execution_file}" \
        > "${txt_file}" \
        2> "${LOG_DIR}/query_${query_number}_error.log"

    if [[ -s "${LOG_DIR}/query_${query_number}_error.log" ]]; then
        echo "ERROR EN QUERY ${query_number}:"
        cat "${LOG_DIR}/query_${query_number}_error.log"
        exit 1
    fi

    if [[ -s "${txt_file}" ]]; then
        txt_lines="$(wc -l < "${txt_file}")"

        echo "TXT OK : ${txt_file}"
        echo "         ${txt_lines} lineas"
    else
        echo "AVISO: LA QUERY ${query_number} NO GENERO SALIDA VISIBLE"
    fi
done


# ============================================================
# EXPORTAR COLECCION COMPLETA
# ============================================================

if command -v mongoexport >/dev/null 2>&1
then
    echo
    echo "[EXPORTACION] COLECCION COMPLETA A CSV..."

    mongoexport \
        --uri="${MONGO_URI}" \
        --collection="${COLLECTION}" \
        --type=csv \
        --fields=invoice_no,stockcode,description,quantity,invoice_date,unit_price,customer_id,country,hoja_origen,is_cancelled,total_amount,year,month,day,hour \
        --out="${CSV_DIR}/online_retail_ii_completo.csv"

    echo
    echo "[EXPORTACION] COLECCION COMPLETA A JSON..."

    mongoexport \
        --uri="${MONGO_URI}" \
        --collection="${COLLECTION}" \
        --jsonFormat=canonical \
        --out="${JSON_DIR}/online_retail_ii_completo.json"

else
    echo
    echo "AVISO: mongoexport NO ESTA INSTALADO."
    echo "LOS 30 TXT SE HAN GENERADO, PERO NO EL CSV/JSON COMPLETO."
fi


# ============================================================
# RESUMEN FINAL
# ============================================================

END_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
END_SECONDS="$(date +%s)"

DURATION="$((END_SECONDS - START_SECONDS))"

TOTAL_TXT="$(
    find "${TXT_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.txt' \
        | wc -l
)"

TOTAL_CSV="$(
    find "${CSV_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.csv' \
        | wc -l
)"

TOTAL_JSON="$(
    find "${JSON_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.json' \
        | wc -l
)"

echo
echo "============================================================"
echo " EXPORTACION MONGODB FINALIZADA"
echo "============================================================"
echo " Inicio         : ${START_TIME}"
echo " Duracion       : ${DURATION} segundos"
echo " TXT generados  : ${TOTAL_TXT}"
echo " CSV generados  : ${TOTAL_CSV}"
echo " JSON generados : ${TOTAL_JSON}"
echo "============================================================"

du -sh "${OUTPUT_BASE}"

echo
echo "PROCESO COMPLETADO"

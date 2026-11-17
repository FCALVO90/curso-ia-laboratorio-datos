#!/usr/bin/env bash

# ============================================================
# EXPORTACION DE CONSULTAS POSTGRESQL
#
# PROYECTO      : ~/curso_ia
# BASE DE DATOS : curso_ia
# SCHEMA        : retail
# TABLA         : retail.online_retail_ii
#
# ORIGEN:
# src/queries/sql/postgresql_retail_queries.sql
#
# SALIDAS:
# salidas/retail/queries/postgresql/csv
# salidas/retail/queries/postgresql/txt
#
# CSV -> DELIMITADO POR COMAS
# TXT -> DELIMITADO POR |
# ============================================================

set -Eeuo pipefail

# ============================================================
# 01. CONFIGURACION GENERAL
# ============================================================

BASE="${HOME}/curso_ia"

SQL_FILE="${BASE}/src/queries/sql/postgresql_retail_queries.sql"

OUTPUT_BASE="${BASE}/salidas/retail/queries/postgresql"
CSV_DIR="${OUTPUT_BASE}/csv"
TXT_DIR="${OUTPUT_BASE}/txt"
LOG_DIR="${OUTPUT_BASE}/logs"

TMP_DIR="$(mktemp -d)"

DB="${PGDATABASE:-curso_ia}"

# ------------------------------------------------------------
# MODO DE CONEXION
#
# En tu instalación solo existe el rol PostgreSQL "postgres"
# y utiliza autenticación peer.
#
# Por eso se ejecuta:
#
# sudo -u postgres psql
#
# Si posteriormente creas el rol PostgreSQL fcqdevadmin,
# puedes cambiar este array por:
#
# PSQL=(psql -U fcqdevadmin)
# ------------------------------------------------------------

PSQL=(
    sudo
    -u
    postgres
    psql
)

# ============================================================
# 02. NOMBRES DE LOS FICHEROS DE SALIDA
# ============================================================

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

# ============================================================
# 03. FUNCION DE LIMPIEZA
# ============================================================

cleanup()
{
    rm -rf "${TMP_DIR}"
}

trap cleanup EXIT

# ============================================================
# 04. FUNCION DE ERROR
# ============================================================

error_handler()
{
    local exit_code=$?
    local line_number=$1

    echo
    echo "============================================================"
    echo " ERROR EN LA EXPORTACION POSTGRESQL"
    echo "============================================================"
    echo " Linea del script : ${line_number}"
    echo " Codigo de salida : ${exit_code}"
    echo "============================================================"
    echo

    exit "${exit_code}"
}

trap 'error_handler ${LINENO}' ERR

# ============================================================
# 05. FUNCION PARA EXTRAER UNA QUERY DEL FICHERO SQL
# ============================================================

extract_query()
{
    local query_number="$1"
    local output_file="$2"

    # --------------------------------------------------------
    # BUSCA EL BLOQUE:
    #
    # -- 01. ...
    #
    # Y TERMINA AL ENCONTRAR:
    #
    # -- 02. ...
    #
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ELIMINA EL ULTIMO PUNTO Y COMA.
    #
    # COPY (SELECT ...;) TO STDOUT NO ADMITE EL PUNTO Y COMA
    # DENTRO DEL PARENTESIS.
    # --------------------------------------------------------

    sed -i -z 's/;[[:space:]]*$//' "${output_file}"

    # --------------------------------------------------------
    # COMPRUEBA QUE SE HAYA EXTRAIDO CONTENIDO
    # --------------------------------------------------------

    if [[ ! -s "${output_file}" ]]; then
        echo
        echo "ERROR: NO SE HA PODIDO EXTRAER LA QUERY ${query_number}."
        echo "REVISA EL FICHERO:"
        echo "${SQL_FILE}"
        echo
        return 1
    fi
}

# ============================================================
# 06. FUNCION DE EXPORTACION
# ============================================================

export_query()
{
    local query_number="$1"
    local query_name="$2"

    local query_file="${TMP_DIR}/query_${query_number}.sql"

    local csv_file="${CSV_DIR}/${query_number}_${query_name}.csv"
    local txt_file="${TXT_DIR}/${query_number}_${query_name}.txt"

    local query

    echo
    echo "------------------------------------------------------------"
    echo "[${query_number}/30] ${query_name}"
    echo "------------------------------------------------------------"

    # --------------------------------------------------------
    # EXTRACCION DE LA QUERY
    # --------------------------------------------------------

    extract_query "${query_number}" "${query_file}"

    query="$(cat "${query_file}")"

    # --------------------------------------------------------
    # EXPORTACION CSV
    #
    # FORMATO:
    # - CSV REAL
    # - CABECERA
    # - DELIMITADOR COMA
    # - CODIFICACION UTF-8
    # --------------------------------------------------------

    "${PSQL[@]}" \
        -X \
        -v ON_ERROR_STOP=1 \
        -d "${DB}" \
        -c "
            COPY
            (
                ${query}
            )
            TO STDOUT
            WITH
            (
                FORMAT CSV,
                HEADER TRUE,
                DELIMITER ',',
                ENCODING 'UTF8'
            );
        " \
        > "${csv_file}"

    # --------------------------------------------------------
    # EXPORTACION TXT
    #
    # FORMATO:
    # - SIN ALINEACION VISUAL
    # - DELIMITADOR |
    # - CABECERA
    # - SIN PIE '(N ROWS)'
    # --------------------------------------------------------

    "${PSQL[@]}" \
        -X \
        -q \
        -v ON_ERROR_STOP=1 \
        -d "${DB}" \
        -A \
        -F "|" \
        -P footer=off \
        -P null="" \
        -c "${query}" \
        > "${txt_file}"

    # --------------------------------------------------------
    # COMPROBACION DE ARCHIVOS
    # --------------------------------------------------------

    if [[ ! -s "${csv_file}" ]]; then
        echo "ERROR: EL CSV ESTA VACIO:"
        echo "${csv_file}"
        return 1
    fi

    if [[ ! -s "${txt_file}" ]]; then
        echo "ERROR: EL TXT ESTA VACIO:"
        echo "${txt_file}"
        return 1
    fi

    local csv_lines
    local txt_lines

    csv_lines="$(wc -l < "${csv_file}")"
    txt_lines="$(wc -l < "${txt_file}")"

    echo "CSV OK : ${csv_file}"
    echo "         ${csv_lines} lineas"

    echo "TXT OK : ${txt_file}"
    echo "         ${txt_lines} lineas"
}

# ============================================================
# 07. VALIDACIONES PREVIAS
# ============================================================

echo
echo "============================================================"
echo " EXPORTACION POSTGRESQL"
echo "============================================================"
echo " Proyecto       : ${BASE}"
echo " Base de datos  : ${DB}"
echo " Schema         : retail"
echo " Tabla          : retail.online_retail_ii"
echo " SQL origen     : ${SQL_FILE}"
echo " CSV destino    : ${CSV_DIR}"
echo " TXT destino    : ${TXT_DIR}"
echo "============================================================"
echo

# ------------------------------------------------------------
# COMPROBAR QUE EXISTE EL FICHERO SQL
# ------------------------------------------------------------

if [[ ! -f "${SQL_FILE}" ]]; then
    echo "ERROR: NO EXISTE EL FICHERO SQL:"
    echo "${SQL_FILE}"
    exit 1
fi

# ------------------------------------------------------------
# COMPROBAR QUE EXISTE PSQl
# ------------------------------------------------------------

if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: NO SE HA ENCONTRADO EL COMANDO psql."
    exit 1
fi

# ------------------------------------------------------------
# VALIDAR CREDENCIALES SUDO
# ------------------------------------------------------------

echo "[VALIDACION] COMPROBANDO ACCESO SUDO..."

sudo -v

# ------------------------------------------------------------
# CREAR DIRECTORIOS DE SALIDA
# ------------------------------------------------------------

mkdir -p "${CSV_DIR}" "${TXT_DIR}" "${LOG_DIR}"

# ------------------------------------------------------------
# COMPROBAR CONEXION CON POSTGRESQL
# ------------------------------------------------------------

echo "[VALIDACION] COMPROBANDO CONEXION CON POSTGRESQL..."

"${PSQL[@]}" \
    -X \
    -v ON_ERROR_STOP=1 \
    -d "${DB}" \
    -Atqc "
        SELECT
            CURRENT_DATABASE(),
            CURRENT_USER;
    "

# ------------------------------------------------------------
# COMPROBAR QUE EXISTE LA TABLA
# ------------------------------------------------------------

echo "[VALIDACION] COMPROBANDO TABLA retail.online_retail_ii..."

TABLE_EXISTS="$(
    "${PSQL[@]}" \
        -X \
        -v ON_ERROR_STOP=1 \
        -d "${DB}" \
        -Atqc "
            SELECT TO_REGCLASS('retail.online_retail_ii');
        "
)"

if [[ "${TABLE_EXISTS}" != "retail.online_retail_ii" ]]; then
    echo
    echo "ERROR: NO EXISTE LA TABLA retail.online_retail_ii."
    exit 1
fi

# ------------------------------------------------------------
# MOSTRAR NUMERO DE REGISTROS
# ------------------------------------------------------------

TOTAL_ROWS="$(
    "${PSQL[@]}" \
        -X \
        -v ON_ERROR_STOP=1 \
        -d "${DB}" \
        -Atqc "
            SELECT COUNT(*)
            FROM retail.online_retail_ii;
        "
)"

echo "[VALIDACION] TOTAL DE REGISTROS: ${TOTAL_ROWS}"

# ------------------------------------------------------------
# COMPROBAR QUE EL FICHERO CONTIENE LOS 30 BLOQUES
# ------------------------------------------------------------

TOTAL_BLOCKS="$(
    grep -Ec '^-- [0-9][0-9]\.' "${SQL_FILE}" || true
)"

echo "[VALIDACION] BLOQUES SQL DETECTADOS: ${TOTAL_BLOCKS}"

if [[ "${TOTAL_BLOCKS}" -lt 30 ]]; then
    echo
    echo "ERROR: EL FICHERO SQL NO CONTIENE LOS 30 BLOQUES."
    echo "BLOQUES ENCONTRADOS: ${TOTAL_BLOCKS}"
    exit 1
fi

# ============================================================
# 08. LIMPIEZA DE EXPORTACIONES ANTERIORES
# ============================================================

echo
echo "[LIMPIEZA] ELIMINANDO EXPORTACIONES ANTERIORES..."

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
# 09. EJECUCION DE LAS 30 EXPORTACIONES
# ============================================================

START_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
START_SECONDS="$(date +%s)"

echo
echo "INICIO: ${START_TIME}"

for index in "${!QUERY_NAMES[@]}"
do
    query_number="$(printf '%02d' "$((index + 1))")"
    query_name="${QUERY_NAMES[$index]}"

    export_query "${query_number}" "${query_name}"
done

# ============================================================
# 10. COMPROBACION FINAL
# ============================================================

END_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
END_SECONDS="$(date +%s)"

DURATION="$((END_SECONDS - START_SECONDS))"

TOTAL_CSV="$(
    find "${CSV_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.csv' \
        | wc -l
)"

TOTAL_TXT="$(
    find "${TXT_DIR}" \
        -maxdepth 1 \
        -type f \
        -name '*.txt' \
        | wc -l
)"

echo
echo "============================================================"
echo " EXPORTACION POSTGRESQL FINALIZADA"
echo "============================================================"
echo " Inicio         : ${START_TIME}"
echo " Fin            : ${END_TIME}"
echo " Duracion       : ${DURATION} segundos"
echo " CSV generados  : ${TOTAL_CSV}"
echo " TXT generados  : ${TOTAL_TXT}"
echo "============================================================"

if [[ "${TOTAL_CSV}" -ne 30 ]]; then
    echo "ADVERTENCIA: SE ESPERABAN 30 CSV."
    exit 1
fi

if [[ "${TOTAL_TXT}" -ne 30 ]]; then
    echo "ADVERTENCIA: SE ESPERABAN 30 TXT."
    exit 1
fi

echo
echo "PRIMEROS FICHEROS CSV:"
find "${CSV_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.csv' \
    -printf '%f\n' \
    | sort \
    | head

echo
echo "PRIMEROS FICHEROS TXT:"
find "${TXT_DIR}" \
    -maxdepth 1 \
    -type f \
    -name '*.txt' \
    -printf '%f\n' \
    | sort \
    | head

echo
echo "TAMANO TOTAL DE LAS EXPORTACIONES:"

du -sh "${OUTPUT_BASE}"

echo
echo "============================================================"
echo " PROCESO COMPLETADO CORRECTAMENTE"
echo "============================================================"

#!/usr/bin/env bash

set -Eeuo pipefail

# =============================================================================
# PRACTICA A3 - CALIDAD DEL DATO Y EDA
# EJECUCION COMPLETA
# =============================================================================

PROYECTO="$HOME/curso_ia"

RAW="$PROYECTO/datos/raw/aire_madrid/calidad_aire_madrid.csv"

PROCESSED="$PROYECTO/datos/processed/aire_madrid/calidad_aire_madrid_procesado.csv"

PYTHON_DIR="$PROYECTO/src/python"
R_DIR="$PROYECTO/src/r"
SQL_DIR="$PROYECTO/src/queries/sql"

SALIDAS_SQL="$PROYECTO/salidas/aire_madrid/queries/postgresql"

CSV_SQL="$SALIDAS_SQL/csv"
TXT_SQL="$SALIDAS_SQL/txt"
LOG_SQL="$SALIDAS_SQL/logs"

LOG_MAESTRO="$LOG_SQL/00_ejecucion_completa_aire_madrid.log"

DB="curso_ia"
SCHEMA="aire_madrid"
TABLA="mediciones_diarias"


# =============================================================================
# FUNCIONES
# =============================================================================

log()
{
    printf '%s | %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "$*"
}


error()
{
    log "[ERROR] $*"
    exit 1
}


ejecutar()
{
    local descripcion="$1"

    shift

    log ""
    log "==============================================================================="
    log "$descripcion"
    log "==============================================================================="
    log ""

    "$@"

    log ""
    log "[OK] $descripcion"
}


# =============================================================================
# PREPARACION
# =============================================================================

cd "$PROYECTO"

mkdir -p \
    "$CSV_SQL" \
    "$TXT_SQL" \
    "$LOG_SQL"

exec > >(tee "$LOG_MAESTRO") 2>&1


log "==============================================================================="
log "PRACTICA A3 - CALIDAD DEL DATO Y EDA"
log "EJECUCION COMPLETA"
log "==============================================================================="
log ""

log "Proyecto: $PROYECTO"
log "Base PostgreSQL: $DB"
log "Esquema PostgreSQL: $SCHEMA"
log ""


# =============================================================================
# 01. PRERREQUISITOS
# =============================================================================

log "[01] Comprobando prerrequisitos..."


[[ -f "$RAW" ]] || \
    error "No existe el RAW: $RAW"


command -v python >/dev/null 2>&1 || \
    error "Python no esta disponible"


command -v Rscript >/dev/null 2>&1 || \
    error "Rscript no esta disponible"


command -v psql >/dev/null 2>&1 || \
    error "psql no esta disponible"


pg_isready >/dev/null 2>&1 || \
    error "PostgreSQL no esta disponible"


psql \
    -d "$DB" \
    -Atqc "SELECT 1" \
    >/dev/null || \
    error "No se puede acceder a la base $DB"


log "[OK] Prerrequisitos superados"


# =============================================================================
# 02. INSPECCION RAW
# =============================================================================

ejecutar \
    "[02] Inspeccion del dataset RAW" \
    python \
    "$PYTHON_DIR/inspeccionar_calidad_aire_madrid.py"


# =============================================================================
# 03. LIMPIEZA
# =============================================================================

ejecutar \
    "[03] Limpieza y transformacion" \
    python \
    "$PYTHON_DIR/limpiar_calidad_aire_madrid.py"


[[ -f "$PROCESSED" ]] || \
    error "No se ha generado el dataset procesado"


# =============================================================================
# 04. VALIDACION
# =============================================================================

ejecutar \
    "[04] Validacion del dataset procesado" \
    python \
    "$PYTHON_DIR/validar_calidad_aire_madrid.py"


# =============================================================================
# 05. EDA PYTHON
# =============================================================================

ejecutar \
    "[05] EDA con Python" \
    python \
    "$PYTHON_DIR/analizar_calidad_aire_madrid.py"


# =============================================================================
# 06. EDA R
# =============================================================================

ejecutar \
    "[06] EDA con R" \
    Rscript \
    "$R_DIR/analizar_calidad_aire_madrid.R"


# =============================================================================
# 07. COMPROBAR ESQUEMA POSTGRESQL
# =============================================================================

log ""
log "[07] Comprobando esquema PostgreSQL..."


EXISTE_SCHEMA="$(
    psql \
        -d "$DB" \
        -Atqc "
            SELECT COUNT(*)
            FROM information_schema.schemata
            WHERE schema_name = '$SCHEMA';
        "
)"


if [[ "$EXISTE_SCHEMA" != "1" ]]
then
    error "No existe el esquema PostgreSQL $SCHEMA"
fi


log "[OK] Existe el esquema $SCHEMA"


# =============================================================================
# 08. CREAR TABLA SI NO EXISTE
# =============================================================================

log ""
log "[08] Preparando tabla PostgreSQL..."


psql \
    -d "$DB" \
    -v ON_ERROR_STOP=1 <<'SQL'

CREATE TABLE IF NOT EXISTS aire_madrid.mediciones_diarias (

    provincia           varchar(2)  NOT NULL,
    municipio           varchar(3)  NOT NULL,
    estacion            integer     NOT NULL,
    magnitud            integer     NOT NULL,
    punto_muestreo      varchar(30) NOT NULL,

    anio                integer     NOT NULL,

    mes                 integer     NOT NULL
                        CHECK (mes BETWEEN 1 AND 12),

    dia                 integer     NOT NULL
                        CHECK (dia BETWEEN 1 AND 31),

    fecha               date        NOT NULL,

    valor               numeric     NOT NULL,

    indicador_validez   char(1)     NOT NULL
                        CHECK (indicador_validez = 'V'),

    es_atipico_iqr      boolean     NOT NULL
);

SQL


log "[OK] Tabla preparada"


# =============================================================================
# 09. RECARGA IDEMPOTENTE
# =============================================================================

log ""
log "[09] Recargando dataset PostgreSQL..."


psql \
    -d "$DB" \
    -v ON_ERROR_STOP=1 \
    -c "TRUNCATE TABLE aire_madrid.mediciones_diarias;"


psql \
    -d "$DB" \
    -v ON_ERROR_STOP=1 \
    -c "\copy aire_madrid.mediciones_diarias FROM '$PROCESSED' WITH (FORMAT csv, HEADER true, DELIMITER ',', ENCODING 'UTF8')"


log "[OK] Carga PostgreSQL completada"


# =============================================================================
# 10. VALIDACION POSTGRESQL
# =============================================================================

log ""
log "[10] Validando carga PostgreSQL..."


REGISTROS="$(
    psql \
        -d "$DB" \
        -Atqc "
            SELECT COUNT(*)
            FROM aire_madrid.mediciones_diarias;
        "
)"


log "Registros PostgreSQL: $REGISTROS"


if [[ "$REGISTROS" != "42273" ]]
then
    error \
        "Se esperaban 42273 registros y PostgreSQL contiene $REGISTROS"
fi


ESTACIONES="$(
    psql \
        -d "$DB" \
        -Atqc "
            SELECT COUNT(DISTINCT estacion)
            FROM aire_madrid.mediciones_diarias;
        "
)"


MAGNITUDES="$(
    psql \
        -d "$DB" \
        -Atqc "
            SELECT COUNT(DISTINCT magnitud)
            FROM aire_madrid.mediciones_diarias;
        "
)"


ATIPICOS="$(
    psql \
        -d "$DB" \
        -Atqc "
            SELECT COUNT(*)
            FROM aire_madrid.mediciones_diarias
            WHERE es_atipico_iqr;
        "
)"


log "Estaciones: $ESTACIONES"
log "Magnitudes: $MAGNITUDES"
log "Atipicos IQR: $ATIPICOS"


# =============================================================================
# 11. SQL ANALITICO
# =============================================================================

ejecutar \
    "[11] Vistas e indices PostgreSQL" \
    psql \
    -d "$DB" \
    -v ON_ERROR_STOP=1 \
    -f "$SQL_DIR/analisis_calidad_aire_madrid_postgresql.sql"


# =============================================================================
# 12. EXPORTACIONES CSV
# =============================================================================

log ""
log "[12] Exportando consultas PostgreSQL a CSV..."


psql -d "$DB" -c \
"\copy (
    SELECT *
    FROM aire_madrid.vw_calidad_datos
) TO '$CSV_SQL/01_calidad_datos.csv'
WITH (FORMAT CSV, HEADER TRUE)"


psql -d "$DB" -c \
"\copy (
    SELECT *
    FROM aire_madrid.vw_resumen_magnitudes
    ORDER BY magnitud
) TO '$CSV_SQL/02_resumen_magnitudes.csv'
WITH (FORMAT CSV, HEADER TRUE)"


psql -d "$DB" -c \
"\copy (
    SELECT *
    FROM aire_madrid.vw_evolucion_mensual
    ORDER BY magnitud, anio, mes
) TO '$CSV_SQL/03_evolucion_mensual.csv'
WITH (FORMAT CSV, HEADER TRUE)"


psql -d "$DB" -c \
"\copy (
    SELECT *
    FROM aire_madrid.vw_atipicos
    ORDER BY porcentaje_atipicos DESC
) TO '$CSV_SQL/04_atipicos.csv'
WITH (FORMAT CSV, HEADER TRUE)"


psql -d "$DB" -c \
"\copy (
    SELECT *
    FROM aire_madrid.vw_ranking_estaciones
    ORDER BY magnitud, ranking_media_magnitud, estacion
) TO '$CSV_SQL/05_ranking_estaciones.csv'
WITH (FORMAT CSV, HEADER TRUE)"


log "[OK] Exportaciones CSV completadas"


# =============================================================================
# 13. EXPORTACIONES TXT
# =============================================================================

log ""
log "[13] Exportando evidencias PostgreSQL a TXT..."


psql \
    -d "$DB" \
    -P pager=off \
    -c "
        SELECT *
        FROM aire_madrid.vw_calidad_datos;
    " \
    > "$TXT_SQL/01_calidad_datos.txt"


psql \
    -d "$DB" \
    -P pager=off \
    -c "
        SELECT *
        FROM aire_madrid.vw_resumen_magnitudes
        ORDER BY magnitud;
    " \
    > "$TXT_SQL/02_resumen_magnitudes.txt"


psql \
    -d "$DB" \
    -P pager=off \
    -c "
        SELECT *
        FROM aire_madrid.vw_atipicos
        ORDER BY porcentaje_atipicos DESC;
    " \
    > "$TXT_SQL/03_atipicos.txt"


psql \
    -d "$DB" \
    -P pager=off \
    -c "
        SELECT
            anio,
            mes,
            MIN(fecha) AS fecha_minima,
            MAX(fecha) AS fecha_maxima,
            COUNT(*) AS mediciones,
            COUNT(DISTINCT fecha) AS dias_con_datos,
            COUNT(DISTINCT estacion) AS estaciones
        FROM aire_madrid.mediciones_diarias
        GROUP BY anio, mes
        ORDER BY anio, mes;
    " \
    > "$TXT_SQL/04_control_temporal.txt"


log "[OK] Exportaciones TXT completadas"


# =============================================================================
# 14. CONTROL FINAL
# =============================================================================

log ""
log "[14] Control final..."


psql \
    -d "$DB" \
    -P pager=off <<'SQL'

SELECT
    COUNT(*) AS registros,
    COUNT(DISTINCT estacion) AS estaciones,
    COUNT(DISTINCT magnitud) AS magnitudes,
    COUNT(DISTINCT punto_muestreo) AS puntos_muestreo,
    MIN(fecha) AS fecha_minima,
    MAX(fecha) AS fecha_maxima,
    COUNT(*) FILTER (
        WHERE es_atipico_iqr
    ) AS atipicos_iqr
FROM aire_madrid.mediciones_diarias;


SELECT
    table_name
FROM information_schema.views
WHERE table_schema = 'aire_madrid'
ORDER BY table_name;

SQL


# =============================================================================
# 15. RESUMEN DE FICHEROS
# =============================================================================

log ""
log "[15] Resumen de artefactos generados..."


printf '\nPython:\n'

find \
    "$PROYECTO/salidas/aire_madrid/python" \
    -type f \
    | sort


printf '\nR:\n'

find \
    "$PROYECTO/salidas/aire_madrid/r" \
    -type f \
    | sort


printf '\nPostgreSQL:\n'

find \
    "$SALIDAS_SQL" \
    -type f \
    | sort


# =============================================================================
# FIN
# =============================================================================

log ""
log "==============================================================================="
log "PRACTICA COMPLETADA CORRECTAMENTE"
log "==============================================================================="
log ""
log "RAW:                  $RAW"
log "PROCESSED:            $PROCESSED"
log "POSTGRESQL:           $SCHEMA.$TABLA"
log "REGISTROS:            $REGISTROS"
log "ESTACIONES:           $ESTACIONES"
log "MAGNITUDES:           $MAGNITUDES"
log "ATIPICOS IQR:         $ATIPICOS"
log "LOG MAESTRO:          $LOG_MAESTRO"
log ""
log "El RAW no se ha sobrescrito."
log "La carga PostgreSQL es idempotente mediante TRUNCATE + COPY."
log "==============================================================================="

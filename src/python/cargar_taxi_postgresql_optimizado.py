#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CARGA OPTIMIZADA DE NYC YELLOW TAXI EN POSTGRESQL
=================================================

Características:

    - Lee cada Parquet por bloques con PyArrow.
    - No carga un mes completo en memoria.
    - No concatena los doce meses.
    - No utiliza multiprocessing.
    - Usa PostgreSQL COPY FROM STDIN.
    - Realiza una transacción independiente por mes.
    - Permite reanudar la carga mes a mes.
    - Elimina la carga anterior del mes antes de reconstruirlo.

Ejemplos:

    Todos los meses:

        python src/python/cargar_taxi_postgresql_optimizado.py \
            --mes todos

    Un mes:

        python src/python/cargar_taxi_postgresql_optimizado.py \
            --mes 02

    Desde marzo hasta diciembre:

        python src/python/cargar_taxi_postgresql_optimizado.py \
            --desde 03 \
            --hasta 12

    Cambiar el tamaño del bloque:

        python src/python/cargar_taxi_postgresql_optimizado.py \
            --mes todos \
            --batch-size 50000
"""

from __future__ import annotations

import argparse
import gc
import io
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import pyarrow.parquet as pq


# =============================================================================
# 1. CONFIGURACIÓN
# =============================================================================

PROYECTO = Path.home() / "curso_ia"

DATA_DIR = (
    PROYECTO
    / "datos"
    / "raw"
    / "taxi"
)

LOOKUP = DATA_DIR / "taxi_zone_lookup.csv"

LOG_DIR = (
    PROYECTO
    / "salidas"
    / "taxi"
    / "bbdd"
    / "logs"
)

POSTGRES_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "curso_ia",
    "user": "postgres",
    "password": "CursoIA_2026",
}

SCHEMA = "nyc_taxi"
TABLA = "viajes_limpios"

BATCH_SIZE_DEFAULT = 100_000


# =============================================================================
# 2. COLUMNAS
# =============================================================================

COLUMNAS_PARQUET = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "Airport_fee",
]

COLUMNAS_POSTGRES = [
    "vendor_id",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "ratecode_id",
    "store_and_fwd_flag",
    "pu_location_id",
    "do_location_id",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
    "duracion_min",
    "velocidad_mph",
    "fecha",
    "hora",
    "dia_semana_num",
    "dia_semana",
    "fin_semana",
    "mes_origen",
    "archivo_origen",
    "borough_origen",
    "zona_origen",
    "zona_servicio_origen",
    "borough_destino",
    "zona_destino",
    "zona_servicio_destino",
]


# =============================================================================
# 3. UTILIDADES
# =============================================================================

def titulo(texto: str) -> None:

    print()
    print("=" * 78)
    print(f" {texto}")
    print("=" * 78)


def memoria_dataframe(df: pd.DataFrame) -> float:

    return (
        df.memory_usage(
            index=True,
            deep=True
        ).sum()
        / 1024
        / 1024
    )


# =============================================================================
# 4. LOOKUP DE ZONAS
# =============================================================================

def cargar_lookup_zonas() -> tuple[pd.DataFrame, pd.DataFrame]:

    titulo("CARGANDO LOOKUP DE ZONAS")

    if not LOOKUP.exists():

        raise FileNotFoundError(
            f"No existe el lookup: {LOOKUP}"
        )

    zonas = pd.read_csv(
        LOOKUP,
        usecols=[
            "LocationID",
            "Borough",
            "Zone",
            "service_zone",
        ],
    )

    zonas["LocationID"] = pd.to_numeric(
        zonas["LocationID"],
        errors="coerce",
    )

    zonas = zonas.dropna(
        subset=[
            "LocationID"
        ]
    )

    zonas["LocationID"] = (
        zonas["LocationID"]
        .astype("int64")
    )

    zonas = zonas.drop_duplicates(
        subset=[
            "LocationID"
        ]
    )

    zonas_origen = zonas.rename(
        columns={
            "LocationID":
                "PULocationID",

            "Borough":
                "borough_origen",

            "Zone":
                "zona_origen",

            "service_zone":
                "zona_servicio_origen",
        }
    )

    zonas_destino = zonas.rename(
        columns={
            "LocationID":
                "DOLocationID",

            "Borough":
                "borough_destino",

            "Zone":
                "zona_destino",

            "service_zone":
                "zona_servicio_destino",
        }
    )

    print(
        f"[OK] Zonas disponibles: {len(zonas):,}"
    )

    return zonas_origen, zonas_destino


# =============================================================================
# 5. TRANSFORMACIÓN Y LIMPIEZA DEL BLOQUE
# =============================================================================

def transformar_bloque(
    datos: pd.DataFrame,
    mes: str,
    archivo: str,
    zonas_origen: pd.DataFrame,
    zonas_destino: pd.DataFrame,
) -> pd.DataFrame:

    inicio_mes = pd.Timestamp(
        f"2024-{mes}-01"
    )

    fin_mes = (
        inicio_mes
        + pd.offsets.MonthBegin(1)
    )

    datos["tpep_pickup_datetime"] = pd.to_datetime(
        datos["tpep_pickup_datetime"],
        errors="coerce",
    )

    datos["tpep_dropoff_datetime"] = pd.to_datetime(
        datos["tpep_dropoff_datetime"],
        errors="coerce",
    )

    datos["duracion_min"] = (
        (
            datos["tpep_dropoff_datetime"]
            -
            datos["tpep_pickup_datetime"]
        )
        .dt
        .total_seconds()
        /
        60.0
    )

    datos["velocidad_mph"] = np.where(
        datos["duracion_min"] > 0,

        datos["trip_distance"]
        /
        (
            datos["duracion_min"]
            /
            60.0
        ),

        np.nan,
    )

    filtro = (
        datos["tpep_pickup_datetime"].ge(
            inicio_mes
        )
        &
        datos["tpep_pickup_datetime"].lt(
            fin_mes
        )
        &
        datos["tpep_dropoff_datetime"].gt(
            datos["tpep_pickup_datetime"]
        )
        &
        datos["duracion_min"].gt(0)
        &
        datos["duracion_min"].lt(1440)
        &
        datos["trip_distance"].gt(0)
        &
        datos["fare_amount"].gt(0)
        &
        datos["total_amount"].gt(0)
        &
        datos["PULocationID"].notna()
        &
        datos["DOLocationID"].notna()
        &
        pd.Series(
            datos["velocidad_mph"]
        ).gt(0)
        &
        pd.Series(
            datos["velocidad_mph"]
        ).le(100)
    )

    viajes = datos.loc[filtro].copy()

    del datos
    gc.collect()

    if viajes.empty:

        return viajes

    viajes["PULocationID"] = pd.to_numeric(
        viajes["PULocationID"],
        errors="coerce",
    )

    viajes["DOLocationID"] = pd.to_numeric(
        viajes["DOLocationID"],
        errors="coerce",
    )

    viajes = viajes.merge(
        zonas_origen,
        on="PULocationID",
        how="left",
        validate="many_to_one",
    )

    viajes = viajes.merge(
        zonas_destino,
        on="DOLocationID",
        how="left",
        validate="many_to_one",
    )

    viajes["fecha"] = (
        viajes["tpep_pickup_datetime"]
        .dt
        .normalize()
    )

    viajes["hora"] = (
        viajes["tpep_pickup_datetime"]
        .dt
        .hour
    )

    viajes["dia_semana_num"] = (
        viajes["tpep_pickup_datetime"]
        .dt
        .day_of_week
    )

    dias = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo",
    }

    viajes["dia_semana"] = (
        viajes["dia_semana_num"]
        .map(dias)
    )

    viajes["fin_semana"] = (
        viajes["dia_semana_num"]
        >= 5
    )

    viajes["mes_origen"] = (
        f"2024-{mes}"
    )

    viajes["archivo_origen"] = archivo

    viajes.rename(
        columns={
            "VendorID":
                "vendor_id",

            "RatecodeID":
                "ratecode_id",

            "PULocationID":
                "pu_location_id",

            "DOLocationID":
                "do_location_id",

            "Airport_fee":
                "airport_fee",
        },
        inplace=True,
    )

    viajes.columns = [
        columna.lower()
        for columna
        in viajes.columns
    ]

    viajes.replace(
        [np.inf, -np.inf],
        np.nan,
        inplace=True,
    )

    columnas_disponibles = set(
        viajes.columns
    )

    columnas_faltantes = [
        columna
        for columna
        in COLUMNAS_POSTGRES
        if columna not in columnas_disponibles
    ]

    if columnas_faltantes:

        raise RuntimeError(
            "Faltan columnas después de transformar: "
            + ", ".join(columnas_faltantes)
        )

    viajes = viajes[
        COLUMNAS_POSTGRES
    ]

    return viajes


# =============================================================================
# 6. COPY A POSTGRESQL
# =============================================================================

def copiar_bloque(
    conexion,
    viajes: pd.DataFrame,
) -> None:

    buffer_csv = io.StringIO()

    viajes.to_csv(
        buffer_csv,
        index=False,
        header=False,
        sep="\t",
        na_rep="\\N",
        lineterminator="\n",
        date_format="%Y-%m-%d %H:%M:%S.%f",
    )

    buffer_csv.seek(0)

    columnas_sql = ", ".join(
        COLUMNAS_POSTGRES
    )

    sentencia_copy = f"""
        COPY {SCHEMA}.{TABLA}
        ({columnas_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            DELIMITER E'\\t',
            NULL '\\N',
            QUOTE '"',
            ESCAPE '"'
        )
    """

    with conexion.cursor() as cursor:

        cursor.copy_expert(
            sentencia_copy,
            buffer_csv,
        )

    buffer_csv.close()


# =============================================================================
# 7. PROCESAR UN MES
# =============================================================================

def procesar_mes(
    archivo: Path,
    batch_size: int,
    zonas_origen: pd.DataFrame,
    zonas_destino: pd.DataFrame,
) -> None:

    mes = archivo.stem[-2:]
    mes_logico = f"2024-{mes}"

    titulo(
        f"PROCESANDO {archivo.name}"
    )

    inicio = time.perf_counter()

    parquet = pq.ParquetFile(
        archivo,
        pre_buffer=False,
    )

    filas_originales = (
        parquet.metadata.num_rows
    )

    print(
        "[INFO] Filas originales: "
        f"{filas_originales:,}"
    )

    print(
        "[INFO] Tamaño del bloque: "
        f"{batch_size:,}"
    )

    conexion = psycopg2.connect(
        **POSTGRES_CONFIG
    )

    total_leidas = 0
    total_limpias = 0
    numero_bloque = 0

    try:

        with conexion.cursor() as cursor:

            cursor.execute(
                f"""
                DELETE
                FROM {SCHEMA}.{TABLA}
                WHERE mes_origen = %s
                """,
                (
                    mes_logico,
                ),
            )

            print(
                "[OK] Filas anteriores eliminadas: "
                f"{cursor.rowcount:,}"
            )

        for record_batch in parquet.iter_batches(
            batch_size=batch_size,
            columns=COLUMNAS_PARQUET,
            use_threads=False,
        ):

            numero_bloque += 1

            datos = record_batch.to_pandas(
                split_blocks=True,
                self_destruct=True,
            )

            filas_bloque = len(datos)
            total_leidas += filas_bloque

            viajes = transformar_bloque(
                datos=datos,
                mes=mes,
                archivo=archivo.name,
                zonas_origen=zonas_origen,
                zonas_destino=zonas_destino,
            )

            filas_limpias = len(viajes)
            total_limpias += filas_limpias

            memoria_mb = memoria_dataframe(
                viajes
            )

            if filas_limpias > 0:

                copiar_bloque(
                    conexion,
                    viajes,
                )

            print(
                f"[BLOQUE {numero_bloque:03d}] "
                f"leidas={filas_bloque:,} | "
                f"limpias={filas_limpias:,} | "
                f"acumuladas={total_limpias:,} | "
                f"memoria_df={memoria_mb:,.1f} MB"
            )

            del viajes
            gc.collect()

        conexion.commit()

    except Exception:

        conexion.rollback()

        print(
            f"[ERROR] Transacción revertida para {mes_logico}"
        )

        raise

    finally:

        conexion.close()

    eliminadas = (
        total_leidas
        -
        total_limpias
    )

    porcentaje = (
        eliminadas
        /
        total_leidas
        *
        100
        if total_leidas
        else 0
    )

    duracion = (
        time.perf_counter()
        -
        inicio
    )

    print()
    print(
        f"[OK] Mes terminado: {mes_logico}"
    )
    print(
        f"[OK] Filas leídas: {total_leidas:,}"
    )
    print(
        f"[OK] Filas limpias: {total_limpias:,}"
    )
    print(
        f"[OK] Filas eliminadas: "
        f"{eliminadas:,} ({porcentaje:.2f}%)"
    )
    print(
        f"[OK] Duración: {duracion:.2f} segundos"
    )


# =============================================================================
# 8. ÍNDICES
# =============================================================================

def eliminar_indices() -> None:

    titulo(
        "ELIMINANDO ÍNDICES TEMPORALMENTE"
    )

    conexion = psycopg2.connect(
        **POSTGRES_CONFIG
    )

    conexion.autocommit = True

    try:

        with conexion.cursor() as cursor:

            for indice in [
                "idx_taxi_fecha",
                "idx_taxi_mes",
                "idx_taxi_origen",
                "idx_taxi_destino",
            ]:

                cursor.execute(
                    f"""
                    DROP INDEX IF EXISTS
                    {SCHEMA}.{indice}
                    """
                )

                print(
                    f"[OK] DROP INDEX: {indice}"
                )

    finally:

        conexion.close()


def crear_indices() -> None:

    titulo(
        "CREANDO ÍNDICES DE POSTGRESQL"
    )

    conexion = psycopg2.connect(
        **POSTGRES_CONFIG
    )

    conexion.autocommit = True

    indices = [
        (
            "idx_taxi_fecha",
            "tpep_pickup_datetime",
        ),
        (
            "idx_taxi_mes",
            "mes_origen",
        ),
        (
            "idx_taxi_origen",
            "pu_location_id",
        ),
        (
            "idx_taxi_destino",
            "do_location_id",
        ),
    ]

    try:

        with conexion.cursor() as cursor:

            for nombre, columna in indices:

                print(
                    f"[INFO] Creando {nombre}..."
                )

                cursor.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS
                    {nombre}
                    ON {SCHEMA}.{TABLA}
                    ({columna})
                    """
                )

                print(
                    f"[OK] Índice creado: {nombre}"
                )

            cursor.execute(
                f"""
                ANALYZE {SCHEMA}.{TABLA}
                """
            )

            print(
                "[OK] ANALYZE completado"
            )

    finally:

        conexion.close()


# =============================================================================
# 9. VALIDACIÓN
# =============================================================================

def validar_postgresql() -> None:

    titulo(
        "VALIDACIÓN FINAL DE POSTGRESQL"
    )

    conexion = psycopg2.connect(
        **POSTGRES_CONFIG
    )

    try:

        with conexion.cursor() as cursor:

            cursor.execute(
                f"""
                SELECT
                    mes_origen,
                    COUNT(*) AS viajes
                FROM {SCHEMA}.{TABLA}
                GROUP BY mes_origen
                ORDER BY mes_origen
                """
            )

            resultados = cursor.fetchall()

            total = 0

            for mes, viajes in resultados:

                total += viajes

                print(
                    f"{mes} : {viajes:,}"
                )

            print()
            print(
                f"[OK] Meses cargados: {len(resultados)}"
            )
            print(
                f"[OK] Viajes totales: {total:,}"
            )

    finally:

        conexion.close()


# =============================================================================
# 10. SELECCIÓN DE ARCHIVOS
# =============================================================================

def seleccionar_archivos(
    mes: str | None,
    desde: str | None,
    hasta: str | None,
) -> list[Path]:

    if mes:

        if mes.lower() == "todos":

            meses = range(
                1,
                13
            )

        else:

            numero = int(mes)

            if numero < 1 or numero > 12:

                raise ValueError(
                    "El mes debe estar entre 01 y 12."
                )

            meses = [
                numero
            ]

    else:

        inicio = int(
            desde or "01"
        )

        fin = int(
            hasta or "12"
        )

        if (
            inicio < 1
            or fin > 12
            or inicio > fin
        ):

            raise ValueError(
                "Rango de meses no válido."
            )

        meses = range(
            inicio,
            fin + 1
        )

    archivos = [
        DATA_DIR
        /
        f"yellow_tripdata_2024-{numero:02d}.parquet"

        for numero
        in meses
    ]

    faltantes = [
        archivo
        for archivo
        in archivos
        if not archivo.exists()
    ]

    if faltantes:

        raise FileNotFoundError(
            "Faltan archivos: "
            +
            ", ".join(
                str(archivo)
                for archivo
                in faltantes
            )
        )

    return archivos


# =============================================================================
# 11. MAIN
# =============================================================================

def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mes",
        help=(
            "Mes 01-12 o 'todos'."
        ),
    )

    parser.add_argument(
        "--desde",
        help=(
            "Primer mes del rango."
        ),
    )

    parser.add_argument(
        "--hasta",
        help=(
            "Último mes del rango."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE_DEFAULT,
        help=(
            "Filas por bloque. "
            "Por defecto: 100000."
        ),
    )

    parser.add_argument(
        "--mantener-indices",
        action="store_true",
        help=(
            "No elimina ni recrea los índices."
        ),
    )

    args = parser.parse_args()

    if args.batch_size < 10_000:

        sys.exit(
            "[ERROR] batch-size debe ser como mínimo 10000."
        )

    titulo(
        "CARGA OPTIMIZADA DE TAXI EN POSTGRESQL"
    )

    print(
        f"[INFO] Proyecto: {PROYECTO}"
    )
    print(
        f"[INFO] Datos: {DATA_DIR}"
    )
    print(
        f"[INFO] Batch size: {args.batch_size:,}"
    )
    print(
        "[INFO] Destino: "
        f"{POSTGRES_CONFIG['dbname']}."
        f"{SCHEMA}.{TABLA}"
    )

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    archivos = seleccionar_archivos(
        mes=args.mes,
        desde=args.desde,
        hasta=args.hasta,
    )

    print(
        f"[INFO] Archivos seleccionados: {len(archivos)}"
    )

    for archivo in archivos:

        print(
            f"       - {archivo.name}"
        )

    zonas_origen, zonas_destino = (
        cargar_lookup_zonas()
    )

    if not args.mantener_indices:

        eliminar_indices()

    correctamente = False

    try:

        for archivo in archivos:

            procesar_mes(
                archivo=archivo,
                batch_size=args.batch_size,
                zonas_origen=zonas_origen,
                zonas_destino=zonas_destino,
            )

        correctamente = True

    finally:

        if (
            not args.mantener_indices
            and correctamente
        ):

            crear_indices()

        elif (
            not args.mantener_indices
            and not correctamente
        ):

            print()
            print(
                "[AVISO] La ejecución no terminó."
            )
            print(
                "[AVISO] Los índices no se recrearon automáticamente."
            )
            print(
                "[AVISO] Continúa la carga y recréalos al terminar."
            )

    validar_postgresql()

    titulo(
        "CARGA FINALIZADA CORRECTAMENTE"
    )


if __name__ == "__main__":

    main()


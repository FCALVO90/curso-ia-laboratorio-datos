#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CARGA NYC YELLOW TAXI LIMPIO EN 3 BBDD
======================================

MariaDB:
    Base: nyc_taxi
    tablas:
        viajes_limpios
        zonas_taxi

PostgreSQL:
    Base: curso_ia
    schema: nyc_taxi
    tablas:
        viajes_limpios
        zonas_taxi

MongoDB:
    Base: nyc_taxi
    colecciones:
        viajes_limpios
        zonas_taxi

EJECUCION:

    python src/python/cargar_taxi_bbdd.py

Por defecto carga enero.

Todos los meses:

    python src/python/cargar_taxi_bbdd.py --mes todos

Un mes:

    python src/python/cargar_taxi_bbdd.py --mes 03
"""

from __future__ import annotations

import argparse
import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from pymongo import ASCENDING, MongoClient
from sqlalchemy import create_engine, text


# ============================================================
# 1. RUTAS
# ============================================================

HOME = Path.home()

PROYECTO = HOME / "curso_ia"

DATA_DIR = (
    PROYECTO
    / "datos"
    / "raw"
    / "taxi"
)

LOOKUP = (
    DATA_DIR
    / "taxi_zone_lookup.csv"
)


# ============================================================
# 2. CONEXIONES
# ============================================================

MARIA_URL = (
    "mysql+pymysql://curso_ia:"
    "CursoIA_2026@127.0.0.1:3306/nyc_taxi"
)

POSTGRES_URL = (
    "postgresql+psycopg2://postgres:"
    "CursoIA_2026@127.0.0.1:5432/curso_ia"
)

MONGO_URL = (
    "mongodb://127.0.0.1:27017"
)


# ============================================================
# 3. NOMBRES LOGICOS
# ============================================================

SCHEMA_POSTGRES = "nyc_taxi"

MONGO_DATABASE = "nyc_taxi"

TABLA_VIAJES = "viajes_limpios"

TABLA_ZONAS = "zonas_taxi"


# ============================================================
# 4. CONFIGURACION
# ============================================================

CHUNKSIZE_SQL = 10000

CHUNKSIZE_MONGO = 10000


# ============================================================
# 5. FUNCION TITULO
# ============================================================

def titulo(texto):

    print("\n")
    print("=" * 78)
    print(f" {texto}")
    print("=" * 78)


# ============================================================
# 6. COMPROBAR MARIADB
# ============================================================

def preparar_mariadb():

    titulo("PREPARANDO MARIADB")

    engine = create_engine(
        MARIA_URL,
        pool_pre_ping=True
    )

    with engine.connect() as conexion:

        base = conexion.execute(
            text("SELECT DATABASE()")
        ).scalar()

        print(
            f"[OK] MariaDB conectado"
        )

        print(
            f"[OK] Base de datos: {base}"
        )

    return engine


# ============================================================
# 7. COMPROBAR POSTGRESQL
# ============================================================

def preparar_postgresql():

    titulo("PREPARANDO POSTGRESQL")

    engine = create_engine(
        POSTGRES_URL,
        pool_pre_ping=True
    )

    with engine.begin() as conexion:

        conexion.execute(
            text(
                """
                CREATE SCHEMA IF NOT EXISTS nyc_taxi
                """
            )
        )

        base = conexion.execute(
            text(
                "SELECT current_database()"
            )
        ).scalar()

        print(
            "[OK] PostgreSQL conectado"
        )

        print(
            f"[OK] Base de datos: {base}"
        )

        print(
            f"[OK] Schema: {SCHEMA_POSTGRES}"
        )

    return engine


# ============================================================
# 8. COMPROBAR MONGODB
# ============================================================

def preparar_mongodb():

    titulo("PREPARANDO MONGODB")

    cliente = MongoClient(
        MONGO_URL,
        serverSelectionTimeoutMS=5000
    )

    cliente.admin.command(
        "ping"
    )

    db = cliente[
        MONGO_DATABASE
    ]

    print(
        "[OK] MongoDB conectado"
    )

    print(
        f"[OK] Base de datos: {MONGO_DATABASE}"
    )

    return cliente, db


# ============================================================
# 9. LEER LOOKUP
# ============================================================

def cargar_zonas():

    titulo("CARGANDO LOOKUP DE ZONAS")

    if not LOOKUP.exists():

        raise FileNotFoundError(
            f"No existe {LOOKUP}"
        )

    zonas = pd.read_csv(
        LOOKUP
    )

    zonas = zonas.rename(
        columns={
            "LocationID": "location_id",
            "Borough": "borough",
            "Zone": "zona",
            "service_zone": "zona_servicio"
        }
    )

    columnas = [
        "location_id",
        "borough",
        "zona",
        "zona_servicio"
    ]

    zonas = zonas[
        columnas
    ].copy()

    zonas["location_id"] = (
        pd.to_numeric(
            zonas["location_id"],
            errors="coerce"
        )
    )

    zonas = zonas.dropna(
        subset=[
            "location_id"
        ]
    )

    zonas["location_id"] = (
        zonas["location_id"]
        .astype(int)
    )

    zonas = zonas.drop_duplicates(
        subset=[
            "location_id"
        ]
    )

    print(
        f"[OK] Zonas cargadas: {len(zonas):,}"
    )

    return zonas


# ============================================================
# 10. VARIABLES DERIVADAS
# ============================================================

def preparar_variables(
    df,
    mes,
    archivo
):

    datos = df.copy()

    datos[
        "tpep_pickup_datetime"
    ] = pd.to_datetime(
        datos[
            "tpep_pickup_datetime"
        ],
        errors="coerce"
    )

    datos[
        "tpep_dropoff_datetime"
    ] = pd.to_datetime(
        datos[
            "tpep_dropoff_datetime"
        ],
        errors="coerce"
    )

    datos[
        "duracion_min"
    ] = (
        (
            datos[
                "tpep_dropoff_datetime"
            ]
            -
            datos[
                "tpep_pickup_datetime"
            ]
        )
        .dt
        .total_seconds()
        / 60
    )

    datos[
        "velocidad_mph"
    ] = np.where(
        datos[
            "duracion_min"
        ] > 0,

        datos[
            "trip_distance"
        ]
        /
        (
            datos[
                "duracion_min"
            ]
            / 60
        ),

        np.nan
    )

    datos[
        "fecha"
    ] = (
        datos[
            "tpep_pickup_datetime"
        ]
        .dt
        .normalize()
    )

    datos[
        "hora"
    ] = (
        datos[
            "tpep_pickup_datetime"
        ]
        .dt
        .hour
    )

    datos[
        "dia_semana_num"
    ] = (
        datos[
            "tpep_pickup_datetime"
        ]
        .dt
        .dayofweek
    )

    dias = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sabado",
        6: "Domingo"
    }

    datos[
        "dia_semana"
    ] = (
        datos[
            "dia_semana_num"
        ]
        .map(dias)
    )

    datos[
        "fin_semana"
    ] = (
        datos[
            "dia_semana_num"
        ]
        >= 5
    )

    datos[
        "mes_origen"
    ] = f"2024-{mes}"

    datos[
        "archivo_origen"
    ] = archivo

    return datos


# ============================================================
# 11. LIMPIEZA
# ============================================================

def limpiar_viajes(
    datos,
    mes
):

    inicio_mes = pd.Timestamp(
        f"2024-{mes}-01"
    )

    fin_mes = (
        inicio_mes
        + pd.offsets.MonthBegin(1)
    )

    # --------------------------------------------------------
    # SOLO CONSERVAMOS VIAJES VALIDOS
    # --------------------------------------------------------

    filtro = (

        datos[
            "tpep_pickup_datetime"
        ].between(
            inicio_mes,
            fin_mes,
            inclusive="left"
        )

        &

        (
            datos[
                "tpep_dropoff_datetime"
            ]
            >
            datos[
                "tpep_pickup_datetime"
            ]
        )

        &

        datos[
            "duracion_min"
        ].between(
            0,
            1440,
            inclusive="neither"
        )

        &

        (
            datos[
                "trip_distance"
            ] > 0
        )

        &

        (
            datos[
                "fare_amount"
            ] > 0
        )

        &

        (
            datos[
                "total_amount"
            ] > 0
        )

        &

        datos[
            "PULocationID"
        ].notna()

        &

        datos[
            "DOLocationID"
        ].notna()
    )

    viajes = (
        datos
        .loc[filtro]
        .copy()
    )

    # --------------------------------------------------------
    # DESCARTAR VELOCIDADES IMPOSIBLES
    # --------------------------------------------------------

    viajes = viajes[
        viajes[
            "velocidad_mph"
        ].between(
            0,
            100,
            inclusive="right"
        )
    ].copy()

    return viajes


# ============================================================
# 12. AÑADIR INFORMACION DE ZONAS
# ============================================================

def enriquecer_zonas(
    viajes,
    zonas
):

    origen = zonas.rename(
        columns={
            "location_id":
                "PULocationID",

            "borough":
                "borough_origen",

            "zona":
                "zona_origen",

            "zona_servicio":
                "zona_servicio_origen"
        }
    )

    destino = zonas.rename(
        columns={
            "location_id":
                "DOLocationID",

            "borough":
                "borough_destino",

            "zona":
                "zona_destino",

            "zona_servicio":
                "zona_servicio_destino"
        }
    )

    viajes = viajes.merge(
        origen,
        on="PULocationID",
        how="left"
    )

    viajes = viajes.merge(
        destino,
        on="DOLocationID",
        how="left"
    )

    return viajes


# ============================================================
# 13. NORMALIZAR NOMBRES
# ============================================================

def normalizar_columnas(
    datos
):

    datos = datos.rename(
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
                "airport_fee"
        }
    )

    datos.columns = [
        columna.lower()
        for columna
        in datos.columns
    ]

    datos = datos.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return datos


# ============================================================
# 14. CARGAR LOOKUP EN LAS 3 BBDD
# ============================================================

def cargar_zonas_bbdd(
    zonas,
    maria_engine,
    postgres_engine,
    mongo_db
):

    titulo(
        "GUARDANDO ZONAS EN LAS TRES BBDD"
    )

    # --------------------------------------------------------
    # MARIADB
    # --------------------------------------------------------

    zonas.to_sql(
        TABLA_ZONAS,
        maria_engine,
        if_exists="replace",
        index=False,
        chunksize=CHUNKSIZE_SQL
    )

    print(
        f"[OK] MariaDB: {TABLA_ZONAS}"
    )

    # --------------------------------------------------------
    # POSTGRESQL
    # --------------------------------------------------------

    zonas.to_sql(
        TABLA_ZONAS,
        postgres_engine,
        schema=SCHEMA_POSTGRES,
        if_exists="replace",
        index=False,
        chunksize=CHUNKSIZE_SQL
    )

    print(
        f"[OK] PostgreSQL: "
        f"{SCHEMA_POSTGRES}.{TABLA_ZONAS}"
    )

    # --------------------------------------------------------
    # MONGODB
    # --------------------------------------------------------

    coleccion = mongo_db[
        TABLA_ZONAS
    ]

    coleccion.drop()

    documentos = (
        zonas
        .where(
            pd.notnull(zonas),
            None
        )
        .to_dict(
            orient="records"
        )
    )

    if documentos:

        coleccion.insert_many(
            documentos
        )

    coleccion.create_index(
        [
            (
                "location_id",
                ASCENDING
            )
        ],
        unique=True
    )

    print(
        f"[OK] MongoDB: {TABLA_ZONAS}"
    )


# ============================================================
# 15. ELIMINAR MES PREVIO
# ============================================================

def eliminar_mes(
    mes,
    maria_engine,
    postgres_engine,
    mongo_db
):

    titulo(
        f"LIMPIANDO CARGA ANTERIOR {mes}"
    )

    # --------------------------------------------------------
    # MARIADB
    # --------------------------------------------------------

    with maria_engine.begin() as conexion:

        existe = conexion.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = :tabla
                """
            ),
            {
                "tabla":
                    TABLA_VIAJES
            }
        ).scalar()

        if existe:

            resultado = conexion.execute(
                text(
                    f"""
                    DELETE
                    FROM {TABLA_VIAJES}
                    WHERE mes_origen = :mes
                    """
                ),
                {
                    "mes":
                        mes
                }
            )

            print(
                "[OK] MariaDB eliminados: "
                f"{resultado.rowcount:,}"
            )

    # --------------------------------------------------------
    # POSTGRESQL
    # --------------------------------------------------------

    with postgres_engine.begin() as conexion:

        existe = conexion.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = :schema
                AND table_name = :tabla
                """
            ),
            {
                "schema":
                    SCHEMA_POSTGRES,

                "tabla":
                    TABLA_VIAJES
            }
        ).scalar()

        if existe:

            resultado = conexion.execute(
                text(
                    f"""
                    DELETE
                    FROM {SCHEMA_POSTGRES}.{TABLA_VIAJES}
                    WHERE mes_origen = :mes
                    """
                ),
                {
                    "mes":
                        mes
                }
            )

            print(
                "[OK] PostgreSQL eliminados: "
                f"{resultado.rowcount:,}"
            )

    # --------------------------------------------------------
    # MONGODB
    # --------------------------------------------------------

    resultado = (
        mongo_db[
            TABLA_VIAJES
        ]
        .delete_many(
            {
                "mes_origen":
                    mes
            }
        )
    )

    print(
        "[OK] MongoDB eliminados: "
        f"{resultado.deleted_count:,}"
    )


# ============================================================
# 16. PREPARAR DATAFRAME PARA SQL
# ============================================================

def preparar_para_sql(
    viajes
):

    datos = viajes.copy()

    # --------------------------------------------------------
    # ENTEROS CON NULOS
    # --------------------------------------------------------

    columnas_enteras = [
        "vendor_id",
        "passenger_count",
        "ratecode_id",
        "pu_location_id",
        "do_location_id",
        "payment_type",
        "hora",
        "dia_semana_num"
    ]

    for columna in columnas_enteras:

        if columna in datos.columns:

            datos[
                columna
            ] = pd.to_numeric(
                datos[
                    columna
                ],
                errors="coerce"
            )

    # --------------------------------------------------------
    # REEMPLAZAR INFINITOS
    # --------------------------------------------------------

    datos = datos.replace(
        [np.inf, -np.inf],
        np.nan
    )

    return datos


# ============================================================
# 17. CARGA SQL
# ============================================================

def cargar_sql(
    viajes,
    maria_engine,
    postgres_engine
):

    titulo(
        "CARGANDO VIAJES EN SQL"
    )

    viajes.to_sql(
        TABLA_VIAJES,
        maria_engine,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE_SQL
    )

    print(
        "[OK] MariaDB insertados: "
        f"{len(viajes):,}"
    )

    viajes.to_sql(
        TABLA_VIAJES,
        postgres_engine,
        schema=SCHEMA_POSTGRES,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE_SQL
    )

    print(
        "[OK] PostgreSQL insertados: "
        f"{len(viajes):,}"
    )


# ============================================================
# 18. CONVERSION PARA MONGODB
# ============================================================

def valor_mongo(valor):

    if isinstance(
        valor,
        pd.Timestamp
    ):

        if pd.isna(valor):
            return None

        return valor.to_pydatetime()

    if isinstance(
        valor,
        np.generic
    ):

        valor = valor.item()

    try:

        if pd.isna(valor):
            return None

    except (
        TypeError,
        ValueError
    ):
        pass

    if isinstance(
        valor,
        float
    ):

        if not np.isfinite(
            valor
        ):
            return None

    return valor


# ============================================================
# 19. CARGA MONGODB
# ============================================================

def cargar_mongodb(
    viajes,
    mongo_db
):

    titulo(
        "CARGANDO VIAJES EN MONGODB"
    )

    coleccion = mongo_db[
        TABLA_VIAJES
    ]

    total = len(
        viajes
    )

    insertados = 0

    for inicio in range(
        0,
        total,
        CHUNKSIZE_MONGO
    ):

        fin = min(
            inicio
            + CHUNKSIZE_MONGO,
            total
        )

        bloque = (
            viajes
            .iloc[
                inicio:fin
            ]
        )

        registros = []

        for registro in bloque.to_dict(
            orient="records"
        ):

            documento = {
                clave:
                    valor_mongo(valor)

                for clave, valor
                in registro.items()
            }

            registros.append(
                documento
            )

        if registros:

            coleccion.insert_many(
                registros,
                ordered=False
            )

        insertados += len(
            registros
        )

        print(
            "[MONGO] "
            f"{insertados:,} / "
            f"{total:,}"
        )

    print(
        "[OK] MongoDB insertados: "
        f"{insertados:,}"
    )


# ============================================================
# 20. PROCESAR UN MES
# ============================================================

def procesar_mes(
    archivo,
    zonas,
    maria_engine,
    postgres_engine,
    mongo_db
):

    mes = archivo.stem[-2:]

    mes_logico = (
        f"2024-{mes}"
    )

    titulo(
        f"PROCESANDO {archivo.name}"
    )

    inicio = time.perf_counter()

    # --------------------------------------------------------
    # LEER PARQUET
    # --------------------------------------------------------

    datos = pd.read_parquet(
        archivo
    )

    filas_originales = len(
        datos
    )

    print(
        "[INFO] Registros originales: "
        f"{filas_originales:,}"
    )

    # --------------------------------------------------------
    # VARIABLES DERIVADAS
    # --------------------------------------------------------

    datos = preparar_variables(
        datos,
        mes,
        archivo.name
    )

    # --------------------------------------------------------
    # LIMPIEZA
    # --------------------------------------------------------

    viajes = limpiar_viajes(
        datos,
        mes
    )

    filas_limpias = len(
        viajes
    )

    eliminadas = (
        filas_originales
        -
        filas_limpias
    )

    porcentaje = (
        eliminadas
        /
        filas_originales
        * 100
    )

    print(
        "[INFO] Viajes limpios: "
        f"{filas_limpias:,}"
    )

    print(
        "[INFO] Eliminados: "
        f"{eliminadas:,}"
        f" ({porcentaje:.2f}%)"
    )

    # --------------------------------------------------------
    # AÑADIR ZONAS
    # --------------------------------------------------------

    viajes = enriquecer_zonas(
        viajes,
        zonas
    )

    # --------------------------------------------------------
    # NORMALIZAR
    # --------------------------------------------------------

    viajes = normalizar_columnas(
        viajes
    )

    viajes = preparar_para_sql(
        viajes
    )

    # --------------------------------------------------------
    # ELIMINAR CARGA ANTIGUA DEL MISMO MES
    # --------------------------------------------------------

    eliminar_mes(
        mes_logico,
        maria_engine,
        postgres_engine,
        mongo_db
    )

    # --------------------------------------------------------
    # CARGAR SQL
    # --------------------------------------------------------

    cargar_sql(
        viajes,
        maria_engine,
        postgres_engine
    )

    # --------------------------------------------------------
    # CARGAR MONGODB
    # --------------------------------------------------------

    cargar_mongodb(
        viajes,
        mongo_db
    )

    duracion = (
        time.perf_counter()
        -
        inicio
    )

    print()
    print(
        f"[OK] {mes_logico} terminado"
    )

    print(
        "[OK] Tiempo: "
        f"{duracion:.2f} segundos"
    )

    del datos
    del viajes

    gc.collect()


# ============================================================
# 21. CREAR INDICES
# ============================================================

def crear_indices(
    maria_engine,
    postgres_engine,
    mongo_db
):

    titulo(
        "CREANDO INDICES"
    )

    # --------------------------------------------------------
    # MARIADB
    # --------------------------------------------------------

    indices = {
        "idx_taxi_fecha":
            "tpep_pickup_datetime",

        "idx_taxi_mes":
            "mes_origen",

        "idx_taxi_origen":
            "pu_location_id",

        "idx_taxi_destino":
            "do_location_id"
    }

    with maria_engine.begin() as conexion:

        for nombre, columna in indices.items():

            existe = conexion.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                    AND table_name = :tabla
                    AND index_name = :indice
                    """
                ),
                {
                    "tabla":
                        TABLA_VIAJES,

                    "indice":
                        nombre
                }
            ).scalar()

            if not existe:

                conexion.execute(
                    text(
                        f"""
                        CREATE INDEX {nombre}
                        ON {TABLA_VIAJES}
                        ({columna})
                        """
                    )
                )

    print(
        "[OK] Indices MariaDB"
    )

    # --------------------------------------------------------
    # POSTGRESQL
    # --------------------------------------------------------

    with postgres_engine.begin() as conexion:

        for nombre, columna in indices.items():

            conexion.execute(
                text(
                    f"""
                    CREATE INDEX IF NOT EXISTS
                    {nombre}
                    ON
                    {SCHEMA_POSTGRES}.{TABLA_VIAJES}
                    ({columna})
                    """
                )
            )

    print(
        "[OK] Indices PostgreSQL"
    )

    # --------------------------------------------------------
    # MONGODB
    # --------------------------------------------------------

    coleccion = mongo_db[
        TABLA_VIAJES
    ]

    coleccion.create_index(
        [
            (
                "tpep_pickup_datetime",
                ASCENDING
            )
        ]
    )

    coleccion.create_index(
        [
            (
                "mes_origen",
                ASCENDING
            )
        ]
    )

    coleccion.create_index(
        [
            (
                "pu_location_id",
                ASCENDING
            )
        ]
    )

    coleccion.create_index(
        [
            (
                "do_location_id",
                ASCENDING
            )
        ]
    )

    print(
        "[OK] Indices MongoDB"
    )


# ============================================================
# 22. VALIDACION FINAL
# ============================================================

def validar(
    maria_engine,
    postgres_engine,
    mongo_db
):

    titulo(
        "VALIDACION FINAL"
    )

    # --------------------------------------------------------
    # MARIADB
    # --------------------------------------------------------

    with maria_engine.connect() as conexion:

        maria = conexion.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM {TABLA_VIAJES}
                """
            )
        ).scalar()

    # --------------------------------------------------------
    # POSTGRESQL
    # --------------------------------------------------------

    with postgres_engine.connect() as conexion:

        postgres = conexion.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM
                {SCHEMA_POSTGRES}.{TABLA_VIAJES}
                """
            )
        ).scalar()

    # --------------------------------------------------------
    # MONGODB
    # --------------------------------------------------------

    mongo = (
        mongo_db[
            TABLA_VIAJES
        ]
        .count_documents({})
    )

    print(
        f"MariaDB    : {maria:,}"
    )

    print(
        f"PostgreSQL : {postgres:,}"
    )

    print(
        f"MongoDB    : {mongo:,}"
    )

    print()

    if (
        maria
        ==
        postgres
        ==
        mongo
    ):

        print(
            "[OK] LOS TRES RECUENTOS COINCIDEN"
        )

    else:

        print(
            "[AVISO] LOS RECUENTOS NO COINCIDEN"
        )


# ============================================================
# 23. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mes",
        default="01",
        help=(
            "Mes 01-12 o todos. "
            "Por defecto 01."
        )
    )

    args = parser.parse_args()

    titulo(
        "CARGA NYC TAXI EN LAS TRES BBDD"
    )

    print(
        f"[INFO] Proyecto: {PROYECTO}"
    )

    print(
        f"[INFO] Datos: {DATA_DIR}"
    )

    print(
        f"[INFO] Mes: {args.mes}"
    )

    print()
    print(
        "[INFO] DESTINOS:"
    )

    print(
        "       MariaDB    -> nyc_taxi"
    )

    print(
        "       PostgreSQL -> curso_ia.nyc_taxi"
    )

    print(
        "       MongoDB    -> nyc_taxi"
    )

    # --------------------------------------------------------
    # COMPROBAR DATOS
    # --------------------------------------------------------

    if not DATA_DIR.exists():

        sys.exit(
            f"[ERROR] No existe {DATA_DIR}"
        )

    # --------------------------------------------------------
    # CONEXIONES
    # --------------------------------------------------------

    maria_engine = preparar_mariadb()

    postgres_engine = preparar_postgresql()

    mongo_cliente, mongo_db = (
        preparar_mongodb()
    )

    try:

        # ----------------------------------------------------
        # ZONAS
        # ----------------------------------------------------

        zonas = cargar_zonas()

        cargar_zonas_bbdd(
            zonas,
            maria_engine,
            postgres_engine,
            mongo_db
        )

        # ----------------------------------------------------
        # SELECCIONAR ARCHIVOS
        # ----------------------------------------------------

        if (
            args.mes.lower()
            ==
            "todos"
        ):

            archivos = sorted(
                DATA_DIR.glob(
                    "yellow_tripdata_2024-*.parquet"
                )
            )

        else:

            mes = (
                args.mes
                .zfill(2)
            )

            meses_validos = {
                f"{numero:02d}"
                for numero
                in range(
                    1,
                    13
                )
            }

            if mes not in meses_validos:

                sys.exit(
                    "[ERROR] "
                    "Use un mes 01-12 "
                    "o --mes todos"
                )

            ruta = (
                DATA_DIR
                /
                f"yellow_tripdata_2024-{mes}.parquet"
            )

            archivos = [
                ruta
            ]

        # ----------------------------------------------------
        # DESCARTAR LOS QUE NO EXISTAN
        # ----------------------------------------------------

        archivos = [
            archivo
            for archivo
            in archivos
            if archivo.exists()
        ]

        if not archivos:

            sys.exit(
                "[ERROR] "
                "No se encontraron Parquet."
            )

        print()
        print(
            "[INFO] Archivos encontrados: "
            f"{len(archivos)}"
        )

        # ----------------------------------------------------
        # PROCESAR MES A MES
        # ----------------------------------------------------

        for archivo in archivos:

            procesar_mes(
                archivo,
                zonas,
                maria_engine,
                postgres_engine,
                mongo_db
            )

        # ----------------------------------------------------
        # INDICES
        # ----------------------------------------------------

        crear_indices(
            maria_engine,
            postgres_engine,
            mongo_db
        )

        # ----------------------------------------------------
        # VALIDACION
        # ----------------------------------------------------

        validar(
            maria_engine,
            postgres_engine,
            mongo_db
        )

    finally:

        maria_engine.dispose()

        postgres_engine.dispose()

        mongo_cliente.close()

        print()
        print(
            "[OK] Conexiones cerradas"
        )

    titulo(
        "CARGA FINALIZADA CORRECTAMENTE"
    )


# ============================================================
# 24. EJECUCION
# ============================================================

if __name__ == "__main__":

    main()

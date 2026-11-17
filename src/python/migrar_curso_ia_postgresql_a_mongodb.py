#!/usr/bin/env python3

import csv
import json
import logging
import math
import os
import re
import sys
import time
import uuid

from datetime import date, datetime, time as dt_time
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from bson import Binary
from bson.decimal128 import Decimal128
from bson.int64 import Int64

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import BulkWriteError


# ============================================================
# CONFIGURACION
# ============================================================

PROYECTO = Path.home() / "curso_ia"

SALIDA = PROYECTO / "salidas" / "migracion_postgresql_mongodb"
SALIDA_CSV = SALIDA / "csv"
SALIDA_JSON = SALIDA / "json"
SALIDA_LOGS = SALIDA / "logs"
SALIDA_TXT = SALIDA / "txt"

for directorio in (
    SALIDA_CSV,
    SALIDA_JSON,
    SALIDA_LOGS,
    SALIDA_TXT,
):
    directorio.mkdir(parents=True, exist_ok=True)


PG_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", "5432")),
    "dbname": os.getenv("PGDATABASE", "curso_ia"),
    "user": os.getenv("PGUSER", os.getenv("USER", "postgres")),
    "password": os.getenv("PGPASSWORD", ""),
}

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017",
)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5000"))

ESQUEMAS_EXCLUIDOS = {
    "pg_catalog",
    "information_schema",
}

BASES_MONGO_PROTEGIDAS = {
    "admin",
    "config",
    "local",
}

BASES_MONGO_LIMPIABLES = {
    "curso_ia",
    "aire_madrid",
    "nyc_taxi",
    "retail",
}

RECREAR_MONGO = (
    os.getenv("RECREAR_MONGO", "true").lower()
    in {"true", "1", "yes", "si", "sí"}
)

LOG_FILE = SALIDA_LOGS / "01_migracion_completa.log"


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_FILE,
            mode="w",
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("migracion_pg_mongo")


# ============================================================
# CONVERSION DE TIPOS
# ============================================================

def convertir_bson(valor):
    if valor is None:
        return None

    if isinstance(valor, bool):
        return valor

    if isinstance(valor, Int64):
        return valor

    if isinstance(valor, int):
        if -(2**31) <= valor <= (2**31 - 1):
            return valor

        if -(2**63) <= valor <= (2**63 - 1):
            return Int64(valor)

        return str(valor)

    if isinstance(valor, float):
        if math.isnan(valor) or math.isinf(valor):
            return None

        return valor

    if isinstance(valor, Decimal):
        try:
            return Decimal128(valor)
        except Exception:
            return str(valor)

    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            valor = valor.astimezone().replace(tzinfo=None)

        return valor

    if isinstance(valor, date):
        return datetime.combine(valor, datetime.min.time())

    if isinstance(valor, dt_time):
        return valor.isoformat()

    if isinstance(valor, uuid.UUID):
        return str(valor)

    if isinstance(valor, memoryview):
        return Binary(valor.tobytes())

    if isinstance(valor, bytes):
        return Binary(valor)

    if isinstance(valor, dict):
        return {
            str(clave): convertir_bson(contenido)
            for clave, contenido in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [
            convertir_bson(elemento)
            for elemento in valor
        ]

    return valor


def convertir_json(valor):
    if valor is None:
        return None

    if isinstance(valor, Decimal128):
        return str(valor.to_decimal())

    if isinstance(valor, Decimal):
        return str(valor)

    if isinstance(valor, Int64):
        return int(valor)

    if isinstance(valor, (datetime, date, dt_time)):
        return valor.isoformat()

    if isinstance(valor, uuid.UUID):
        return str(valor)

    if isinstance(valor, (Binary, bytes, bytearray)):
        return f"<binario:{len(valor)} bytes>"

    if isinstance(valor, dict):
        return {
            str(clave): convertir_json(contenido)
            for clave, contenido in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [
            convertir_json(elemento)
            for elemento in valor
        ]

    return valor


def guardar_json(ruta, contenido):
    with ruta.open("w", encoding="utf-8") as fichero:
        json.dump(
            convertir_json(contenido),
            fichero,
            ensure_ascii=False,
            indent=4,
        )


# ============================================================
# CONEXIONES
# ============================================================

def conectar_postgresql():
    logger.info(
        "Conectando con PostgreSQL %s:%s/%s como %s",
        PG_CONFIG["host"],
        PG_CONFIG["port"],
        PG_CONFIG["dbname"],
        PG_CONFIG["user"],
    )

    conexion = psycopg2.connect(**PG_CONFIG)
    conexion.autocommit = False

    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                current_database(),
                current_user,
                version()
            """
        )

        base, usuario, version = cursor.fetchone()

    logger.info("PostgreSQL conectado")
    logger.info("Base: %s", base)
    logger.info("Usuario: %s", usuario)
    logger.info("Version: %s", version)

    return conexion


def conectar_mongodb():
    logger.info("Conectando con MongoDB: %s", MONGO_URI)

    cliente = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=None,
    )

    resultado = cliente.admin.command("ping")

    logger.info("MongoDB conectado: %s", resultado)

    return cliente


# ============================================================
# INVENTARIO POSTGRESQL
# ============================================================

def obtener_esquemas_usuario(conexion):
    consulta = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN (
            'pg_catalog',
            'information_schema'
        )
          AND schema_name NOT LIKE 'pg_toast%%'
          AND schema_name NOT LIKE 'pg_temp_%%'
        ORDER BY schema_name
    """

    with conexion.cursor() as cursor:
        cursor.execute(consulta)

        esquemas = [
            fila[0]
            for fila in cursor.fetchall()
        ]

    return esquemas


def obtener_objetos(conexion):
    consulta = """
        SELECT
            n.nspname AS esquema,
            c.relname AS objeto,
            c.relkind AS codigo_tipo,
            CASE c.relkind
                WHEN 'r' THEN 'tabla'
                WHEN 'p' THEN 'tabla_particionada'
                WHEN 'f' THEN 'tabla_foranea'
                WHEN 'v' THEN 'vista'
                WHEN 'm' THEN 'vista_materializada'
                ELSE c.relkind::text
            END AS tipo,
            pg_catalog.obj_description(
                c.oid,
                'pg_class'
            ) AS comentario
        FROM pg_catalog.pg_class AS c
        INNER JOIN pg_catalog.pg_namespace AS n
            ON n.oid = c.relnamespace
        WHERE n.nspname NOT IN (
            'pg_catalog',
            'information_schema'
        )
          AND n.nspname NOT LIKE 'pg_toast%%'
          AND n.nspname NOT LIKE 'pg_temp_%%'
          AND c.relkind IN ('r', 'p', 'f', 'v', 'm')
        ORDER BY
            n.nspname,
            CASE c.relkind
                WHEN 'r' THEN 1
                WHEN 'p' THEN 2
                WHEN 'f' THEN 3
                WHEN 'v' THEN 4
                WHEN 'm' THEN 5
                ELSE 6
            END,
            c.relname
    """

    with conexion.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(consulta)

        return [
            dict(fila)
            for fila in cursor.fetchall()
        ]


def obtener_columnas(conexion, esquema, objeto):
    consulta = """
        SELECT
            ordinal_position,
            column_name,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
    """

    with conexion.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(
            consulta,
            (esquema, objeto),
        )

        return [
            dict(fila)
            for fila in cursor.fetchall()
        ]


def obtener_clave_primaria(conexion, esquema, objeto):
    consulta = """
        SELECT
            a.attname AS columna,
            posicion.ordinalidad
        FROM pg_catalog.pg_index AS i
        INNER JOIN pg_catalog.pg_class AS c
            ON c.oid = i.indrelid
        INNER JOIN pg_catalog.pg_namespace AS n
            ON n.oid = c.relnamespace
        INNER JOIN unnest(i.indkey)
            WITH ORDINALITY AS posicion(attnum, ordinalidad)
            ON TRUE
        INNER JOIN pg_catalog.pg_attribute AS a
            ON a.attrelid = c.oid
           AND a.attnum = posicion.attnum
        WHERE n.nspname = %s
          AND c.relname = %s
          AND i.indisprimary
        ORDER BY posicion.ordinalidad
    """

    with conexion.cursor() as cursor:
        cursor.execute(
            consulta,
            (esquema, objeto),
        )

        return [
            fila[0]
            for fila in cursor.fetchall()
        ]


def obtener_indices(conexion, esquema, objeto):
    consulta = """
        SELECT
            indice.relname AS nombre_indice,
            i.indisunique AS es_unico,
            i.indisprimary AS es_primario,
            pg_get_indexdef(i.indexrelid) AS definicion,
            pg_get_expr(
                i.indpred,
                i.indrelid
            ) AS predicado,
            ARRAY_AGG(
                atributo.attname
                ORDER BY posicion.ordinalidad
            ) FILTER (
                WHERE atributo.attname IS NOT NULL
            ) AS columnas,
            ARRAY_AGG(
                opcion
                ORDER BY posicion.ordinalidad
            ) FILTER (
                WHERE atributo.attname IS NOT NULL
            ) AS opciones_orden,
            BOOL_OR(
                posicion.attnum = 0
            ) AS tiene_expresion
        FROM pg_catalog.pg_class AS tabla
        INNER JOIN pg_catalog.pg_namespace AS esquema
            ON esquema.oid = tabla.relnamespace
        INNER JOIN pg_catalog.pg_index AS i
            ON i.indrelid = tabla.oid
        INNER JOIN pg_catalog.pg_class AS indice
            ON indice.oid = i.indexrelid
        LEFT JOIN unnest(i.indkey, i.indoption)
            WITH ORDINALITY
            AS posicion(attnum, opcion, ordinalidad)
            ON TRUE
        LEFT JOIN pg_catalog.pg_attribute AS atributo
            ON atributo.attrelid = tabla.oid
           AND atributo.attnum = posicion.attnum
        WHERE esquema.nspname = %s
          AND tabla.relname = %s
        GROUP BY
            indice.relname,
            i.indisunique,
            i.indisprimary,
            i.indexrelid,
            i.indpred,
            i.indrelid
        ORDER BY indice.relname
    """

    with conexion.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(
            consulta,
            (esquema, objeto),
        )

        resultados = []

        for fila in cursor.fetchall():
            resultado = dict(fila)
            resultado["columnas"] = resultado["columnas"] or []
            resultado["opciones_orden"] = (
                resultado["opciones_orden"] or []
            )
            resultados.append(resultado)

        return resultados


def obtener_restricciones(conexion, esquema, objeto):
    consulta = """
        SELECT
            restriccion.conname AS nombre,
            CASE restriccion.contype
                WHEN 'p' THEN 'PRIMARY KEY'
                WHEN 'f' THEN 'FOREIGN KEY'
                WHEN 'u' THEN 'UNIQUE'
                WHEN 'c' THEN 'CHECK'
                WHEN 'x' THEN 'EXCLUSION'
                ELSE restriccion.contype::text
            END AS tipo,
            pg_get_constraintdef(
                restriccion.oid,
                true
            ) AS definicion
        FROM pg_catalog.pg_constraint AS restriccion
        INNER JOIN pg_catalog.pg_class AS tabla
            ON tabla.oid = restriccion.conrelid
        INNER JOIN pg_catalog.pg_namespace AS esquema
            ON esquema.oid = tabla.relnamespace
        WHERE esquema.nspname = %s
          AND tabla.relname = %s
        ORDER BY restriccion.conname
    """

    with conexion.cursor(
        cursor_factory=RealDictCursor
    ) as cursor:
        cursor.execute(
            consulta,
            (esquema, objeto),
        )

        return [
            dict(fila)
            for fila in cursor.fetchall()
        ]


def obtener_definicion_vista(conexion, esquema, objeto, tipo):
    if tipo not in {"vista", "vista_materializada"}:
        return None

    consulta = """
        SELECT pg_get_viewdef(
            format('%%I.%%I', %s, %s)::regclass,
            true
        )
    """

    with conexion.cursor() as cursor:
        cursor.execute(
            consulta,
            (esquema, objeto),
        )

        resultado = cursor.fetchone()

    return resultado[0] if resultado else None


def contar_postgresql(conexion, esquema, objeto):
    consulta = sql.SQL(
        "SELECT COUNT(*) FROM {}.{}"
    ).format(
        sql.Identifier(esquema),
        sql.Identifier(objeto),
    )

    with conexion.cursor() as cursor:
        cursor.execute(consulta)
        return int(cursor.fetchone()[0])


# ============================================================
# SEGURIDAD DEL BORRADO MONGODB
# ============================================================

def limpiar_bases_mongodb(cliente, esquemas):
    if not RECREAR_MONGO:
        logger.warning(
            "RECREAR_MONGO=false: no se eliminan bases MongoDB"
        )
        return

    bases_existentes = set(cliente.list_database_names())

    bases_destino = set(esquemas)

    bases_a_eliminar = (
        BASES_MONGO_LIMPIABLES
        | bases_destino
    )

    bases_a_eliminar -= BASES_MONGO_PROTEGIDAS

    logger.warning(
        "Bases MongoDB existentes: %s",
        sorted(bases_existentes),
    )

    logger.warning(
        "Bases candidatas a eliminacion: %s",
        sorted(bases_a_eliminar),
    )

    for base in sorted(bases_a_eliminar):
        if base in BASES_MONGO_PROTEGIDAS:
            raise RuntimeError(
                f"Intento de eliminar base protegida: {base}"
            )

        if base in bases_existentes:
            logger.warning(
                "Eliminando base MongoDB: %s",
                base,
            )
            cliente.drop_database(base)
        else:
            logger.info(
                "La base MongoDB no existe, no se elimina: %s",
                base,
            )


# ============================================================
# LECTURA POR LOTES
# ============================================================

def generar_lotes(conexion, esquema, objeto):
    nombre_cursor = (
        "migracion_"
        + re.sub(
            r"[^A-Za-z0-9_]",
            "_",
            f"{esquema}_{objeto}",
        )
        + "_"
        + uuid.uuid4().hex[:8]
    )

    cursor = conexion.cursor(
        name=nombre_cursor,
        cursor_factory=RealDictCursor,
    )

    cursor.itersize = BATCH_SIZE

    consulta = sql.SQL(
        "SELECT * FROM {}.{}"
    ).format(
        sql.Identifier(esquema),
        sql.Identifier(objeto),
    )

    try:
        cursor.execute(consulta)

        while True:
            filas = cursor.fetchmany(BATCH_SIZE)

            if not filas:
                break

            lote = []

            for fila in filas:
                documento = {
                    str(clave): convertir_bson(valor)
                    for clave, valor in dict(fila).items()
                }

                lote.append(documento)

            yield lote

    finally:
        cursor.close()


# ============================================================
# INDICES MONGODB
# ============================================================

def recrear_indices_mongodb(coleccion, indices):
    resultados = []

    for indice in indices:
        nombre = indice["nombre_indice"]
        columnas = indice["columnas"]
        opciones = indice["opciones_orden"]
        unico = bool(indice["es_unico"])
        expresion = bool(indice["tiene_expresion"])
        predicado = indice["predicado"]

        if not columnas:
            resultados.append({
                "indice": nombre,
                "estado": "omitido_sin_columnas",
            })
            continue

        if expresion:
            resultados.append({
                "indice": nombre,
                "estado": "omitido_expresion",
            })
            continue

        if predicado:
            resultados.append({
                "indice": nombre,
                "estado": "omitido_parcial",
                "predicado": predicado,
            })
            continue

        claves = []

        for posicion, columna in enumerate(columnas):
            opcion = (
                opciones[posicion]
                if posicion < len(opciones)
                else 0
            )

            descendente = bool(opcion & 1)

            direccion = (
                DESCENDING
                if descendente
                else ASCENDING
            )

            claves.append((columna, direccion))

        nombre_mongo = re.sub(
            r"[^A-Za-z0-9_.-]",
            "_",
            nombre,
        )[:120]

        try:
            resultado = coleccion.create_index(
                claves,
                name=nombre_mongo,
                unique=unico,
                background=True,
            )

            resultados.append({
                "indice": nombre,
                "indice_mongodb": resultado,
                "columnas": columnas,
                "unique": unico,
                "estado": "creado",
            })

        except Exception as error:
            logger.warning(
                "No se pudo crear el indice %s: %s",
                nombre,
                error,
            )

            resultados.append({
                "indice": nombre,
                "columnas": columnas,
                "unique": unico,
                "estado": "error",
                "error": str(error),
            })

    return resultados


# ============================================================
# MIGRACION DE UN OBJETO
# ============================================================

def migrar_objeto(conexion_pg, cliente_mongo, objeto):
    esquema = objeto["esquema"]
    nombre = objeto["objeto"]
    tipo = objeto["tipo"]

    base_mongo = cliente_mongo[esquema]

    logger.info("=" * 80)
    logger.info(
        "Migrando %s.%s",
        esquema,
        nombre,
    )
    logger.info(
        "Destino MongoDB: %s.%s",
        esquema,
        nombre,
    )
    logger.info(
        "Tipo: %s",
        tipo,
    )

    inicio = time.time()

    columnas = obtener_columnas(
        conexion_pg,
        esquema,
        nombre,
    )

    clave_primaria = obtener_clave_primaria(
        conexion_pg,
        esquema,
        nombre,
    )

    restricciones = obtener_restricciones(
        conexion_pg,
        esquema,
        nombre,
    )

    indices = obtener_indices(
        conexion_pg,
        esquema,
        nombre,
    )

    definicion_vista = obtener_definicion_vista(
        conexion_pg,
        esquema,
        nombre,
        tipo,
    )

    total_postgresql = contar_postgresql(
        conexion_pg,
        esquema,
        nombre,
    )

    logger.info(
        "Filas PostgreSQL: %d",
        total_postgresql,
    )

    if nombre in base_mongo.list_collection_names():
        base_mongo.drop_collection(nombre)

    base_mongo.create_collection(nombre)
    coleccion = base_mongo[nombre]

    insertados = 0
    numero_lote = 0

    for lote in generar_lotes(
        conexion_pg,
        esquema,
        nombre,
    ):
        numero_lote += 1

        try:
            resultado = coleccion.insert_many(
                lote,
                ordered=False,
            )

            insertados += len(resultado.inserted_ids)

        except BulkWriteError as error:
            insertados += (
                error.details or {}
            ).get("nInserted", 0)

            logger.exception(
                "Error de escritura en %s.%s, lote %d",
                esquema,
                nombre,
                numero_lote,
            )

            raise

        logger.info(
            "Lote %d: %d/%d documentos",
            numero_lote,
            insertados,
            total_postgresql,
        )

    total_mongodb = coleccion.count_documents({})

    indices_mongodb = recrear_indices_mongodb(
        coleccion,
        indices,
    )

    duracion = round(time.time() - inicio, 3)

    verificado = total_postgresql == total_mongodb

    estado = "OK" if verificado else "ERROR_CONTEO"

    logger.info(
        "PostgreSQL=%d | MongoDB=%d | Estado=%s",
        total_postgresql,
        total_mongodb,
        estado,
    )

    return {
        "origen": {
            "base_datos": PG_CONFIG["dbname"],
            "esquema": esquema,
            "objeto": nombre,
            "tipo": tipo,
            "comentario": objeto["comentario"],
            "filas": total_postgresql,
            "columnas": columnas,
            "clave_primaria": clave_primaria,
            "restricciones": restricciones,
            "indices": indices,
            "definicion_vista": definicion_vista,
        },
        "destino": {
            "base_datos": esquema,
            "coleccion": nombre,
            "documentos": total_mongodb,
            "indices": indices_mongodb,
        },
        "migracion": {
            "estado": estado,
            "verificado": verificado,
            "duracion_segundos": duracion,
            "fecha": datetime.now(),
            "materializacion_vista": (
                tipo in {"vista", "vista_materializada"}
            ),
        },
    }


# ============================================================
# METADATOS
# ============================================================

def guardar_metadatos(cliente, resultados):
    resultados_por_esquema = {}

    for resultado in resultados:
        esquema = resultado["origen"]["esquema"]

        resultados_por_esquema.setdefault(
            esquema,
            [],
        ).append(resultado)

    for esquema, grupo in resultados_por_esquema.items():
        base = cliente[esquema]

        colecciones_meta = [
            "_meta_objetos_postgresql",
            "_meta_columnas_postgresql",
            "_meta_restricciones_postgresql",
            "_meta_indices_postgresql",
            "_meta_vistas_postgresql",
            "_meta_resumen_migracion",
        ]

        for coleccion in colecciones_meta:
            base.drop_collection(coleccion)

        objetos = []
        columnas = []
        restricciones = []
        indices = []
        vistas = []
        resumen = []

        for resultado in grupo:
            origen = resultado["origen"]
            destino = resultado["destino"]
            migracion = resultado["migracion"]

            identificador = (
                f"{origen['esquema']}.{origen['objeto']}"
            )

            objetos.append({
                "identificador": identificador,
                "esquema": origen["esquema"],
                "objeto": origen["objeto"],
                "tipo": origen["tipo"],
                "comentario": origen["comentario"],
                "coleccion_mongodb": destino["coleccion"],
            })

            for columna in origen["columnas"]:
                documento = convertir_bson(dict(columna))
                documento["objeto"] = identificador
                columnas.append(documento)

            for restriccion in origen["restricciones"]:
                documento = convertir_bson(dict(restriccion))
                documento["objeto"] = identificador
                restricciones.append(documento)

            for indice in origen["indices"]:
                documento = convertir_bson(dict(indice))
                documento["objeto"] = identificador
                indices.append(documento)

            if origen["definicion_vista"]:
                vistas.append({
                    "objeto": identificador,
                    "tipo": origen["tipo"],
                    "definicion_sql": (
                        origen["definicion_vista"]
                    ),
                    "coleccion_materializada": (
                        destino["coleccion"]
                    ),
                })

            resumen.append({
                "objeto_postgresql": identificador,
                "tipo": origen["tipo"],
                "coleccion_mongodb": destino["coleccion"],
                "filas_postgresql": origen["filas"],
                "documentos_mongodb": destino["documentos"],
                "estado": migracion["estado"],
                "verificado": migracion["verificado"],
                "duracion_segundos": (
                    migracion["duracion_segundos"]
                ),
                "fecha": migracion["fecha"],
            })

        datos = {
            "_meta_objetos_postgresql": objetos,
            "_meta_columnas_postgresql": columnas,
            "_meta_restricciones_postgresql": restricciones,
            "_meta_indices_postgresql": indices,
            "_meta_vistas_postgresql": vistas,
            "_meta_resumen_migracion": resumen,
        }

        for nombre, documentos in datos.items():
            base.create_collection(nombre)

            if documentos:
                base[nombre].insert_many(
                    documentos,
                    ordered=True,
                )

        base["_meta_objetos_postgresql"].create_index(
            [("identificador", ASCENDING)],
            unique=True,
        )

        base["_meta_resumen_migracion"].create_index(
            [
                ("estado", ASCENDING),
                ("tipo", ASCENDING),
            ]
        )


# ============================================================
# SALIDAS
# ============================================================

def guardar_salidas(resultados, inventario):
    guardar_json(
        SALIDA_JSON / "01_inventario_postgresql.json",
        {
            "fecha": datetime.now(),
            "base_postgresql": PG_CONFIG["dbname"],
            "objetos": inventario,
        },
    )

    guardar_json(
        SALIDA_JSON / "02_resultado_migracion.json",
        {
            "fecha": datetime.now(),
            "origen": PG_CONFIG["dbname"],
            "resultados": resultados,
        },
    )

    ruta_csv = SALIDA_CSV / "01_resumen_migracion.csv"

    with ruta_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as fichero:
        campos = [
            "esquema_postgresql",
            "objeto_postgresql",
            "tipo",
            "base_mongodb",
            "coleccion_mongodb",
            "filas_postgresql",
            "documentos_mongodb",
            "diferencia",
            "estado",
            "duracion_segundos",
        ]

        escritor = csv.DictWriter(
            fichero,
            fieldnames=campos,
        )

        escritor.writeheader()

        for resultado in resultados:
            origen = resultado["origen"]
            destino = resultado["destino"]
            migracion = resultado["migracion"]

            escritor.writerow({
                "esquema_postgresql": origen["esquema"],
                "objeto_postgresql": origen["objeto"],
                "tipo": origen["tipo"],
                "base_mongodb": destino["base_datos"],
                "coleccion_mongodb": destino["coleccion"],
                "filas_postgresql": origen["filas"],
                "documentos_mongodb": destino["documentos"],
                "diferencia": (
                    destino["documentos"]
                    - origen["filas"]
                ),
                "estado": migracion["estado"],
                "duracion_segundos": (
                    migracion["duracion_segundos"]
                ),
            })

    ruta_txt = SALIDA_TXT / "01_verificacion_migracion.txt"

    with ruta_txt.open("w", encoding="utf-8") as fichero:
        fichero.write(
            "MIGRACION POSTGRESQL -> MONGODB\n"
        )
        fichero.write("=" * 100 + "\n")

        for resultado in resultados:
            origen = resultado["origen"]
            destino = resultado["destino"]
            migracion = resultado["migracion"]

            fichero.write(
                f"{origen['esquema']}.{origen['objeto']} "
                f"-> {destino['base_datos']}."
                f"{destino['coleccion']} | "
                f"PostgreSQL={origen['filas']} | "
                f"MongoDB={destino['documentos']} | "
                f"{migracion['estado']}\n"
            )


# ============================================================
# MAIN
# ============================================================

def main():
    conexion_pg = None
    cliente_mongo = None

    try:
        logger.info("=" * 80)
        logger.info(
            "MIGRACION COMPLETA POSTGRESQL -> MONGODB"
        )
        logger.info("=" * 80)

        conexion_pg = conectar_postgresql()
        cliente_mongo = conectar_mongodb()

        esquemas = obtener_esquemas_usuario(
            conexion_pg
        )

        objetos = obtener_objetos(
            conexion_pg
        )

        esquemas_con_objetos = sorted({
            objeto["esquema"]
            for objeto in objetos
        })

        logger.info(
            "Esquemas PostgreSQL detectados: %s",
            esquemas,
        )

        logger.info(
            "Esquemas con objetos migrables: %s",
            esquemas_con_objetos,
        )

        logger.info(
            "Objetos detectados: %d",
            len(objetos),
        )

        if not objetos:
            raise RuntimeError(
                "No se han encontrado objetos migrables"
            )

        for objeto in objetos:
            logger.info(
                "Inventario: %s.%s | %s",
                objeto["esquema"],
                objeto["objeto"],
                objeto["tipo"],
            )

        limpiar_bases_mongodb(
            cliente_mongo,
            esquemas_con_objetos,
        )

        resultados = []

        for numero, objeto in enumerate(objetos, start=1):
            logger.info(
                "Objeto %d/%d",
                numero,
                len(objetos),
            )

            resultado = migrar_objeto(
                conexion_pg,
                cliente_mongo,
                objeto,
            )

            resultados.append(resultado)

        guardar_metadatos(
            cliente_mongo,
            resultados,
        )

        guardar_salidas(
            resultados,
            objetos,
        )

        correctos = sum(
            1
            for resultado in resultados
            if resultado["migracion"]["verificado"]
        )

        total_postgresql = sum(
            resultado["origen"]["filas"]
            for resultado in resultados
        )

        total_mongodb = sum(
            resultado["destino"]["documentos"]
            for resultado in resultados
        )

        logger.info("=" * 80)
        logger.info("MIGRACION TERMINADA")
        logger.info(
            "Objetos correctos: %d/%d",
            correctos,
            len(resultados),
        )
        logger.info(
            "Filas totales PostgreSQL: %d",
            total_postgresql,
        )
        logger.info(
            "Documentos totales MongoDB: %d",
            total_mongodb,
        )
        logger.info(
            "Resumen: %s",
            SALIDA_CSV / "01_resumen_migracion.csv",
        )
        logger.info(
            "Log: %s",
            LOG_FILE,
        )

        if correctos != len(resultados):
            return 2

        return 0

    except KeyboardInterrupt:
        logger.warning(
            "Proceso interrumpido por el usuario"
        )
        return 130

    except Exception:
        logger.exception(
            "Error durante la migracion"
        )
        return 1

    finally:
        if conexion_pg is not None:
            conexion_pg.close()
            logger.info("Conexion PostgreSQL cerrada")

        if cliente_mongo is not None:
            cliente_mongo.close()
            logger.info("Conexion MongoDB cerrada")


if __name__ == "__main__":
    sys.exit(main())

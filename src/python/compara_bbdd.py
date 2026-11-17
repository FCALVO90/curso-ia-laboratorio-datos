#!/usr/bin/env python3

# ============================================================
# COMPARACION MARIADB -> POSTGRESQL -> MONGODB
# ONLINE RETAIL II
# ============================================================

import os
import getpass

import pandas as pd
from sqlalchemy import create_engine, text
from pymongo import MongoClient, InsertOne

# ============================================================
# 1. CONFIGURACION
# ============================================================

MARIADB_USER = os.getenv("MARIADB_USER", "curso_ia")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD") or getpass.getpass(
    f"Contraseña MariaDB para {MARIADB_USER}: "
)
MARIADB_HOST = os.getenv("MARIADB_HOST", "127.0.0.1")
MARIADB_PORT = os.getenv("MARIADB_PORT", "3306")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "curso_ia")

POSTGRES_USER = os.getenv("PGUSER", "postgres")
POSTGRES_PASSWORD = os.getenv("PGPASSWORD") or getpass.getpass(
    f"Contraseña PostgreSQL para {POSTGRES_USER}: "
)
POSTGRES_HOST = os.getenv("PGHOST", "127.0.0.1")
POSTGRES_PORT = os.getenv("PGPORT", "5432")
POSTGRES_DATABASE = os.getenv("PGDATABASE", "curso_ia")

MARIA_URL = (
    f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}"
    f"@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}"
)

POSTGRES_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
)

MONGO_URL = "mongodb://127.0.0.1:27017"

print("=" * 70)
print("COMPARACION MARIADB - POSTGRESQL - MONGODB")
print("=" * 70)

# ============================================================
# 2. CONEXIONES SQL
# ============================================================

maria = create_engine(MARIA_URL)
postgres = create_engine(POSTGRES_URL)

with maria.connect() as con:
    maria_count = con.execute(
        text("SELECT COUNT(*) FROM online_retail_ii")
    ).scalar_one()

with postgres.connect() as con:
    postgres_count = con.execute(
        text("SELECT COUNT(*) FROM retail.online_retail_ii")
    ).scalar_one()

print("\nREGISTROS ORIGINALES")
print("-" * 70)
print(f"MariaDB    : {maria_count:,}")
print(f"PostgreSQL : {postgres_count:,}")

# ============================================================
# 3. MONGODB
# ============================================================

mongo = MongoClient(MONGO_URL)

mongo.admin.command("ping")

db = mongo["curso_ia"]
collection = db["online_retail_ii"]

print("\nConexion MongoDB OK")

# ============================================================
# 4. VACIAR COLECCION PARA HACER LA PRACTICA REPRODUCIBLE
# ============================================================

collection.drop()

print("Coleccion MongoDB preparada")

# ============================================================
# 5. LEER MARIADB POR BLOQUES Y CARGAR MONGODB
# ============================================================

CHUNK_SIZE = 10000
total_insertados = 0

print("\nCARGANDO MARIADB -> MONGODB")
print("-" * 70)

for numero, chunk in enumerate(
    pd.read_sql(
        "SELECT * FROM online_retail_ii",
        maria,
        chunksize=CHUNK_SIZE
    ),
    start=1
):

    # MongoDB no debe recibir NaN/NaT de Pandas
    chunk = chunk.astype(object).where(pd.notnull(chunk), None)

    documentos = chunk.to_dict("records")

    if documentos:
        operaciones = [
            InsertOne(documento)
            for documento in documentos
        ]

        resultado = collection.bulk_write(
            operaciones,
            ordered=False
        )

        total_insertados += resultado.inserted_count

    print(
        f"Bloque {numero:03d} | "
        f"insertados acumulados: {total_insertados:,}"
    )

# ============================================================
# 6. INDICES MONGODB
# ============================================================

collection.create_index("invoice_no")
collection.create_index("customer_id")
collection.create_index("country")

# ============================================================
# 7. CONTAR MONGODB
# ============================================================

mongo_count = collection.count_documents({})

# ============================================================
# 8. COMPARACION DE NUMERO DE REGISTROS
# ============================================================

print("\n" + "=" * 70)
print("COMPARACION DE REGISTROS")
print("=" * 70)

print(f"MariaDB    : {maria_count:,}")
print(f"PostgreSQL : {postgres_count:,}")
print(f"MongoDB    : {mongo_count:,}")

conteos_iguales = (
    maria_count
    == postgres_count
    == mongo_count
)

print(f"\nMISMO NUMERO DE REGISTROS: {conteos_iguales}")

# ============================================================
# 9. COMPARACIONES FUNCIONALES
# ============================================================

with maria.connect() as con:

    maria_stats = con.execute(text("""
        SELECT
            COUNT(DISTINCT invoice_no) AS facturas,
            COUNT(DISTINCT customer_id) AS clientes,
            COUNT(DISTINCT country) AS paises
        FROM online_retail_ii
    """)).mappings().one()

with postgres.connect() as con:

    postgres_stats = con.execute(text("""
        SELECT
            COUNT(DISTINCT invoice_no) AS facturas,
            COUNT(DISTINCT customer_id) AS clientes,
            COUNT(DISTINCT country) AS paises
        FROM retail.online_retail_ii
    """)).mappings().one()

mongo_facturas = len(
    collection.distinct(
        "invoice_no",
        {"invoice_no": {"$ne": None}}
    )
)

mongo_clientes = len(
    collection.distinct(
        "customer_id",
        {"customer_id": {"$ne": None}}
    )
)

mongo_paises = len(
    collection.distinct(
        "country",
        {"country": {"$ne": None}}
    )
)

# ============================================================
# 10. RESULTADOS
# ============================================================

print("\n" + "=" * 70)
print("COMPARACION FUNCIONAL")
print("=" * 70)

print("\nFACTURAS")
print(f"MariaDB    : {maria_stats['facturas']:,}")
print(f"PostgreSQL : {postgres_stats['facturas']:,}")
print(f"MongoDB    : {mongo_facturas:,}")

print("\nCLIENTES")
print(f"MariaDB    : {maria_stats['clientes']:,}")
print(f"PostgreSQL : {postgres_stats['clientes']:,}")
print(f"MongoDB    : {mongo_clientes:,}")

print("\nPAISES")
print(f"MariaDB    : {maria_stats['paises']:,}")
print(f"PostgreSQL : {postgres_stats['paises']:,}")
print(f"MongoDB    : {mongo_paises:,}")

facturas_ok = (
    maria_stats["facturas"]
    == postgres_stats["facturas"]
    == mongo_facturas
)

clientes_ok = (
    maria_stats["clientes"]
    == postgres_stats["clientes"]
    == mongo_clientes
)

paises_ok = (
    maria_stats["paises"]
    == postgres_stats["paises"]
    == mongo_paises
)

print("\n" + "=" * 70)
print("VALIDACION FINAL")
print("=" * 70)

print(f"Registros iguales : {conteos_iguales}")
print(f"Facturas iguales  : {facturas_ok}")
print(f"Clientes iguales  : {clientes_ok}")
print(f"Paises iguales    : {paises_ok}")

TODO_OK = (
    conteos_iguales
    and facturas_ok
    and clientes_ok
    and paises_ok
)

if TODO_OK:
    print("\n>>> VALIDACION CORRECTA: LAS TRES BBDD SON COHERENTES <<<")
else:
    print("\n>>> ATENCION: EXISTEN DIFERENCIAS ENTRE LAS BBDD <<<")

# ============================================================
# 11. CERRAR
# ============================================================

mongo.close()
maria.dispose()
postgres.dispose()

print("\nProceso finalizado.")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
============================================================
INSPECCION DATASET NYC YELLOW TAXI
============================================================
Objetivo:
    - Localizar todos los Parquet disponibles.
    - Comprobar meses disponibles.
    - Inspeccionar esquema, columnas y tipos.
    - Obtener numero de filas sin cargar todo el año.
    - Mostrar una muestra de datos.
    - Revisar nulos y estadisticas basicas de cada mes.
    - Inspeccionar taxi_zone_lookup.csv.

Proyecto:
    ~/curso_ia

Datos:
    ~/curso_ia/datos/raw/taxi/

Ejecutar:
    python src/python/inspeccionar_taxi.py
============================================================
"""

from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq


# ============================================================
# 1. RUTAS DEL PROYECTO
# ============================================================

HOME = Path.home()

PROYECTO = HOME / "curso_ia"
DATA_DIR = PROYECTO / "datos" / "raw" / "taxi"

LOOKUP = DATA_DIR / "taxi_zone_lookup.csv"

print("\n" + "=" * 70)
print(" INSPECCION DEL DATASET NYC YELLOW TAXI")
print("=" * 70)

print(f"\n[INFO] Proyecto : {PROYECTO}")
print(f"[INFO] Datos    : {DATA_DIR}")


# ============================================================
# 2. COMPROBAR DIRECTORIO
# ============================================================

if not DATA_DIR.exists():
    print("\n[ERROR] No existe el directorio:")
    print(DATA_DIR)
    sys.exit(1)

print("\n[OK] Directorio de datos localizado.")


# ============================================================
# 3. BUSCAR TODOS LOS PARQUET
# ============================================================

archivos = sorted(DATA_DIR.glob("yellow_tripdata_2024-*.parquet"))

print("\n" + "=" * 70)
print(" FICHEROS PARQUET LOCALIZADOS")
print("=" * 70)

if not archivos:
    print("\n[ERROR] No se han encontrado archivos Parquet.")
    print("Patron esperado:")
    print("yellow_tripdata_2024-XX.parquet")
    sys.exit(1)

print(f"\n[OK] Meses/ficheros encontrados: {len(archivos)}\n")

for archivo in archivos:

    tam_mb = archivo.stat().st_size / (1024 ** 2)

    print(f"    {archivo.name:<40} {tam_mb:10.2f} MB")


# ============================================================
# 4. INSPECCION GENERAL DE CADA MES
# ============================================================

print("\n" + "=" * 70)
print(" INSPECCION MES A MES")
print("=" * 70)

resumen = []

esquema_referencia = None

for numero, archivo in enumerate(archivos, start=1):

    print("\n")
    print("#" * 70)
    print(f" FICHERO {numero}/{len(archivos)}")
    print(f" {archivo.name}")
    print("#" * 70)

    # --------------------------------------------------------
    # LEER METADATOS PARQUET
    # Esto NO carga todo el dataset en memoria.
    # --------------------------------------------------------

    parquet = pq.ParquetFile(archivo)

    filas = parquet.metadata.num_rows
    columnas = parquet.metadata.num_columns
    row_groups = parquet.metadata.num_row_groups

    tam_mb = archivo.stat().st_size / (1024 ** 2)

    print(f"\n[INFO] Tamano fichero : {tam_mb:,.2f} MB")
    print(f"[INFO] Numero filas   : {filas:,}")
    print(f"[INFO] Numero columnas: {columnas}")
    print(f"[INFO] Row groups     : {row_groups}")

    # --------------------------------------------------------
    # MOSTRAR ESQUEMA
    # --------------------------------------------------------

    schema = parquet.schema_arrow

    print("\n[ESQUEMA]")
    print("-" * 70)

    for campo in schema:
        print(f"{campo.name:<35} -> {campo.type}")

    # --------------------------------------------------------
    # COMPROBAR SI CAMBIA EL ESQUEMA ENTRE MESES
    # --------------------------------------------------------

    nombres_columnas = schema.names

    if esquema_referencia is None:

        esquema_referencia = nombres_columnas

        print("\n[OK] Este fichero establece el esquema de referencia.")

    elif nombres_columnas == esquema_referencia:

        print("\n[OK] El esquema coincide con el primer fichero.")

    else:

        print("\n[AVISO] El esquema NO coincide exactamente.")

        columnas_nuevas = set(nombres_columnas) - set(esquema_referencia)
        columnas_faltantes = set(esquema_referencia) - set(nombres_columnas)

        print("Columnas nuevas   :", columnas_nuevas)
        print("Columnas faltantes:", columnas_faltantes)

    # --------------------------------------------------------
    # LEER SOLO UNA PEQUENA MUESTRA
    # --------------------------------------------------------

    print("\n[MUESTRA - PRIMERAS 5 FILAS]")
    print("-" * 70)

    tabla_muestra = parquet.read_row_group(0)
    muestra = tabla_muestra.slice(0, 5).to_pandas()

    print(muestra.to_string(index=False))

    # --------------------------------------------------------
    # GUARDAR RESUMEN
    # --------------------------------------------------------

    resumen.append({
        "archivo": archivo.name,
        "filas": filas,
        "columnas": columnas,
        "row_groups": row_groups,
        "tamano_mb": round(tam_mb, 2)
    })


# ============================================================
# 5. DATAFRAME RESUMEN DEL ANO
# ============================================================

df_resumen = pd.DataFrame(resumen)

print("\n\n" + "=" * 70)
print(" RESUMEN DE TODOS LOS MESES")
print("=" * 70)

print("\n")
print(df_resumen.to_string(index=False))

print("\n[INFO] Numero total de registros segun metadatos:")

total_filas = df_resumen["filas"].sum()

print(f"{total_filas:,} registros")


# ============================================================
# 6. INSPECCION MAS PROFUNDA DEL PRIMER MES
# ============================================================

primer_archivo = archivos[0]

print("\n" + "=" * 70)
print(" INSPECCION DETALLADA DEL PRIMER MES")
print("=" * 70)

print(f"\n[INFO] Se analizara: {primer_archivo.name}")

print("\n[INFO] Cargando el primer mes con pandas...")

df = pd.read_parquet(primer_archivo)

print("[OK] Dataset cargado.")


# ============================================================
# 7. DIMENSIONES
# ============================================================

print("\n--- DIMENSIONES ---")

print(f"Filas   : {df.shape[0]:,}")
print(f"Columnas: {df.shape[1]}")


# ============================================================
# 8. COLUMNAS
# ============================================================

print("\n--- COLUMNAS ---")

for numero, columna in enumerate(df.columns, start=1):

    print(f"{numero:02d}. {columna}")


# ============================================================
# 9. TIPOS
# ============================================================

print("\n--- TIPOS DE DATOS ---")

print(df.dtypes)


# ============================================================
# 10. PRIMERAS FILAS
# ============================================================

print("\n--- PRIMERAS 10 FILAS ---")

print(df.head(10).to_string())


# ============================================================
# 11. NULOS
# ============================================================

print("\n--- VALORES NULOS ---")

nulos = df.isna().sum()

nulos = nulos[nulos > 0].sort_values(ascending=False)

if len(nulos) == 0:

    print("[OK] No se han encontrado valores nulos.")

else:

    print(nulos)


# ============================================================
# 12. ESTADISTICAS DESCRIPTIVAS
# ============================================================

print("\n--- ESTADISTICAS DESCRIPTIVAS ---")

print(
    df.describe(
        include="all"
    ).transpose().to_string()
)


# ============================================================
# 13. MEMORIA
# ============================================================

memoria_mb = df.memory_usage(deep=True).sum() / 1024 ** 2

print("\n--- MEMORIA ---")

print(f"Memoria aproximada del DataFrame: {memoria_mb:,.2f} MB")


# ============================================================
# 14. COMPROBAR VARIABLES IMPORTANTES
# ============================================================

print("\n" + "=" * 70)
print(" VARIABLES IMPORTANTES PARA LOS EJERCICIOS")
print("=" * 70)

variables = [
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
]

for variable in variables:

    if variable in df.columns:

        print(f"[OK] {variable}")

    else:

        print(f"[NO ENCONTRADA] {variable}")


# ============================================================
# 15. INSPECCION DEL LOOKUP DE ZONAS
# ============================================================

print("\n" + "=" * 70)
print(" TAXI ZONE LOOKUP")
print("=" * 70)

if LOOKUP.exists():

    zonas = pd.read_csv(LOOKUP)

    print(f"\n[OK] Encontrado: {LOOKUP.name}")

    print(f"Filas   : {zonas.shape[0]:,}")
    print(f"Columnas: {zonas.shape[1]}")

    print("\nColumnas:")

    print(zonas.columns.tolist())

    print("\nPrimeras 10 zonas:")

    print(zonas.head(10).to_string(index=False))

else:

    print("\n[AVISO] No esta disponible taxi_zone_lookup.csv")


# ============================================================
# 16. GUARDAR RESUMEN
# ============================================================

OUTPUT_DIR = PROYECTO / "salidas" / "taxi" / "python" / "csv"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

salida = OUTPUT_DIR / "resumen_datasets_taxi.csv"

df_resumen.to_csv(
    salida,
    index=False
)

print("\n" + "=" * 70)
print(" INSPECCION FINALIZADA")
print("=" * 70)

print(f"\n[OK] Resumen guardado en:")
print(salida)

print("\nYa podemos utilizar esta informacion para construir")
print("los ejercicios definitivos de Python/Spyder.")
print("=" * 70 + "\n")

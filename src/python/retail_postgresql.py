#!/usr/bin/env python3
# ============================================================
# ONLINE RETAIL II
# LECTURA, ANALISIS DESCRIPTIVO, VISUALIZACION Y POSTGRESQL
# ============================================================

from pathlib import Path
from getpass import getpass
import os
import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path.home() / "curso_ia"
EXCEL_PATH = BASE_DIR / "datos/raw/retail/online_retail_II.xlsx"
OUTPUT_DIR = BASE_DIR / "salidas" / "retail" / "python" / "graficos"
PROCESSED_DIR = BASE_DIR / "datos" / "processed" / "retail"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("ONLINE RETAIL II - PYTHON Y POSTGRESQL")
print("=" * 70)
print(f"Excel: {EXCEL_PATH}")

if not EXCEL_PATH.exists():
    print(f"ERROR: no existe {EXCEL_PATH}")
    print("Contenido disponible:")
    for archivo in (BASE_DIR / "datos/raw/retail").glob("*"):
        print(f"  - {archivo.name}")
    sys.exit(1)

# ============================================================
# 2. LEER TODAS LAS HOJAS DEL EXCEL
# ============================================================

excel = pd.ExcelFile(EXCEL_PATH, engine="openpyxl")

print("\nHojas encontradas:")
for hoja in excel.sheet_names:
    print(f"  - {hoja}")

dataframes = []

for hoja in excel.sheet_names:
    print(f"\nLeyendo hoja: {hoja}")

    temporal = pd.read_excel(
        EXCEL_PATH,
        sheet_name=hoja,
        engine="openpyxl",
        dtype={
            "Invoice": "string",
            "InvoiceNo": "string",
            "StockCode": "string",
            "Description": "string",
            "Customer ID": "string",
            "CustomerID": "string",
            "Country": "string"
        }
    )

    temporal["hoja_origen"] = hoja
    dataframes.append(temporal)

df = pd.concat(dataframes, ignore_index=True)

print(f"\nFilas importadas: {len(df):,}")
print(f"Columnas importadas: {len(df.columns)}")
print(f"Columnas originales: {list(df.columns)}")

# ============================================================
# 3. NORMALIZAR NOMBRES DE COLUMNAS
# ============================================================

def normalizar_columna(nombre):
    nombre = str(nombre).strip()
    nombre = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", nombre)
    nombre = nombre.lower()
    nombre = re.sub(r"[^a-z0-9]+", "_", nombre)
    return nombre.strip("_")

df.columns = [normalizar_columna(columna) for columna in df.columns]

# Compatibilidad entre nombres usados en distintas versiones
renombrados = {
    "invoice": "invoice_no",
    "customer_id": "customer_id",
    "price": "unit_price"
}

df = df.rename(columns=renombrados)

print(f"Columnas normalizadas: {list(df.columns)}")

# ============================================================
# 4. CONVERSION DE TIPOS
# ============================================================

df["invoice_no"] = df["invoice_no"].astype("string").str.strip()
df["stock_code"] = df["stock_code"].astype("string").str.strip()
df["description"] = df["description"].astype("string").str.strip()
df["customer_id"] = df["customer_id"].astype("string").str.replace(
    r"\.0$", "", regex=True
)
df["country"] = df["country"].astype("string").str.strip()

df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")

# ============================================================
# 5. VARIABLES DERIVADAS, SIN BORRAR DATOS RAW
# ============================================================

df["is_cancelled"] = (
    df["invoice_no"]
    .fillna("")
    .str.upper()
    .str.startswith("C")
)

df["total_amount"] = df["quantity"] * df["unit_price"]
df["invoice_year"] = df["invoice_date"].dt.year.astype("Int64")
df["invoice_month"] = df["invoice_date"].dt.month.astype("Int64")
df["invoice_day"] = df["invoice_date"].dt.day.astype("Int64")
df["invoice_hour"] = df["invoice_date"].dt.hour.astype("Int64")

# ============================================================
# 6. ANALISIS DESCRIPTIVO
# ============================================================

print("\n" + "=" * 70)
print("DIMENSIONES")
print("=" * 70)
print(df.shape)

print("\n" + "=" * 70)
print("PRIMERAS FILAS")
print("=" * 70)
print(df.head(10).to_string())

print("\n" + "=" * 70)
print("TIPOS DE DATOS")
print("=" * 70)
print(df.dtypes)

print("\n" + "=" * 70)
print("VALORES NULOS")
print("=" * 70)
print(df.isna().sum().sort_values(ascending=False))

print("\n" + "=" * 70)
print("DUPLICADOS")
print("=" * 70)
print(f"Filas duplicadas completas: {df.duplicated().sum():,}")

print("\n" + "=" * 70)
print("RESUMEN NUMERICO")
print("=" * 70)
print(
    df[["quantity", "unit_price", "total_amount"]]
    .describe()
    .round(2)
    .to_string()
)

print("\n" + "=" * 70)
print("RESUMEN FUNCIONAL")
print("=" * 70)
print(f"Facturas diferentes: {df['invoice_no'].nunique():,}")
print(f"Productos diferentes: {df['stock_code'].nunique():,}")
print(f"Clientes diferentes: {df['customer_id'].nunique():,}")
print(f"Países diferentes: {df['country'].nunique():,}")
print(f"Operaciones canceladas: {df['is_cancelled'].sum():,}")
print(f"Cantidades negativas: {(df['quantity'] < 0).sum():,}")
print(f"Precios negativos: {(df['unit_price'] < 0).sum():,}")

# ============================================================
# 7. GUARDAR CSV PROCESADO
# ============================================================

csv_path = PROCESSED_DIR / "online_retail_ii_procesado.csv"

df.to_csv(csv_path, index=False)

print(f"\nCSV procesado guardado en: {csv_path}")

# ============================================================
# 8. VISUALIZACIONES
# ============================================================

sns.set_theme(style="whitegrid")

# GRAFICO 1: TOP 15 PAISES
top_paises = (
    df["country"]
    .dropna()
    .value_counts()
    .head(15)
    .sort_values()
)

plt.figure(figsize=(12, 7))
top_paises.plot(kind="barh", color="steelblue")
plt.title("Top 15 países por número de líneas de transacción")
plt.xlabel("Número de registros")
plt.ylabel("País")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "python_01_top_paises.png", dpi=150)
plt.show()
plt.close()

# Para ventas usamos únicamente operaciones no canceladas
ventas_validas = df[
    (~df["is_cancelled"])
    & (df["quantity"] > 0)
    & (df["unit_price"] > 0)
    & (df["invoice_date"].notna())
].copy()

# GRAFICO 2: VENTAS MENSUALES
ventas_mensuales = (
    ventas_validas
    .set_index("invoice_date")
    .resample("MS")["total_amount"]
    .sum()
)

plt.figure(figsize=(14, 6))
ventas_mensuales.plot(marker="o", color="darkgreen")
plt.title("Facturación mensual")
plt.xlabel("Mes")
plt.ylabel("Facturación")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "python_02_facturacion_mensual.png", dpi=150)
plt.show()
plt.close()

# GRAFICO 3: TOP 15 PRODUCTOS
top_productos = (
    ventas_validas
    .dropna(subset=["description"])
    .groupby("description")["quantity"]
    .sum()
    .nlargest(15)
    .sort_values()
)

plt.figure(figsize=(12, 8))
top_productos.plot(kind="barh", color="darkorange")
plt.title("Top 15 productos por unidades vendidas")
plt.xlabel("Unidades")
plt.ylabel("Producto")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "python_03_top_productos.png", dpi=150)
plt.show()
plt.close()

# GRAFICO 4: DISTRIBUCION DE PRECIOS SIN EXTREMOS
precios = ventas_validas["unit_price"].dropna()
limite_precio = precios.quantile(0.99)
precios_grafico = precios[precios <= limite_precio]

plt.figure(figsize=(12, 6))
sns.histplot(precios_grafico, bins=50, color="purple")
plt.title("Distribución del precio unitario hasta el percentil 99")
plt.xlabel("Precio unitario")
plt.ylabel("Frecuencia")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "python_04_distribucion_precios.png", dpi=150)
plt.show()
plt.close()

print(f"\nGráficos guardados en: {OUTPUT_DIR}")

# ============================================================
# 9. CONEXION Y CARGA EN POSTGRESQL
# ============================================================

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DATABASE = os.getenv("PG_DATABASE", "curso_ia")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD") or getpass(
    f"Contraseña PostgreSQL para {PG_USER}: "
)

url = URL.create(
    drivername="postgresql+psycopg2",
    username=PG_USER,
    password=PG_PASSWORD,
    host=PG_HOST,
    port=PG_PORT,
    database=PG_DATABASE
)

engine = create_engine(url, pool_pre_ping=True)

print("\nConectando con PostgreSQL...")

with engine.begin() as connection:
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS retail"))

print("Cargando tabla retail.online_retail_ii...")

df.to_sql(
    name="online_retail_ii",
    con=engine,
    schema="retail",
    if_exists="replace",
    index=False,
    chunksize=5000,
    method="multi"
)

# ============================================================
# 10. INDICES Y VALIDACION
# ============================================================

with engine.begin() as connection:
    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_retail_invoice_no
        ON retail.online_retail_ii (invoice_no)
    """))

    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_retail_customer_id
        ON retail.online_retail_ii (customer_id)
    """))

    connection.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_retail_invoice_date
        ON retail.online_retail_ii (invoice_date)
    """))

    filas_sql = connection.execute(
        text("SELECT COUNT(*) FROM retail.online_retail_ii")
    ).scalar_one()

engine.dispose()

print("\n" + "=" * 70)
print("CARGA POSTGRESQL FINALIZADA")
print("=" * 70)
print(f"Filas del DataFrame: {len(df):,}")
print(f"Filas en PostgreSQL: {filas_sql:,}")
print(f"Coincidencia: {len(df) == filas_sql}")

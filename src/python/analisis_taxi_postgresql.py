#!/usr/bin/env python3
"""
Análisis visual y modelado de NYC Taxi desde PostgreSQL.

Este script:
- No carga ni modifica datos.
- Ejecuta agregaciones directamente en PostgreSQL.
- Descarga únicamente resultados agregados y una muestra para ML.
- Guarda los CSV en salidas/taxi/python/csv.
- Guarda el resumen JSON en salidas/taxi/python/json.
- Guarda los gráficos Python en salidas/taxi/python/graficos.
"""
import json, os, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, balanced_accuracy_score,
    classification_report, confusion_matrix, f1_score, mean_absolute_error,
    mean_squared_error, median_absolute_error, precision_recall_curve,
    precision_score, r2_score, recall_score, roc_auc_score, roc_curve,
    average_precision_score)
from sklearn.model_selection import train_test_split
warnings.filterwarnings("ignore", category=FutureWarning)

from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split


# ---------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------------------------

warnings.filterwarnings("ignore", category=FutureWarning)

PROYECTO = Path.home() / "curso_ia"
SALIDAS_DIR = PROYECTO / "salidas" / "taxi" / "python"

CSV_DIR = SALIDAS_DIR / "csv"
JSON_DIR = SALIDAS_DIR / "json"
GRAFICOS_DIR = SALIDAS_DIR / "graficos"

for directorio in (CSV_DIR, JSON_DIR, GRAFICOS_DIR):
    directorio.mkdir(parents=True, exist_ok=True)

SCHEMA = os.getenv("PGSCHEMA", "nyc_taxi")
TABLE = os.getenv("PGTABLE", "viajes_limpios")

SAMPLE_PCT = float(os.getenv("TAXI_SAMPLE_PCT", "0.35"))
MAX_ROWS = int(os.getenv("TAXI_MAX_ROWS", "150000"))
SEED = int(os.getenv("TAXI_SEED", "42"))

PG_DSN = os.getenv("PG_DSN")

if not PG_DSN:
    raise RuntimeError(
        "ERROR: debes definir PG_DSN antes de ejecutar este script"
    )

engine = create_engine(
    PG_DSN,
    pool_pre_ping=True,
)


# ---------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------------------

def q(sql, **params):
    """
    Ejecuta una consulta SQL y devuelve un DataFrame.
    """
    return pd.read_sql(
        text(sql),
        engine,
        params=params,
    )


def savefig(name):
    """
    Guarda el gráfico activo en salidas/taxi/python/graficos y libera memoria.
    """
    output_path = GRAFICOS_DIR / name

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=160,
        bbox_inches="tight",
    )
    plt.close()

    print(f"[OK] Gráfico guardado: {output_path}")


def save_csv(dataframe, name):
    """
    Guarda un DataFrame en salidas/taxi/python/csv.
    """
    output_path = CSV_DIR / name

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print(f"[OK] CSV guardado: {output_path}")


# ---------------------------------------------------------------------
# CONEXIÓN Y DETECCIÓN DE COLUMNAS
# ---------------------------------------------------------------------

print("=" * 70)
print(" ANÁLISIS NYC TAXI DESDE POSTGRESQL CON PYTHON")
print("=" * 70)

print(f"[INFO] PostgreSQL: {SCHEMA}.{TABLE}")
print(f"[INFO] Máximo de registros para ML: {MAX_ROWS:,}")
print(f"[INFO] Porcentaje TABLESAMPLE: {SAMPLE_PCT}")
print(f"[INFO] Semilla: {SEED}")

cols = q(
    """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = :s
      AND table_name = :t
    ORDER BY ordinal_position
    """,
    s=SCHEMA,
    t=TABLE,
)["column_name"].tolist()

if not cols:
    raise RuntimeError(
        f"No existe la tabla {SCHEMA}.{TABLE} "
        "o el usuario no tiene permisos para consultarla."
    )

print(f"[OK] Columnas detectadas: {len(cols)}")

low = {
    column.lower(): column
    for column in cols
}


def C(*names):
    """
    Localiza una columna aunque su nombre cambie ligeramente.
    Devuelve el identificador entre comillas para PostgreSQL.
    """
    for name in names:
        if name.lower() in low:
            real_name = low[name.lower()]
            return '"' + real_name.replace('"', '""') + '"'

    raise RuntimeError(
        "Falta una columna. Nombres buscados: "
        + ", ".join(names)
    )


pickup = C(
    "tpep_pickup_datetime",
    "pickup_datetime",
)

dropoff = C(
    "tpep_dropoff_datetime",
    "dropoff_datetime",
)

dist = C("trip_distance")
fare = C("fare_amount")
tip = C("tip_amount")
total = C("total_amount")
pay = C("payment_type")

pu = C(
    "PULocationID",
    "pulocationid",
    "pu_location_id",
)

do = C(
    "DOLocationID",
    "dolocationid",
    "do_location_id",
)

passengers = C("passenger_count")

vendor = C(
    "VendorID",
    "vendorid",
    "vendor_id",
)

full_table = (
    f'"{SCHEMA.replace(chr(34), chr(34) * 2)}".'
    f'"{TABLE.replace(chr(34), chr(34) * 2)}"'
)

valid = f"""
    {pickup} >= TIMESTAMP '2024-01-01'
    AND {pickup} < TIMESTAMP '2025-01-01'
    AND {dist} > 0
    AND {dist} <= 100
    AND {fare} > 0
    AND {total} > 0
    AND {tip} >= 0
    AND {dropoff} > {pickup}
"""


# ---------------------------------------------------------------------
# 1. EVOLUCIÓN MENSUAL
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 1. EVOLUCIÓN MENSUAL")
print("=" * 70)

monthly = q(
    f"""
    SELECT
        date_trunc('month', {pickup})::date AS mes,
        COUNT(*) AS viajes,
        SUM({total}) AS ingresos,
        AVG({dist}) AS distancia_media,
        AVG(
            EXTRACT(
                EPOCH FROM ({dropoff} - {pickup})
            ) / 60.0
        ) AS duracion_media
    FROM {full_table}
    WHERE {valid}
    GROUP BY 1
    ORDER BY 1
    """
)

monthly["mes"] = pd.to_datetime(monthly["mes"])

save_csv(
    monthly,
    "01_resumen_mensual_python.csv",
)

fig, ax = plt.subplots(
    2,
    1,
    figsize=(11, 8),
)

ax[0].plot(
    monthly["mes"],
    monthly["viajes"],
    marker="o",
    linewidth=2,
)

ax[0].set_title("Viajes mensuales")
ax[0].set_ylabel("Viajes")
ax[0].grid(alpha=0.25)

ax[1].plot(
    monthly["mes"],
    monthly["ingresos"],
    marker="o",
    linewidth=2,
    color="tab:green",
)

ax[1].set_title("Ingresos mensuales")
ax[1].set_ylabel("Importe total")
ax[1].set_xlabel("Mes")
ax[1].grid(alpha=0.25)

savefig("01_evolucion_mensual.png")


# ---------------------------------------------------------------------
# 2. PERFIL HORARIO
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 2. PERFIL HORARIO")
print("=" * 70)

hour = q(
    f"""
    SELECT
        EXTRACT(HOUR FROM {pickup})::int AS hora,
        COUNT(*) AS viajes,
        AVG(
            EXTRACT(
                EPOCH FROM ({dropoff} - {pickup})
            ) / 60.0
        ) AS duracion_media,
        AVG({total}) AS importe_medio
    FROM {full_table}
    WHERE {valid}
    GROUP BY 1
    ORDER BY 1
    """
)

save_csv(
    hour,
    "02_perfil_horario_python.csv",
)

fig, ax = plt.subplots(figsize=(11, 5))

ax.bar(
    hour["hora"],
    hour["viajes"],
    color="tab:blue",
)

ax.set_title("Demanda por hora")
ax.set_xlabel("Hora")
ax.set_ylabel("Viajes")
ax.set_xticks(range(24))
ax.grid(axis="y", alpha=0.25)

savefig("02_demanda_horaria.png")


# ---------------------------------------------------------------------
# 3. RUTAS MÁS FRECUENTES
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 3. RUTAS MÁS FRECUENTES")
print("=" * 70)

routes = q(
    f"""
    SELECT
        {pu} AS pu,
        {do} AS destino,
        COUNT(*) AS viajes,
        AVG({dist}) AS distancia_media,
        AVG({total}) AS importe_medio
    FROM {full_table}
    WHERE {valid}
    GROUP BY 1, 2
    HAVING COUNT(*) >= 500
    ORDER BY viajes DESC
    LIMIT 25
    """
)

save_csv(
    routes,
    "03_top_rutas_python.csv",
)

labels = (
    routes["pu"].astype(str)
    + " → "
    + routes["destino"].astype(str)
)

plt.figure(figsize=(11, 8))

plt.barh(
    labels.iloc[::-1],
    routes["viajes"].iloc[::-1],
    color="tab:orange",
)

plt.title("25 rutas más frecuentes")
plt.xlabel("Viajes")
plt.ylabel("Zona origen → zona destino")

savefig("03_top_rutas.png")


# ---------------------------------------------------------------------
# 4. MAPA DE CALOR DÍA-HORA
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 4. MAPA DE CALOR DÍA-HORA")
print("=" * 70)

heat = q(
    f"""
    SELECT
        EXTRACT(ISODOW FROM {pickup})::int AS dia,
        EXTRACT(HOUR FROM {pickup})::int AS hora,
        COUNT(*) AS viajes
    FROM {full_table}
    WHERE {valid}
    GROUP BY 1, 2
    ORDER BY 1, 2
    """
)

save_csv(
    heat,
    "04_demanda_dia_hora_python.csv",
)

pivot_heat = (
    heat.pivot(
        index="dia",
        columns="hora",
        values="viajes",
    )
    .reindex(
        index=range(1, 8),
        columns=range(24),
        fill_value=0,
    )
    .fillna(0)
)

plt.figure(figsize=(13, 5))

plt.imshow(
    pivot_heat,
    aspect="auto",
    cmap="viridis",
)

plt.colorbar(label="Viajes")

plt.xticks(
    range(24),
    range(24),
)

plt.yticks(
    range(7),
    ["L", "M", "X", "J", "V", "S", "D"],
)

plt.xlabel("Hora")
plt.ylabel("Día")
plt.title("Mapa de calor de demanda")

savefig("04_heatmap_demanda.png")


# ---------------------------------------------------------------------
# 5. MUESTRA PARA MODELOS
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 5. EXTRACCIÓN DE MUESTRA PARA MODELOS")
print("=" * 70)

features = f"""
    {vendor} AS vendor_id,
    COALESCE({passengers}, 1) AS passenger_count,
    {dist} AS trip_distance,
    {pay} AS payment_type,
    {pu} AS pu_location_id,
    {do} AS do_location_id,
    EXTRACT(HOUR FROM {pickup})::int AS hora,
    EXTRACT(ISODOW FROM {pickup})::int AS dia_semana,
    EXTRACT(
        EPOCH FROM ({dropoff} - {pickup})
    ) / 60.0 AS duracion_min,
    {fare} AS fare_amount,
    {tip} AS tip_amount,
    {total} AS total_amount
"""

sample = q(
    f"""
    SELECT {features}
    FROM {full_table}
    TABLESAMPLE SYSTEM ({SAMPLE_PCT})
    REPEATABLE ({SEED})
    WHERE {valid}
    LIMIT {MAX_ROWS}
    """
)

if len(sample) < 5000:
    print(
        "[WARN] TABLESAMPLE devolvió una muestra insuficiente. "
        "Se utiliza una consulta limitada sin TABLESAMPLE."
    )

    sample = q(
        f"""
        SELECT {features}
        FROM {full_table}
        WHERE {valid}
        LIMIT {MAX_ROWS}
        """
    )

if len(sample) < 5000:
    raise RuntimeError(
        f"Muestra insuficiente para modelado: {len(sample)} registros."
    )

print(f"[OK] Muestra de modelado: {len(sample):,} registros")


# ---------------------------------------------------------------------
# 6. MODELO DE REGRESIÓN DE DURACIÓN
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 6. MODELO DE DURACIÓN")
print("=" * 70)

reg_cols = [
    "trip_distance",
    "passenger_count",
    "hora",
    "dia_semana",
    "pu_location_id",
    "do_location_id",
    "vendor_id",
]

reg_data = sample[
    reg_cols + ["duracion_min"]
].dropna().copy()

reg_data = reg_data[
    (reg_data["duracion_min"] > 0)
    & (reg_data["duracion_min"] <= 120)
]

X_reg = reg_data[reg_cols]
y_reg = reg_data["duracion_min"]

Xtr_reg, Xte_reg, ytr_reg, yte_reg = train_test_split(
    X_reg,
    y_reg,
    test_size=0.2,
    random_state=SEED,
)

reg = HistGradientBoostingRegressor(
    max_iter=180,
    max_leaf_nodes=31,
    learning_rate=0.08,
    random_state=SEED,
)

reg.fit(
    Xtr_reg,
    ytr_reg,
)

pred_reg = reg.predict(Xte_reg)

reg_metrics = {
    "MAE": float(
        mean_absolute_error(
            yte_reg,
            pred_reg,
        )
    ),
    "RMSE": float(
        mean_squared_error(
            yte_reg,
            pred_reg,
        ) ** 0.5
    ),
    "R2": float(
        r2_score(
            yte_reg,
            pred_reg,
        )
    ),
    "n": int(len(reg_data)),
}

save_csv(
    pd.DataFrame([reg_metrics]),
    "05_metricas_regresion_duracion_python.csv",
)

plt.figure(figsize=(6, 6))

plt.hexbin(
    yte_reg,
    pred_reg,
    gridsize=45,
    mincnt=1,
    cmap="Blues",
)

upper_limit = min(
    120,
    max(
        float(yte_reg.max()),
        float(np.max(pred_reg)),
    ),
)

plt.plot(
    [0, upper_limit],
    [0, upper_limit],
    "r--",
)

plt.xlim(0, upper_limit)
plt.ylim(0, upper_limit)
plt.xlabel("Duración real (min)")
plt.ylabel("Predicción (min)")
plt.title("Modelo Python: duración del viaje")
plt.colorbar(label="Observaciones")

savefig("05_modelo_duracion.png")


# ---------------------------------------------------------------------
# 7. IMPORTANCIA DE VARIABLES DEL MODELO DE DURACIÓN
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 7. IMPORTANCIA DE VARIABLES")
print("=" * 70)

importance_size = min(
    15000,
    len(Xte_reg),
)

importance_index = Xte_reg.sample(
    n=importance_size,
    random_state=SEED,
).index

importance = permutation_importance(
    reg,
    Xte_reg.loc[importance_index],
    yte_reg.loc[importance_index],
    n_repeats=3,
    random_state=SEED,
    n_jobs=-1,
)

importance_df = pd.DataFrame(
    {
        "variable": reg_cols,
        "importancia": importance.importances_mean,
        "desviacion": importance.importances_std,
    }
).sort_values(
    "importancia",
    ascending=False,
)

save_csv(
    importance_df,
    "06_importancia_duracion_python.csv",
)

plt.figure(figsize=(9, 5))

importance_plot = importance_df.sort_values(
    "importancia",
    ascending=True,
)

plt.barh(
    importance_plot["variable"],
    importance_plot["importancia"],
    color="tab:cyan",
)

plt.title("Importancia por permutación: duración")
plt.xlabel("Disminución media del rendimiento")
plt.ylabel("Variable")

savefig("06_importancia_duracion.png")


# ---------------------------------------------------------------------
# 8. MODELO DE CLASIFICACIÓN DE PROPINA ALTA
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print(" 8. MODELO DE PROPINA ALTA")
print("=" * 70)

card = sample[
    (sample["payment_type"] == 1)
    & (sample["fare_amount"] > 0)
].copy()

card["propina_alta"] = (
    card["tip_amount"] / card["fare_amount"] >= 0.20
).astype(int)

clf_cols = [
    "trip_distance",
    "passenger_count",
    "hora",
    "dia_semana",
    "pu_location_id",
    "do_location_id",
    "vendor_id",
    "fare_amount",
]

card = card[
    clf_cols + ["propina_alta"]
].dropna().copy()

if len(card) < 5000:
    raise RuntimeError(
        f"Muestra insuficiente para clasificación: {len(card)} registros."
    )

if card["propina_alta"].nunique() < 2:
    raise RuntimeError(
        "La variable propina_alta solo contiene una clase."
    )

X_clf = card[clf_cols]
y_clf = card["propina_alta"]

Xtr_clf, Xte_clf, ytr_clf, yte_clf = train_test_split(
    X_clf,
    y_clf,
    test_size=0.2,
    random_state=SEED,
    stratify=y_clf,
)

clf = RandomForestClassifier(
    n_estimators=180,
    max_depth=16,
    min_samples_leaf=20,
    n_jobs=-1,
    class_weight="balanced",
    random_state=SEED,
)

clf.fit(
    Xtr_clf,
    ytr_clf,
)

proba_clf = clf.predict_proba(Xte_clf)[:, 1]

pred_clf = (
    proba_clf >= 0.5
).astype(int)

clf_metrics = {
    "ROC_AUC": float(
        roc_auc_score(
            yte_clf,
            proba_clf,
        )
    ),
    "n": int(len(card)),
    "prevalencia": float(
        y_clf.mean()
    ),
    "accuracy": float(
        np.mean(pred_clf == yte_clf)
    ),
}

save_csv(
    pd.DataFrame([clf_metrics]),
    "07_metricas_clasificacion_propina_python.csv",
)

classification_df = pd.DataFrame(
    classification_report(
        yte_clf,
        pred_clf,
        output_dict=True,
        zero_division=0,
    )
).T.reset_index().rename(
    columns={"index": "clase"}
)

save_csv(
    classification_df,
    "07_reporte_clasificacion_propina_python.csv",
)

ConfusionMatrixDisplay.from_predictions(
    yte_clf,
    pred_clf,
    cmap="Purples",
)

plt.title("Modelo Python: propina ≥ 20 %")

savefig("07_matriz_confusion_propina.png")


# ---------------------------------------------------------------------
# 9. IMPORTANCIA DEL MODELO DE PROPINA
# ---------------------------------------------------------------------

clf_importance = pd.DataFrame(
    {
        "variable": clf_cols,
        "importancia": clf.feature_importances_,
    }
).sort_values(
    "importancia",
    ascending=False,
)

save_csv(
    clf_importance,
    "08_importancia_propina_python.csv",
)

plt.figure(figsize=(9, 5))

clf_importance_plot = clf_importance.sort_values(
    "importancia",
    ascending=True,
)

plt.barh(
    clf_importance_plot["variable"],
    clf_importance_plot["importancia"],
    color="tab:purple",
)

plt.title("Random Forest: importancia para propina alta")
plt.xlabel("Importancia")
plt.ylabel("Variable")

savefig("08_importancia_propina.png")


# ---------------------------------------------------------------------
# 10. RESUMEN JSON
# ---------------------------------------------------------------------

summary = {
    "origen": {
        "motor": "PostgreSQL",
        "tabla": f"{SCHEMA}.{TABLE}",
    },
    "configuracion": {
        "sample_pct": SAMPLE_PCT,
        "max_rows": MAX_ROWS,
        "seed": SEED,
    },
    "datos": {
        "filas_muestra": int(len(sample)),
        "filas_regresion": int(len(reg_data)),
        "filas_clasificacion": int(len(card)),
    },
    "regresion_duracion": reg_metrics,
    "clasificacion_propina": clf_metrics,
}

json_file = JSON_DIR / "00_resumen_python.json"

with open(
    json_file,
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False,
        default=float,
    )

print(f"[OK] JSON guardado: {json_file}")


# ---------------------------------------------------------------------
# FINALIZACIÓN
# ---------------------------------------------------------------------

engine.dispose()

print("\n" + "=" * 70)
print(" ANÁLISIS PYTHON FINALIZADO")
print("=" * 70)

print("[OK] CSVs     :", CSV_DIR.resolve())
print("[OK] JSON     :", JSON_DIR.resolve())
print("[OK] Gráficos :", GRAFICOS_DIR.resolve())
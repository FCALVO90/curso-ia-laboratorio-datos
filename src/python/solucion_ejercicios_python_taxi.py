#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOLUCION UNICA P1-P8 - NYC YELLOW TAXI 2024
============================================
Resuelve en un solo script los ejercicios Python/Spyder P1 a P8.

Proyecto esperado:
    ~/curso_ia
Datos:
    ~/curso_ia/datos/raw/taxi/
Salidas:
    ~/curso_ia/resultados/python_taxi/

Uso:
    python src/python/solucion_ejercicios_python_taxi.py

Opciones:
    python src/python/solucion_ejercicios_python_taxi.py --mes 01
    python src/python/solucion_ejercicios_python_taxi.py --solo P1 P2 P3
    python src/python/solucion_ejercicios_python_taxi.py --muestra-modelo 100000

Dependencias:
    pip install pandas pyarrow matplotlib seaborn geopandas mapclassify folium scikit-learn scipy
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
import tracemalloc
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 180)
sns.set_theme(style="whitegrid")

# ============================================================
# 0. CONFIGURACION
# ============================================================
HOME = Path.home()
PROYECTO = HOME / "curso_ia"
DATA_DIR = PROYECTO / "datos" / "raw" / "taxi"
LOOKUP = DATA_DIR / "taxi_zone_lookup.csv"
ZONAS_DIR = DATA_DIR / "zonas"
# ============================================================
# CARPETAS DE SALIDA
# ============================================================
SALIDAS_DIR = PROYECTO / "salidas" / "taxi" / "python"

CSV_DIR = SALIDAS_DIR / "csv"
GRAFICOS_DIR = SALIDAS_DIR / "graficos"
JSON_DIR = SALIDAS_DIR / "json"
HTML_DIR = SALIDAS_DIR / "html"

for directorio in (CSV_DIR, GRAFICOS_DIR, JSON_DIR, HTML_DIR):
    directorio.mkdir(parents=True, exist_ok=True)

COLUMNAS = [
    "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "passenger_count", "trip_distance", "RatecodeID",
    "store_and_fwd_flag", "PULocationID", "DOLocationID",
    "payment_type", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "improvement_surcharge",
    "total_amount", "congestion_surcharge", "Airport_fee"
]


def titulo(texto: str) -> None:
    print("\n" + "=" * 78)
    print(f" {texto}")
    print("=" * 78)


def guardar_csv(df: pd.DataFrame, nombre: str, index: bool = False) -> None:
    ruta = CSV_DIR / nombre
    df.to_csv(ruta, index=index)
    print(f"[OK] CSV guardado: {ruta}")


def guardar_fig(fig, nombre: str) -> None:
    ruta = GRAFICOS_DIR / nombre
    fig.savefig(ruta, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Figura guardada: {ruta}")


def localizar_shapefile() -> Path | None:
    candidatos = list(DATA_DIR.rglob("*.shp"))
    return candidatos[0] if candidatos else None


def cargar_mes(mes: str) -> pd.DataFrame:
    ruta = DATA_DIR / f"yellow_tripdata_2024-{mes}.parquet"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe: {ruta}")
    inicio = time.perf_counter()
    df = pd.read_parquet(ruta)
    print(f"[OK] {ruta.name}: {len(df):,} filas en {time.perf_counter()-inicio:.2f} s")
    return df


def preparar_variables(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["tpep_pickup_datetime"] = pd.to_datetime(d["tpep_pickup_datetime"], errors="coerce")
    d["tpep_dropoff_datetime"] = pd.to_datetime(d["tpep_dropoff_datetime"], errors="coerce")
    d["duracion_min"] = (d["tpep_dropoff_datetime"] - d["tpep_pickup_datetime"]).dt.total_seconds() / 60
    d["velocidad_mph"] = np.where(d["duracion_min"] > 0, d["trip_distance"] / (d["duracion_min"] / 60), np.nan)
    d["fecha"] = d["tpep_pickup_datetime"].dt.date
    d["hora"] = d["tpep_pickup_datetime"].dt.hour
    d["dia_semana_num"] = d["tpep_pickup_datetime"].dt.dayofweek
    dias = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes",5:"Sabado",6:"Domingo"}
    d["dia_semana"] = d["dia_semana_num"].map(dias)
    d["fin_semana"] = d["dia_semana_num"] >= 5
    return d


def filtro_validos(df: pd.DataFrame, mes: str) -> pd.Series:
    inicio = pd.Timestamp(f"2024-{mes}-01")
    fin = inicio + pd.offsets.MonthBegin(1)
    return (
        df["tpep_pickup_datetime"].between(inicio, fin, inclusive="left")
        & (df["tpep_dropoff_datetime"] > df["tpep_pickup_datetime"])
        & (df["duracion_min"] > 0) & (df["duracion_min"] <= 24 * 60)
        & (df["trip_distance"] > 0)
        & (df["fare_amount"] > 0)
        & (df["total_amount"] > 0)
    )


# ============================================================
# P1. LECTURA, TIPOS, MEMORIA Y GROUPBY
# ============================================================
def ejercicio_p1(df: pd.DataFrame, mes: str) -> None:
    titulo("P1 - DESCARGAR, LEER Y MIRAR EL DATO")
    print(f"Dimensiones: {df.shape[0]:,} filas x {df.shape[1]} columnas")
    print("\nTipos:\n", df.dtypes)
    memoria = df.memory_usage(deep=True).sum() / 1024**2
    print(f"\nMemoria profunda: {memoria:,.2f} MB")
    resumen = (df.groupby("payment_type", dropna=False)
                 .agg(viajes=("payment_type", "size"),
                      distancia_media=("trip_distance", "mean"),
                      importe_medio=("total_amount", "mean"))
                 .reset_index())
    print("\nResumen por tipo de pago:\n", resumen.to_string(index=False))
    guardar_csv(resumen, f"P1_resumen_pago_2024-{mes}.csv")

    ruta = DATA_DIR / f"yellow_tripdata_2024-{mes}.parquet"
    cols = ["tpep_pickup_datetime", "trip_distance", "payment_type", "tip_amount", "total_amount"]
    t0 = time.perf_counter(); parcial = pd.read_parquet(ruta, columns=cols); t1 = time.perf_counter()
    print(f"[EXTRA] Lectura de 5 columnas: {t1-t0:.2f} s; memoria {parcial.memory_usage(deep=True).sum()/1024**2:.2f} MB")
    del parcial


# ============================================================
# P2. CALIDAD, CATEGORICAS Y VIAJES VALIDOS
# ============================================================
def ejercicio_p2(df: pd.DataFrame, mes: str) -> pd.DataFrame:
    titulo("P2 - CALIDAD DEL DATO CON PANDAS")
    d = preparar_variables(df)
    calidad = pd.DataFrame({"nulos": d.isna().sum(), "porcentaje": d.isna().mean().mul(100)}).sort_values("nulos", ascending=False)
    print("\nNulos:\n", calidad[calidad.nulos > 0].to_string())

    anomalias = pd.Series({
        "pasajeros_0_o_na": ((d["passenger_count"] == 0) | d["passenger_count"].isna()).sum(),
        "distancia_no_positiva": (d["trip_distance"] <= 0).sum(),
        "tarifa_no_positiva": (d["fare_amount"] <= 0).sum(),
        "importe_no_positivo": (d["total_amount"] <= 0).sum(),
        "duracion_no_positiva": (d["duracion_min"] <= 0).sum(),
        "duracion_mayor_24h": (d["duracion_min"] > 1440).sum(),
    }, name="casos").to_frame()
    print("\nAnomalias:\n", anomalias.to_string())
    guardar_csv(calidad.reset_index(names="columna"), f"P2_calidad_2024-{mes}.csv")
    guardar_csv(anomalias.reset_index(names="regla"), f"P2_anomalias_2024-{mes}.csv")

    antes = d.memory_usage(deep=True).sum()
    optimizado = d.copy()
    for c in ["VendorID", "RatecodeID", "store_and_fwd_flag", "payment_type"]:
        optimizado[c] = optimizado[c].astype("category")
    despues = optimizado.memory_usage(deep=True).sum()
    print(f"\nMemoria antes: {antes/1024**2:.2f} MB")
    print(f"Memoria despues: {despues/1024**2:.2f} MB")
    print(f"Ahorro: {(1-despues/antes)*100:.2f}%")
    mask = filtro_validos(d, mes)
    validos = d.loc[mask].copy()
    print(f"Viajes validos: {len(validos):,}; descartados: {(~mask).sum():,} ({(~mask).mean()*100:.2f}%)")
    return validos


# ============================================================
# P3. FIGURA 2x2
# ============================================================
def ejercicio_p3(v: pd.DataFrame, mes: str) -> None:
    titulo("P3 - VISUALIZACION CON MATPLOTLIB Y SEABORN")
    muestra = v.sample(min(150_000, len(v)), random_state=42)
    dist_tope = v["trip_distance"].quantile(.995)
    importe_tope = v["total_amount"].quantile(.99)
    plot = muestra[(muestra.trip_distance <= dist_tope) & (muestra.total_amount <= importe_tope)]
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))
    ax[0,0].hist(plot.trip_distance, bins=60, log=True, color="#D9491A")
    ax[0,0].set(title="Distancia de viaje", xlabel="Millas", ylabel="Frecuencia log")
    sns.boxplot(data=plot, x="payment_type", y="total_amount", ax=ax[0,1], showfliers=False)
    ax[0,1].set(title="Importe por tipo de pago", xlabel="Tipo de pago", ylabel="Importe total ($)")
    sns.violinplot(data=plot.sample(min(40_000, len(plot)), random_state=42), x="payment_type", y="total_amount", ax=ax[1,0], cut=0)
    ax[1,0].set(title="Distribucion del importe", xlabel="Tipo de pago", ylabel="Importe total ($)")
    hb = ax[1,1].hexbin(plot.trip_distance, plot.fare_amount, gridsize=60, bins="log", mincnt=1, cmap="viridis")
    fig.colorbar(hb, ax=ax[1,1], label="log10(numero de viajes)")
    ax[1,1].set(title="Distancia frente a tarifa", xlabel="Millas", ylabel="Tarifa ($)")
    fig.tight_layout()
    guardar_fig(fig, f"P3_panel_exploratorio_2024-{mes}.png")


# ============================================================
# P4. SERIES TEMPORALES
# ============================================================
def ejercicio_p4(v: pd.DataFrame, mes: str) -> None:
    titulo("P4 - SERIES TEMPORALES CON RESAMPLE")
    ts = v.set_index("tpep_pickup_datetime").sort_index()
    por_hora = ts.resample("h").size().rename("viajes")
    por_dia = ts.resample("D").size().rename("viajes")
    media24 = por_hora.rolling(24, min_periods=1).mean()
    perfil = (v.assign(tipo_dia=np.where(v.fin_semana, "Fin de semana", "Laborable"))
                .groupby(["tipo_dia", "hora"]).size().rename("viajes").reset_index())
    fig, ax = plt.subplots(3, 1, figsize=(14, 12))
    ax[0].plot(por_hora.index, por_hora.values, alpha=.45, label="Viajes/hora")
    ax[0].plot(media24.index, media24.values, linewidth=2, label="Media movil 24 h")
    ax[0].legend(); ax[0].set_title("Demanda horaria")
    ax[1].plot(por_dia.index, por_dia.values, marker="o"); ax[1].set_title("Viajes diarios")
    sns.lineplot(data=perfil, x="hora", y="viajes", hue="tipo_dia", marker="o", ax=ax[2])
    ax[2].set_title("Perfil horario: laborable frente a fin de semana")
    fig.tight_layout(); guardar_fig(fig, f"P4_series_temporales_2024-{mes}.png")
    guardar_csv(por_dia.reset_index(), f"P4_viajes_diarios_2024-{mes}.csv")


# ============================================================
# P5. MERGE, RUTAS, PIVOT Y HEATMAP
# ============================================================
def enriquecer_zonas(v: pd.DataFrame) -> pd.DataFrame:
    if not LOOKUP.exists():
        raise FileNotFoundError(f"No existe {LOOKUP}")
    z = pd.read_csv(LOOKUP)
    pu = z.rename(columns={"LocationID":"PULocationID", "Borough":"borough_origen", "Zone":"zona_origen", "service_zone":"service_origen"})
    do = z.rename(columns={"LocationID":"DOLocationID", "Borough":"borough_destino", "Zone":"zona_destino", "service_zone":"service_destino"})
    return v.merge(pu, on="PULocationID", how="left").merge(do, on="DOLocationID", how="left")


def ejercicio_p5(v: pd.DataFrame, mes: str) -> pd.DataFrame:
    titulo("P5 - CRUCE CON ZONAS")
    vz = enriquecer_zonas(v)
    rutas = (vz.groupby(["borough_origen","zona_origen","borough_destino","zona_destino"], dropna=False)
               .agg(viajes=("total_amount","size"), importe_medio=("total_amount","mean"))
               .nlargest(15, "viajes").reset_index())
    matriz = pd.pivot_table(vz, index="borough_origen", columns="borough_destino", values="total_amount", aggfunc="size", fill_value=0)
    top_zonas = vz.groupby("zona_origen").size().nlargest(15).sort_values()
    print("\nTop 15 rutas:\n", rutas.to_string(index=False))
    guardar_csv(rutas, f"P5_top_rutas_2024-{mes}.csv")
    guardar_csv(matriz.reset_index(), f"P5_matriz_boroughs_2024-{mes}.csv")
    fig, ax = plt.subplots(1, 2, figsize=(16, 7))
    sns.heatmap(matriz, annot=True, fmt="g", cmap="YlOrRd", ax=ax[0])
    ax[0].set_title("Borough origen x destino")
    top_zonas.plot.barh(ax=ax[1], color="#D9491A"); ax[1].set_title("Zonas con mas recogidas")
    fig.tight_layout(); guardar_fig(fig, f"P5_zonas_y_boroughs_2024-{mes}.png")
    mismo = (vz.PULocationID == vz.DOLocationID).mean() * 100
    print(f"[EXTRA] Viajes con origen y destino en la misma zona: {mismo:.2f}%")
    return vz


# ============================================================
# P6. MAPAS GEOPANDAS
# ============================================================
def ejercicio_p6(vz: pd.DataFrame, mes: str) -> None:
    titulo("P6 - MAPAS CON GEOPANDAS")
    shp = localizar_shapefile()
    if shp is None:
        print("[AVISO] No se encontro un .shp bajo datos/raw/taxi. Se omite P6.")
        return
    try:
        import geopandas as gpd
        zonas = gpd.read_file(shp)
        id_geo = next((c for c in ["LocationID", "location_i", "OBJECTID"] if c in zonas.columns), None)
        if id_geo is None:
            raise KeyError(f"No se localiza el ID de zona. Columnas: {zonas.columns.tolist()}")
        agg = (vz.groupby("PULocationID")
                .agg(viajes=("total_amount","size"), propina_media=("tip_amount","mean"), tarifa_media=("fare_amount","mean"))
                .reset_index())
        agg["tip_pct"] = np.where(agg.tarifa_media > 0, 100*agg.propina_media/agg.tarifa_media, np.nan)
        mapa = zonas.merge(agg, left_on=id_geo, right_on="PULocationID", how="left")
        print(f"CRS original: {mapa.crs}")
        fig, ax = plt.subplots(1, 2, figsize=(16, 8))
        mapa.plot(column="viajes", scheme="quantiles", k=5, legend=True, cmap="YlOrRd", ax=ax[0], missing_kwds={"color":"lightgrey"})
        mapa.plot(column="tip_pct", scheme="quantiles", k=5, legend=True, cmap="viridis", ax=ax[1], missing_kwds={"color":"lightgrey"})
        ax[0].set_title("Viajes por zona"); ax[1].set_title("Propina media (%)")
        for a in ax: a.set_axis_off()
        fig.tight_layout(); guardar_fig(fig, f"P6_mapas_estaticos_2024-{mes}.png")
        mapa4326 = mapa.to_crs(4326)
        try:
            interactivo = mapa4326.explore(column="viajes", cmap="YlOrRd", tooltip=[id_geo, "viajes", "tip_pct"], legend=True)
            ruta_html = HTML_DIR / f"P6_mapa_interactivo_2024-{mes}.html"
            interactivo.save(ruta_html); print(f"[OK] Mapa interactivo: {ruta_html}")
        except Exception as exc:
            print(f"[AVISO] No se pudo crear el mapa interactivo: {exc}")
    except Exception as exc:
        print(f"[AVISO] P6 omitido por dependencia/dato geografico: {exc}")


# ============================================================
# P7. MODELOS DE PROPINAS
# ============================================================
def ejercicio_p7(vz: pd.DataFrame, mes: str, n_muestra: int) -> None:
    titulo("P7 - PREDECIR LA PROPINAS CON SCIKIT-LEARN")
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import HistGradientBoostingRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.inspection import permutation_importance
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler

        d = vz[(vz.payment_type == 1) & (vz.fare_amount > 0)].copy()
        d["tip_pct"] = 100 * d.tip_amount / d.fare_amount
        d = d[d.tip_pct.between(0, 100)]
        d["aeropuerto"] = d["zona_origen"].fillna("").str.contains("Airport", case=False)
        num = ["hora", "trip_distance", "duracion_min", "passenger_count", "fare_amount"]
        cat = ["fin_semana", "borough_origen", "aeropuerto"]
        d = d[num + cat + ["tip_pct"]].replace([np.inf, -np.inf], np.nan)
        d = d.sample(min(n_muestra, len(d)), random_state=42)
        X, y = d[num + cat], d["tip_pct"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)
        prep = ColumnTransformer([
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), num),
            ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), cat)
        ])
        modelos = {
            "Regresion lineal": LinearRegression(),
            "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=180, learning_rate=.08, random_state=42)
        }
        filas, predicciones = [], {}
        for nombre, modelo in modelos.items():
            pipe = Pipeline([("prep", prep), ("modelo", modelo)])
            cv_rmse = -cross_val_score(pipe, X_train, y_train, cv=3, scoring="neg_root_mean_squared_error", n_jobs=-1).mean()
            pipe.fit(X_train, y_train)
            pred = pipe.predict(X_test)
            filas.append({"modelo":nombre, "cv_rmse":cv_rmse, "test_rmse":mean_squared_error(y_test, pred)**.5, "test_r2":r2_score(y_test, pred)})
            predicciones[nombre] = (pipe, pred)
        metricas = pd.DataFrame(filas)
        print(metricas.to_string(index=False)); guardar_csv(metricas, f"P7_metricas_2024-{mes}.csv")
        mejor_nombre = metricas.sort_values("test_rmse").iloc[0]["modelo"]
        mejor_pipe, pred = predicciones[mejor_nombre]
        # Permutacion sobre variables originales para interpretacion compacta
        imp = permutation_importance(mejor_pipe, X_test.sample(min(5000,len(X_test)), random_state=42), y_test.loc[X_test.sample(min(5000,len(X_test)), random_state=42).index], n_repeats=3, random_state=42, scoring="neg_root_mean_squared_error")
        importancia = pd.Series(imp.importances_mean, index=X.columns).sort_values()
        fig, ax = plt.subplots(1, 3, figsize=(18, 5))
        ax[0].scatter(y_test, pred, s=7, alpha=.2); ax[0].plot([0,100],[0,100], "r--"); ax[0].set(title=f"Real vs predicho: {mejor_nombre}", xlabel="Real (%)", ylabel="Predicho (%)")
        resid = y_test.to_numpy() - pred
        ax[1].scatter(pred, resid, s=7, alpha=.2); ax[1].axhline(0, color="r", ls="--"); ax[1].set(title="Residuos", xlabel="Predicho", ylabel="Residuo")
        importancia.plot.barh(ax=ax[2]); ax[2].set_title("Importancia por permutacion")
        fig.tight_layout(); guardar_fig(fig, f"P7_diagnostico_modelo_2024-{mes}.png")
    except Exception as exc:
        print(f"[AVISO] P7 no pudo finalizar: {exc}")


# ============================================================
# P8. ANO COMPLETO POR LOTES Y PANEL
# ============================================================
def ejercicio_p8() -> None:
    titulo("P8 - GRAN VOLUMEN Y PANEL ANUAL")
    archivos = sorted(DATA_DIR.glob("yellow_tripdata_2024-*.parquet"))
    if not archivos:
        print("[AVISO] No hay ficheros mensuales.")
        return
    tracemalloc.start()
    resultados = []
    for ruta in archivos:
        mes = ruta.stem[-2:]
        acumulados = {"viajes":0, "tip_sum":0.0, "tip_n":0, "vel_sum":0.0, "vel_n":0, "importe_sum":0.0}
        pf = pq.ParquetFile(ruta)
        cols = ["tpep_pickup_datetime","tpep_dropoff_datetime","trip_distance","tip_amount","total_amount","fare_amount"]
        for batch in pf.iter_batches(batch_size=250_000, columns=cols):
            b = batch.to_pandas()
            dur_h = (b.tpep_dropoff_datetime - b.tpep_pickup_datetime).dt.total_seconds()/3600
            ok = (dur_h > 0) & (dur_h <= 24) & (b.trip_distance > 0) & (b.fare_amount > 0) & (b.total_amount > 0)
            x = b.loc[ok]
            vel = x.trip_distance / dur_h.loc[ok]
            vel = vel[vel.between(0, 100)]
            acumulados["viajes"] += len(x)
            acumulados["tip_sum"] += x.tip_amount.sum(); acumulados["tip_n"] += x.tip_amount.notna().sum()
            acumulados["vel_sum"] += vel.sum(); acumulados["vel_n"] += vel.notna().sum()
            acumulados["importe_sum"] += x.total_amount.sum()
            del b, x, vel
        resultados.append({
            "mes":mes, "viajes":acumulados["viajes"],
            "propina_media":acumulados["tip_sum"]/max(acumulados["tip_n"],1),
            "velocidad_media_mph":acumulados["vel_sum"]/max(acumulados["vel_n"],1),
            "importe_medio":acumulados["importe_sum"]/max(acumulados["viajes"],1)
        })
        print(f"[OK] Mes {mes} procesado por lotes")
    actual, pico = tracemalloc.get_traced_memory(); tracemalloc.stop()
    anual = pd.DataFrame(resultados).sort_values("mes")
    med = anual["viajes"].median(); mad = np.median(np.abs(anual["viajes"]-med))
    anual["z_robusto_viajes"] = 0.6745*(anual["viajes"]-med)/mad if mad else 0
    anual["mes_atipico"] = anual["z_robusto_viajes"].abs() > 3.5
    guardar_csv(anual, "P8_resumen_anual_2024.csv")
    print(anual.to_string(index=False)); print(f"Pico aproximado medido por tracemalloc: {pico/1024**2:.2f} MB")
    fig = plt.figure(figsize=(15, 10)); gs = fig.add_gridspec(2, 2)
    variables = [("viajes","Viajes validos"),("propina_media","Propina media ($)"),("velocidad_media_mph","Velocidad media (mph)"),("importe_medio","Importe medio ($)")]
    for i,(col,tit) in enumerate(variables):
        ax = fig.add_subplot(gs[i//2, i%2]); ax.plot(anual.mes, anual[col], marker="o", color="#D9491A"); ax.set_title(tit); ax.set_xlabel("Mes")
    fig.tight_layout(); guardar_fig(fig, "P8_panel_anual_2024.png")
    # Hallazgos calculados, no prefabricados
    hallazgos = {
        "mes_mas_viajes": anual.loc[anual.viajes.idxmax(), "mes"],
        "mes_mayor_propina_media": anual.loc[anual.propina_media.idxmax(), "mes"],
        "mes_mayor_velocidad_media": anual.loc[anual.velocidad_media_mph.idxmax(), "mes"],
        "meses_atipicos": anual.loc[anual.mes_atipico, "mes"].tolist()
    }
    (JSON_DIR / "P8_hallazgos.json").write_text(json.dumps(hallazgos, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Hallazgos:", json.dumps(hallazgos, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Solucion unica ejercicios P1-P8 NYC Taxi")
    parser.add_argument("--mes", default="01", choices=[f"{m:02d}" for m in range(1,13)])
    parser.add_argument("--solo", nargs="*", default=[f"P{i}" for i in range(1,9)], choices=[f"P{i}" for i in range(1,9)])
    parser.add_argument("--muestra-modelo", type=int, default=100_000)
    args = parser.parse_args()
    titulo("INICIO - SOLUCION EJERCICIOS PYTHON NYC TAXI")
    print(f"Datos: {DATA_DIR}")
    print(f"CSV: {CSV_DIR}")
    print(f"Graficos: {GRAFICOS_DIR}")
    print(f"JSON: {JSON_DIR}")
    print(f"HTML: {HTML_DIR}")
    print(f"Ejercicios: {', '.join(args.solo)}")
    if not DATA_DIR.exists():
        sys.exit(f"[ERROR] No existe {DATA_DIR}")
    necesita_mes = any(p in args.solo for p in ["P1","P2","P3","P4","P5","P6","P7"])
    df = cargar_mes(args.mes) if necesita_mes else None
    validos = None; vz = None
    if "P1" in args.solo: ejercicio_p1(df, args.mes)
    if any(p in args.solo for p in ["P2","P3","P4","P5","P6","P7"]): validos = ejercicio_p2(df, args.mes)
    if "P3" in args.solo: ejercicio_p3(validos, args.mes)
    if "P4" in args.solo: ejercicio_p4(validos, args.mes)
    if any(p in args.solo for p in ["P5","P6","P7"]): vz = ejercicio_p5(validos, args.mes)
    if "P6" in args.solo: ejercicio_p6(vz, args.mes)
    if "P7" in args.solo: ejercicio_p7(vz, args.mes, max(5_000, args.muestra_modelo))
    if "P8" in args.solo: ejercicio_p8()
    del df, validos, vz
    gc.collect()
    titulo("FIN - TODOS LOS EJERCICIOS SOLICITADOS HAN TERMINADO")
    print(f"CSV generados: {CSV_DIR}")
    print(f"Graficos generados: {GRAFICOS_DIR}")
    print(f"JSON generados: {JSON_DIR}")
    print(f"HTML generados: {HTML_DIR}")


if __name__ == "__main__":
    main()

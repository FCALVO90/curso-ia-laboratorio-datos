#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Análisis exploratorio de datos de calidad del aire de Madrid.

ENTRADA
-------
datos/processed/aire_madrid/calidad_aire_madrid_procesado.csv

SALIDAS
-------
salidas/aire_madrid/python/csv/
salidas/aire_madrid/python/graficos/
salidas/aire_madrid/python/json/
salidas/aire_madrid/python/logs/

CRITERIOS
---------
- Se trabaja exclusivamente con el dataset procesado.
- No se modifica el fichero de entrada.
- Las magnitudes se analizan separadamente cuando tienen escalas distintas.
- Los posibles atípicos IQR se conservan y se estudian.
- Los gráficos se guardan en PNG.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

PROYECTO = Path.home() / "curso_ia"

PROCESSED = (
    PROYECTO
    / "datos"
    / "processed"
    / "aire_madrid"
    / "calidad_aire_madrid_procesado.csv"
)

SALIDA_BASE = (
    PROYECTO
    / "salidas"
    / "aire_madrid"
    / "python"
)

CSV_DIR = SALIDA_BASE / "csv"
GRAFICOS_DIR = SALIDA_BASE / "graficos"
JSON_DIR = SALIDA_BASE / "json"
LOG_DIR = SALIDA_BASE / "logs"

LOG_FILE = (
    LOG_DIR
    / "04_analizar_calidad_aire_madrid.log"
)

DPI = 180


# =============================================================================
# FUNCIONES GENERALES
# =============================================================================

def crear_directorios() -> None:
    """Crea únicamente los directorios de salida necesarios."""

    for directorio in [
        CSV_DIR,
        GRAFICOS_DIR,
        JSON_DIR,
        LOG_DIR,
    ]:
        directorio.mkdir(
            parents=True,
            exist_ok=True,
        )


def configurar_logging() -> logging.Logger:
    """Configura trazas por terminal y fichero."""

    logger = logging.getLogger(
        "eda_aire_madrid"
    )

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    consola = logging.StreamHandler(
        sys.stdout
    )
    consola.setFormatter(
        formato
    )

    fichero = logging.FileHandler(
        LOG_FILE,
        mode="w",
        encoding="utf-8",
    )
    fichero.setFormatter(
        formato
    )

    logger.addHandler(
        consola
    )
    logger.addHandler(
        fichero
    )

    return logger


def sha256_fichero(ruta: Path) -> str:
    """Calcula el SHA256 del dataset de entrada."""

    calculador = hashlib.sha256()

    with ruta.open("rb") as fichero:

        while True:

            bloque = fichero.read(
                1024 * 1024
            )

            if not bloque:
                break

            calculador.update(
                bloque
            )

    return calculador.hexdigest()


def guardar_csv(
    dataframe: pd.DataFrame,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Guarda una tabla de resultados en CSV."""

    ruta = CSV_DIR / nombre

    dataframe.to_csv(
        ruta,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d",
    )

    logger.info(
        "CSV generado: %s",
        ruta,
    )


def guardar_json(
    contenido: dict,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Guarda un resumen en JSON."""

    ruta = JSON_DIR / nombre

    with ruta.open(
        "w",
        encoding="utf-8",
    ) as fichero:

        json.dump(
            contenido,
            fichero,
            ensure_ascii=False,
            indent=4,
            default=str,
        )

    logger.info(
        "JSON generado: %s",
        ruta,
    )


def guardar_grafico(
    figura: plt.Figure,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Ajusta, guarda y cierra un gráfico."""

    ruta = GRAFICOS_DIR / nombre

    figura.savefig(
        ruta,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(
        figura
    )

    logger.info(
        "Gráfico generado: %s",
        ruta,
    )


def convertir_booleano(serie: pd.Series) -> pd.Series:
    """Convierte la representación textual del booleano."""

    resultado = (
        serie.astype("string")
        .str.strip()
        .str.lower()
        .map(
            {
                "true": True,
                "false": False,
                "1": True,
                "0": False,
            }
        )
    )

    return resultado.astype(
        "boolean"
    )


def aplicar_formato_ejes(eje: plt.Axes) -> None:
    """Aplica una rejilla discreta y elimina bordes innecesarios."""

    eje.grid(
        axis="y",
        alpha=0.25,
    )

    eje.spines[
        "top"
    ].set_visible(False)

    eje.spines[
        "right"
    ].set_visible(False)


# =============================================================================
# CARGA Y VALIDACIÓN MÍNIMA
# =============================================================================

def cargar_datos(
    logger: logging.Logger,
) -> pd.DataFrame:
    """Carga exclusivamente el fichero procesado."""

    if not PROCESSED.exists():

        raise FileNotFoundError(
            f"No existe el fichero procesado: {PROCESSED}"
        )

    logger.info(
        "Leyendo dataset procesado: %s",
        PROCESSED,
    )

    datos = pd.read_csv(
        PROCESSED,
        dtype={
            "provincia": "string",
            "municipio": "string",
            "estacion": "Int64",
            "magnitud": "Int64",
            "punto_muestreo": "string",
            "anio": "Int64",
            "mes": "Int64",
            "dia": "Int64",
            "indicador_validez": "string",
        },
    )

    datos["fecha"] = pd.to_datetime(
        datos["fecha"],
        errors="coerce",
    )

    datos["valor"] = pd.to_numeric(
        datos["valor"],
        errors="coerce",
    )

    datos["es_atipico_iqr"] = convertir_booleano(
        datos["es_atipico_iqr"]
    )

    if datos["fecha"].isna().any():

        raise ValueError(
            "Existen fechas inválidas en el procesado."
        )

    if datos["valor"].isna().any():

        raise ValueError(
            "Existen valores no numéricos en el procesado."
        )

    if datos["es_atipico_iqr"].isna().any():

        raise ValueError(
            "Existen indicadores de atípicos no interpretables."
        )

    logger.info(
        "Registros cargados: %s",
        len(datos),
    )

    logger.info(
        "Periodo: %s -> %s",
        datos["fecha"].min().date(),
        datos["fecha"].max().date(),
    )

    return datos


# =============================================================================
# TABLAS DEL EDA
# =============================================================================

def crear_tablas(
    datos: pd.DataFrame,
    logger: logging.Logger,
) -> dict[str, pd.DataFrame]:
    """Construye las tablas descriptivas principales."""

    logger.info(
        "Calculando tablas del análisis exploratorio..."
    )

    # -------------------------------------------------------------------------
    # 31. DESCRIPTIVOS POR MAGNITUD
    # -------------------------------------------------------------------------

    descriptivos = (
        datos.groupby(
            "magnitud",
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            estaciones=("estacion", "nunique"),
            puntos_muestreo=("punto_muestreo", "nunique"),
            media=("valor", "mean"),
            desviacion=("valor", "std"),
            minimo=("valor", "min"),
            q1=("valor", lambda serie: serie.quantile(0.25)),
            mediana=("valor", "median"),
            q3=("valor", lambda serie: serie.quantile(0.75)),
            maximo=("valor", "max"),
            atipicos_iqr=("es_atipico_iqr", "sum"),
        )
        .reset_index()
        .sort_values("magnitud")
    )

    descriptivos["porcentaje_atipicos"] = (
        descriptivos["atipicos_iqr"]
        / descriptivos["registros"]
        * 100
    )

    columnas_redondeo = [
        "media",
        "desviacion",
        "minimo",
        "q1",
        "mediana",
        "q3",
        "maximo",
        "porcentaje_atipicos",
    ]

    descriptivos[columnas_redondeo] = (
        descriptivos[columnas_redondeo]
        .round(4)
    )

    guardar_csv(
        descriptivos,
        "31_descriptivos_por_magnitud.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 32. EVOLUCIÓN MENSUAL POR MAGNITUD
    # -------------------------------------------------------------------------

    mensual = (
        datos.groupby(
            [
                "anio",
                "mes",
                "magnitud",
            ],
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            estaciones=("estacion", "nunique"),
            media=("valor", "mean"),
            mediana=("valor", "median"),
            minimo=("valor", "min"),
            maximo=("valor", "max"),
            atipicos_iqr=("es_atipico_iqr", "sum"),
        )
        .reset_index()
        .sort_values(
            [
                "magnitud",
                "anio",
                "mes",
            ]
        )
    )

    mensual[
        [
            "media",
            "mediana",
            "minimo",
            "maximo",
        ]
    ] = (
        mensual[
            [
                "media",
                "mediana",
                "minimo",
                "maximo",
            ]
        ]
        .round(4)
    )

    guardar_csv(
        mensual,
        "32_evolucion_mensual.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 33. EVOLUCIÓN DIARIA POR MAGNITUD
    # -------------------------------------------------------------------------

    diaria = (
        datos.groupby(
            [
                "fecha",
                "magnitud",
            ],
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            estaciones=("estacion", "nunique"),
            media=("valor", "mean"),
            mediana=("valor", "median"),
            minimo=("valor", "min"),
            maximo=("valor", "max"),
        )
        .reset_index()
        .sort_values(
            [
                "magnitud",
                "fecha",
            ]
        )
    )

    diaria[
        [
            "media",
            "mediana",
            "minimo",
            "maximo",
        ]
    ] = (
        diaria[
            [
                "media",
                "mediana",
                "minimo",
                "maximo",
            ]
        ]
        .round(4)
    )

    guardar_csv(
        diaria,
        "33_evolucion_diaria.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 34. RESUMEN DE ESTACIONES
    # -------------------------------------------------------------------------

    estaciones = (
        datos.groupby(
            "estacion",
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            magnitudes=("magnitud", "nunique"),
            puntos_muestreo=("punto_muestreo", "nunique"),
            primera_fecha=("fecha", "min"),
            ultima_fecha=("fecha", "max"),
            atipicos_iqr=("es_atipico_iqr", "sum"),
        )
        .reset_index()
        .sort_values(
            [
                "registros",
                "estacion",
            ],
            ascending=[
                False,
                True,
            ],
        )
    )

    estaciones["porcentaje_atipicos"] = (
        estaciones["atipicos_iqr"]
        / estaciones["registros"]
        * 100
    ).round(4)

    guardar_csv(
        estaciones,
        "34_resumen_estaciones.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 35. ATÍPICOS POR MAGNITUD
    # -------------------------------------------------------------------------

    atipicos = (
        datos.groupby(
            "magnitud",
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            atipicos=("es_atipico_iqr", "sum"),
        )
        .reset_index()
        .sort_values("magnitud")
    )

    atipicos["no_atipicos"] = (
        atipicos["registros"]
        - atipicos["atipicos"]
    )

    atipicos["porcentaje_atipicos"] = (
        atipicos["atipicos"]
        / atipicos["registros"]
        * 100
    ).round(4)

    guardar_csv(
        atipicos,
        "35_atipicos_por_magnitud.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 36. RANKING ESTACIÓN-MAGNITUD
    # -------------------------------------------------------------------------

    ranking = (
        datos.groupby(
            [
                "magnitud",
                "estacion",
            ],
            dropna=False,
        )
        .agg(
            registros=("valor", "count"),
            media=("valor", "mean"),
            mediana=("valor", "median"),
            maximo=("valor", "max"),
            atipicos_iqr=("es_atipico_iqr", "sum"),
        )
        .reset_index()
    )

    ranking["ranking_media_magnitud"] = (
        ranking.groupby(
            "magnitud"
        )["media"]
        .rank(
            method="dense",
            ascending=False,
        )
        .astype("Int64")
    )

    ranking[
        [
            "media",
            "mediana",
            "maximo",
        ]
    ] = (
        ranking[
            [
                "media",
                "mediana",
                "maximo",
            ]
        ]
        .round(4)
    )

    ranking = ranking.sort_values(
        [
            "magnitud",
            "ranking_media_magnitud",
            "estacion",
        ]
    )

    guardar_csv(
        ranking,
        "36_ranking_estaciones_magnitud.csv",
        logger,
    )

    return {
        "descriptivos": descriptivos,
        "mensual": mensual,
        "diaria": diaria,
        "estaciones": estaciones,
        "atipicos": atipicos,
        "ranking": ranking,
    }


# =============================================================================
# GRÁFICO 1: DISTRIBUCIONES INDIVIDUALES
# =============================================================================

def grafico_distribuciones(
    datos: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """Genera histogramas separados para cada magnitud."""

    logger.info(
        "Generando distribuciones por magnitud..."
    )

    magnitudes = sorted(
        datos["magnitud"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    columnas = 3
    filas = math.ceil(
        len(magnitudes)
        / columnas
    )

    figura, ejes = plt.subplots(
        filas,
        columnas,
        figsize=(16, 4 * filas),
    )

    ejes = np.asarray(
        ejes
    ).reshape(-1)

    for eje, magnitud in zip(
        ejes,
        magnitudes,
    ):

        valores = datos.loc[
            datos["magnitud"] == magnitud,
            "valor",
        ]

        eje.hist(
            valores,
            bins=30,
            color="#2878B5",
            edgecolor="white",
            linewidth=0.4,
        )

        eje.axvline(
            valores.median(),
            color="#D1495B",
            linestyle="--",
            linewidth=1.5,
            label=(
                f"Mediana: "
                f"{valores.median():.2f}"
            ),
        )

        eje.set_title(
            f"Magnitud {magnitud}"
        )

        eje.set_xlabel(
            "Valor"
        )

        eje.set_ylabel(
            "Frecuencia"
        )

        eje.legend(
            fontsize=8
        )

        aplicar_formato_ejes(
            eje
        )

    for eje in ejes[
        len(magnitudes):
    ]:
        eje.set_visible(False)

    figura.suptitle(
        "Distribución de valores por magnitud",
        fontsize=17,
        fontweight="bold",
    )

    figura.subplots_adjust(
        top=0.93,
        hspace=0.42,
        wspace=0.25,
    )

    guardar_grafico(
        figura,
        "01_distribucion_magnitudes.png",
        logger,
    )


# =============================================================================
# GRÁFICO 2: BOXPLOTS INDIVIDUALES
# =============================================================================

def grafico_boxplots(
    datos: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """Genera un boxplot independiente por magnitud."""

    logger.info(
        "Generando boxplots por magnitud..."
    )

    magnitudes = sorted(
        datos["magnitud"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    columnas = 3
    filas = math.ceil(
        len(magnitudes)
        / columnas
    )

    figura, ejes = plt.subplots(
        filas,
        columnas,
        figsize=(16, 4 * filas),
    )

    ejes = np.asarray(
        ejes
    ).reshape(-1)

    for eje, magnitud in zip(
        ejes,
        magnitudes,
    ):

        valores = datos.loc[
            datos["magnitud"] == magnitud,
            "valor",
        ].dropna()

        eje.boxplot(
            valores,
            vert=True,
            patch_artist=True,
            boxprops={
                "facecolor": "#6BAED6",
                "edgecolor": "#1F4E79",
            },
            medianprops={
                "color": "#C1121F",
                "linewidth": 2,
            },
            whiskerprops={
                "color": "#1F4E79",
            },
            capprops={
                "color": "#1F4E79",
            },
            flierprops={
                "marker": "o",
                "markerfacecolor": "#F28E2B",
                "markeredgecolor": "none",
                "alpha": 0.35,
                "markersize": 3,
            },
        )

        eje.set_title(
            f"Magnitud {magnitud}"
        )

        eje.set_ylabel(
            "Valor"
        )

        eje.set_xticks(
            []
        )

        aplicar_formato_ejes(
            eje
        )

    for eje in ejes[
        len(magnitudes):
    ]:
        eje.set_visible(False)

    figura.suptitle(
        "Dispersión y posibles atípicos por magnitud",
        fontsize=17,
        fontweight="bold",
    )

    figura.subplots_adjust(
        top=0.93,
        hspace=0.38,
        wspace=0.25,
    )

    guardar_grafico(
        figura,
        "02_boxplot_magnitudes.png",
        logger,
    )


# =============================================================================
# GRÁFICO 3: EVOLUCIÓN MENSUAL NORMALIZADA
# =============================================================================

def grafico_evolucion_mensual(
    mensual: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """
    Compara patrones mensuales mediante un índice base 100.

    La normalización evita comparar directamente unidades
    y escalas distintas.
    """

    logger.info(
        "Generando evolución mensual normalizada..."
    )

    grafico = mensual[
        [
            "mes",
            "magnitud",
            "mediana",
        ]
    ].copy()

    primera_mediana = (
        grafico.sort_values("mes")
        .groupby("magnitud")["mediana"]
        .transform("first")
    )

    grafico["indice_base_100"] = np.where(
        primera_mediana != 0,
        grafico["mediana"]
        / primera_mediana
        * 100,
        np.nan,
    )

    figura, eje = plt.subplots(
        figsize=(15, 8)
    )

    for magnitud, grupo in grafico.groupby(
        "magnitud"
    ):

        grupo = grupo.sort_values(
            "mes"
        )

        eje.plot(
            grupo["mes"],
            grupo["indice_base_100"],
            marker="o",
            linewidth=1.8,
            markersize=4,
            label=f"Magnitud {magnitud}",
        )

    eje.axhline(
        100,
        color="black",
        linestyle="--",
        linewidth=1,
        alpha=0.6,
    )

    eje.set_title(
        "Evolución mensual de la mediana por magnitud\n"
        "Índice enero = 100",
        fontsize=16,
        fontweight="bold",
    )

    eje.set_xlabel(
        "Mes de 2024"
    )

    eje.set_ylabel(
        "Índice base 100"
    )

    eje.set_xticks(
        sorted(
            grafico["mes"]
            .unique()
        )
    )

    eje.legend(
        ncol=2,
        fontsize=9,
    )

    aplicar_formato_ejes(
        eje
    )

    guardar_grafico(
        figura,
        "03_evolucion_mensual.png",
        logger,
    )


# =============================================================================
# GRÁFICO 4: EVOLUCIÓN DIARIA POR MAGNITUD
# =============================================================================

def grafico_evolucion_diaria(
    diaria: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """Genera pequeñas series temporales separadas."""

    logger.info(
        "Generando evolución diaria por magnitud..."
    )

    magnitudes = sorted(
        diaria["magnitud"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    columnas = 2
    filas = math.ceil(
        len(magnitudes)
        / columnas
    )

    figura, ejes = plt.subplots(
        filas,
        columnas,
        figsize=(17, 3.5 * filas),
    )

    ejes = np.asarray(
        ejes
    ).reshape(-1)

    for eje, magnitud in zip(
        ejes,
        magnitudes,
    ):

        grupo = diaria.loc[
            diaria["magnitud"] == magnitud
        ].sort_values(
            "fecha"
        )

        eje.plot(
            grupo["fecha"],
            grupo["mediana"],
            color="#2878B5",
            linewidth=0.9,
            alpha=0.9,
        )

        media_movil = (
            grupo.set_index("fecha")["mediana"]
            .rolling(
                window=14,
                min_periods=1,
            )
            .mean()
        )

        eje.plot(
            media_movil.index,
            media_movil.values,
            color="#D1495B",
            linewidth=2,
            label="Media móvil 14 días",
        )

        eje.set_title(
            f"Magnitud {magnitud}"
        )

        eje.set_xlabel(
            "Fecha"
        )

        eje.set_ylabel(
            "Mediana diaria"
        )

        eje.legend(
            fontsize=8
        )

        eje.tick_params(
            axis="x",
            rotation=30,
        )

        aplicar_formato_ejes(
            eje
        )

    for eje in ejes[
        len(magnitudes):
    ]:
        eje.set_visible(False)

    figura.suptitle(
        "Evolución diaria por magnitud",
        fontsize=17,
        fontweight="bold",
    )

    figura.subplots_adjust(
        top=0.96,
        hspace=0.55,
        wspace=0.2,
    )

    guardar_grafico(
        figura,
        "04_evolucion_diaria.png",
        logger,
    )


# =============================================================================
# GRÁFICO 5: ATÍPICOS POR MAGNITUD
# =============================================================================

def grafico_atipicos(
    atipicos: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """Representa el porcentaje de atípicos por magnitud."""

    logger.info(
        "Generando gráfico de atípicos..."
    )

    grafico = atipicos.sort_values(
        "porcentaje_atipicos",
        ascending=True,
    )

    figura, eje = plt.subplots(
        figsize=(12, 7)
    )

    barras = eje.barh(
        grafico["magnitud"].astype(str),
        grafico["porcentaje_atipicos"],
        color="#F28E2B",
        edgecolor="#8C4A00",
        linewidth=0.5,
    )

    for barra, porcentaje, cantidad in zip(
        barras,
        grafico["porcentaje_atipicos"],
        grafico["atipicos"],
    ):

        eje.text(
            barra.get_width() + 0.15,
            barra.get_y() + barra.get_height() / 2,
            f"{porcentaje:.2f}% ({int(cantidad)})",
            va="center",
            fontsize=9,
        )

    eje.set_title(
        "Posibles atípicos IQR por magnitud",
        fontsize=16,
        fontweight="bold",
    )

    eje.set_xlabel(
        "Porcentaje de registros marcados"
    )

    eje.set_ylabel(
        "Magnitud"
    )

    aplicar_formato_ejes(
        eje
    )

    guardar_grafico(
        figura,
        "05_atipicos_por_magnitud.png",
        logger,
    )


# =============================================================================
# GRÁFICO 6: HEATMAP MES-MAGNITUD NORMALIZADO
# =============================================================================

def grafico_heatmap(
    mensual: pd.DataFrame,
    logger: logging.Logger,
) -> None:
    """
    Genera una matriz de puntuaciones normalizadas por magnitud.

    Cada fila se normaliza independientemente mediante z-score.
    """

    logger.info(
        "Generando mapa de calor mes-magnitud..."
    )

    matriz = mensual.pivot(
        index="magnitud",
        columns="mes",
        values="mediana",
    ).sort_index()

    medias = matriz.mean(
        axis=1
    )

    desviaciones = matriz.std(
        axis=1
    ).replace(
        0,
        np.nan,
    )

    matriz_z = matriz.sub(
        medias,
        axis=0,
    ).div(
        desviaciones,
        axis=0,
    ).fillna(0)

    figura, eje = plt.subplots(
        figsize=(15, 7)
    )

    imagen = eje.imshow(
        matriz_z.values,
        aspect="auto",
        cmap="coolwarm",
        vmin=-2.5,
        vmax=2.5,
    )

    eje.set_title(
        "Variación mensual normalizada dentro de cada magnitud",
        fontsize=16,
        fontweight="bold",
    )

    eje.set_xlabel(
        "Mes de 2024"
    )

    eje.set_ylabel(
        "Magnitud"
    )

    eje.set_xticks(
        np.arange(
            len(matriz_z.columns)
        )
    )

    eje.set_xticklabels(
        [
            str(valor)
            for valor in matriz_z.columns
        ]
    )

    eje.set_yticks(
        np.arange(
            len(matriz_z.index)
        )
    )

    eje.set_yticklabels(
        [
            str(valor)
            for valor in matriz_z.index
        ]
    )

    for fila in range(
        matriz_z.shape[0]
    ):

        for columna in range(
            matriz_z.shape[1]
        ):

            valor = matriz_z.iloc[
                fila,
                columna,
            ]

            color_texto = (
                "white"
                if abs(valor) > 1.3
                else "black"
            )

            eje.text(
                columna,
                fila,
                f"{valor:.1f}",
                ha="center",
                va="center",
                fontsize=8,
                color=color_texto,
            )

    barra_color = figura.colorbar(
        imagen,
        ax=eje,
        shrink=0.85,
    )

    barra_color.set_label(
        "Puntuación z de la mediana mensual"
    )

    guardar_grafico(
        figura,
        "06_heatmap_mes_magnitud.png",
        logger,
    )


# =============================================================================
# GRÁFICO 7: PANEL RESUMEN
# =============================================================================

def grafico_panel(
    datos: pd.DataFrame,
    tablas: dict[str, pd.DataFrame],
    logger: logging.Logger,
) -> None:
    """Genera un panel ejecutivo resumen del EDA."""

    logger.info(
        "Generando panel resumen del EDA..."
    )

    descriptivos = tablas[
        "descriptivos"
    ]

    mensual = tablas[
        "mensual"
    ]

    atipicos = tablas[
        "atipicos"
    ]

    estaciones = tablas[
        "estaciones"
    ]

    figura = plt.figure(
        figsize=(18, 12)
    )

    rejilla = figura.add_gridspec(
        nrows=3,
        ncols=4,
        height_ratios=[
            0.75,
            2.2,
            2.2,
        ],
        hspace=0.55,
        wspace=0.45,
    )

    # -------------------------------------------------------------------------
    # KPI 1
    # -------------------------------------------------------------------------

    eje_kpi_1 = figura.add_subplot(
        rejilla[0, 0]
    )

    eje_kpi_1.axis(
        "off"
    )

    eje_kpi_1.text(
        0.5,
        0.62,
        f"{len(datos):,}".replace(",", "."),
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="#1F4E79",
    )

    eje_kpi_1.text(
        0.5,
        0.22,
        "Mediciones válidas",
        ha="center",
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # KPI 2
    # -------------------------------------------------------------------------

    eje_kpi_2 = figura.add_subplot(
        rejilla[0, 1]
    )

    eje_kpi_2.axis(
        "off"
    )

    eje_kpi_2.text(
        0.5,
        0.62,
        str(
            datos["estacion"].nunique()
        ),
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="#1F4E79",
    )

    eje_kpi_2.text(
        0.5,
        0.22,
        "Estaciones",
        ha="center",
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # KPI 3
    # -------------------------------------------------------------------------

    eje_kpi_3 = figura.add_subplot(
        rejilla[0, 2]
    )

    eje_kpi_3.axis(
        "off"
    )

    eje_kpi_3.text(
        0.5,
        0.62,
        str(
            datos["magnitud"].nunique()
        ),
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="#1F4E79",
    )

    eje_kpi_3.text(
        0.5,
        0.22,
        "Magnitudes",
        ha="center",
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # KPI 4
    # -------------------------------------------------------------------------

    eje_kpi_4 = figura.add_subplot(
        rejilla[0, 3]
    )

    eje_kpi_4.axis(
        "off"
    )

    total_atipicos = int(
        datos["es_atipico_iqr"].sum()
    )

    porcentaje_atipicos = (
        total_atipicos
        / len(datos)
        * 100
    )

    eje_kpi_4.text(
        0.5,
        0.62,
        f"{porcentaje_atipicos:.2f}%",
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color="#D1495B",
    )

    eje_kpi_4.text(
        0.5,
        0.22,
        f"Atípicos IQR ({total_atipicos})",
        ha="center",
        fontsize=11,
    )

    # -------------------------------------------------------------------------
    # REGISTROS POR MAGNITUD
    # -------------------------------------------------------------------------

    eje_registros = figura.add_subplot(
        rejilla[1, 0:2]
    )

    eje_registros.bar(
        descriptivos[
            "magnitud"
        ].astype(str),
        descriptivos[
            "registros"
        ],
        color="#4E79A7",
    )

    eje_registros.set_title(
        "Número de mediciones por magnitud",
        fontweight="bold",
    )

    eje_registros.set_xlabel(
        "Magnitud"
    )

    eje_registros.set_ylabel(
        "Registros"
    )

    aplicar_formato_ejes(
        eje_registros
    )

    # -------------------------------------------------------------------------
    # ATÍPICOS
    # -------------------------------------------------------------------------

    eje_atipicos = figura.add_subplot(
        rejilla[1, 2:4]
    )

    atipicos_ordenados = atipicos.sort_values(
        "porcentaje_atipicos",
        ascending=False,
    )

    eje_atipicos.bar(
        atipicos_ordenados[
            "magnitud"
        ].astype(str),
        atipicos_ordenados[
            "porcentaje_atipicos"
        ],
        color="#F28E2B",
    )

    eje_atipicos.set_title(
        "Porcentaje de atípicos por magnitud",
        fontweight="bold",
    )

    eje_atipicos.set_xlabel(
        "Magnitud"
    )

    eje_atipicos.set_ylabel(
        "Porcentaje"
    )

    aplicar_formato_ejes(
        eje_atipicos
    )

    # -------------------------------------------------------------------------
    # EVOLUCIÓN NORMALIZADA
    # -------------------------------------------------------------------------

    eje_evolucion = figura.add_subplot(
        rejilla[2, 0:3]
    )

    evolucion = mensual[
        [
            "mes",
            "magnitud",
            "mediana",
        ]
    ].copy()

    base = (
        evolucion.sort_values("mes")
        .groupby("magnitud")["mediana"]
        .transform("first")
    )

    evolucion["indice"] = np.where(
        base != 0,
        evolucion["mediana"]
        / base
        * 100,
        np.nan,
    )

    for magnitud, grupo in evolucion.groupby(
        "magnitud"
    ):

        grupo = grupo.sort_values(
            "mes"
        )

        eje_evolucion.plot(
            grupo["mes"],
            grupo["indice"],
            marker="o",
            markersize=3,
            linewidth=1.4,
            label=str(magnitud),
        )

    eje_evolucion.axhline(
        100,
        color="black",
        linestyle="--",
        linewidth=0.8,
    )

    eje_evolucion.set_title(
        "Evolución mensual normalizada, enero = 100",
        fontweight="bold",
    )

    eje_evolucion.set_xlabel(
        "Mes"
    )

    eje_evolucion.set_ylabel(
        "Índice"
    )

    eje_evolucion.set_xticks(
        sorted(
            evolucion["mes"]
            .unique()
        )
    )

    eje_evolucion.legend(
        title="Magnitud",
        ncol=4,
        fontsize=7,
    )

    aplicar_formato_ejes(
        eje_evolucion
    )

    # -------------------------------------------------------------------------
    # ESTACIONES
    # -------------------------------------------------------------------------

    eje_estaciones = figura.add_subplot(
        rejilla[2, 3]
    )

    top_estaciones = (
        estaciones.nlargest(
            10,
            "registros",
        )
        .sort_values(
            "registros",
            ascending=True,
        )
    )

    eje_estaciones.barh(
        top_estaciones[
            "estacion"
        ].astype(str),
        top_estaciones[
            "registros"
        ],
        color="#59A14F",
    )

    eje_estaciones.set_title(
        "Top 10 estaciones\npor número de mediciones",
        fontweight="bold",
    )

    eje_estaciones.set_xlabel(
        "Registros"
    )

    eje_estaciones.set_ylabel(
        "Estación"
    )

    aplicar_formato_ejes(
        eje_estaciones
    )

    figura.suptitle(
        "Panel exploratorio de calidad del aire de Madrid, 2024",
        fontsize=20,
        fontweight="bold",
        y=0.99,
    )

    figura.text(
        0.5,
        0.01,
        (
            "Periodo disponible: "
            f"{datos['fecha'].min().date()} a "
            f"{datos['fecha'].max().date()}. "
            "Los posibles atípicos se conservan."
        ),
        ha="center",
        fontsize=10,
    )

    guardar_grafico(
        figura,
        "07_panel_eda_calidad_aire.png",
        logger,
    )


# =============================================================================
# HALLAZGOS AUTOMÁTICOS
# =============================================================================

def obtener_hallazgos(
    datos: pd.DataFrame,
    tablas: dict[str, pd.DataFrame],
) -> dict:
    """Extrae resultados descriptivos sin alterar los datos."""

    descriptivos = tablas[
        "descriptivos"
    ]

    atipicos = tablas[
        "atipicos"
    ]

    mensual = tablas[
        "mensual"
    ]

    fila_mas_atipicos = atipicos.loc[
        atipicos[
            "atipicos"
        ].idxmax()
    ]

    fila_mayor_porcentaje = atipicos.loc[
        atipicos[
            "porcentaje_atipicos"
        ].idxmax()
    ]

    fila_mayor_maximo = descriptivos.loc[
        descriptivos[
            "maximo"
        ].idxmax()
    ]

    maximos_mensuales = (
        mensual.loc[
            mensual.groupby(
                "magnitud"
            )["mediana"]
            .idxmax(),
            [
                "magnitud",
                "mes",
                "mediana",
            ],
        ]
        .sort_values(
            "magnitud"
        )
    )

    picos_mensuales = [
        {
            "magnitud": int(fila["magnitud"]),
            "mes_mayor_mediana": int(fila["mes"]),
            "mediana": float(fila["mediana"]),
        }
        for _, fila in maximos_mensuales.iterrows()
    ]

    hallazgos = {
        "registros": int(
            len(datos)
        ),
        "fecha_minima": str(
            datos["fecha"].min().date()
        ),
        "fecha_maxima": str(
            datos["fecha"].max().date()
        ),
        "estaciones": int(
            datos["estacion"].nunique()
        ),
        "magnitudes": int(
            datos["magnitud"].nunique()
        ),
        "puntos_muestreo": int(
            datos["punto_muestreo"].nunique()
        ),
        "atipicos_iqr": int(
            datos["es_atipico_iqr"].sum()
        ),
        "porcentaje_atipicos_iqr": round(
            float(
                datos["es_atipico_iqr"].mean()
                * 100
            ),
            4,
        ),
        "magnitud_con_mas_atipicos": {
            "magnitud": int(
                fila_mas_atipicos["magnitud"]
            ),
            "cantidad": int(
                fila_mas_atipicos["atipicos"]
            ),
        },
        "magnitud_con_mayor_porcentaje_atipicos": {
            "magnitud": int(
                fila_mayor_porcentaje["magnitud"]
            ),
            "porcentaje": float(
                fila_mayor_porcentaje[
                    "porcentaje_atipicos"
                ]
            ),
        },
        "mayor_valor_observado": {
            "magnitud": int(
                fila_mayor_maximo["magnitud"]
            ),
            "valor": float(
                fila_mayor_maximo["maximo"]
            ),
        },
        "mes_con_mayor_mediana_por_magnitud":
            picos_mensuales,
        "criterio_atipicos": (
            "Los posibles atípicos IQR se conservan. "
            "Su presencia no implica automáticamente "
            "un error de medición."
        ),
        "limitacion_temporal": (
            "El dataset procesado disponible termina "
            "el 30 de noviembre de 2024."
        ),
    }

    return hallazgos


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main() -> None:
    """Ejecuta el EDA completo."""

    crear_directorios()
    logger = configurar_logging()

    inicio = datetime.now()

    logger.info(
        "=" * 79
    )
    logger.info(
        "INICIO DEL EDA DE CALIDAD DEL AIRE DE MADRID"
    )
    logger.info(
        "=" * 79
    )

    hash_antes = sha256_fichero(
        PROCESSED
    )

    logger.info(
        "SHA256 del procesado antes del EDA: %s",
        hash_antes,
    )

    datos = cargar_datos(
        logger
    )

    tablas = crear_tablas(
        datos,
        logger,
    )

    grafico_distribuciones(
        datos,
        logger,
    )

    grafico_boxplots(
        datos,
        logger,
    )

    grafico_evolucion_mensual(
        tablas["mensual"],
        logger,
    )

    grafico_evolucion_diaria(
        tablas["diaria"],
        logger,
    )

    grafico_atipicos(
        tablas["atipicos"],
        logger,
    )

    grafico_heatmap(
        tablas["mensual"],
        logger,
    )

    grafico_panel(
        datos,
        tablas,
        logger,
    )

    hallazgos = obtener_hallazgos(
        datos,
        tablas,
    )

    hash_despues = sha256_fichero(
        PROCESSED
    )

    procesado_modificado = (
        hash_antes != hash_despues
    )

    if procesado_modificado:

        raise RuntimeError(
            "El dataset procesado ha cambiado durante el EDA."
        )

    resumen = {
        "dataset": {
            "ruta": str(PROCESSED),
            "registros": int(len(datos)),
            "columnas": int(len(datos.columns)),
            "sha256_antes": hash_antes,
            "sha256_despues": hash_despues,
            "modificado": procesado_modificado,
        },
        "cobertura": {
            "fecha_minima": datos["fecha"].min(),
            "fecha_maxima": datos["fecha"].max(),
            "estaciones": int(
                datos["estacion"].nunique()
            ),
            "magnitudes": int(
                datos["magnitud"].nunique()
            ),
            "puntos_muestreo": int(
                datos["punto_muestreo"].nunique()
            ),
        },
        "resultados": {
            "tablas_csv_generadas": 6,
            "graficos_png_generados": 7,
            "atipicos_iqr_conservados": int(
                datos["es_atipico_iqr"].sum()
            ),
        },
        "hallazgos": hallazgos,
        "ejecucion": {
            "inicio": inicio.isoformat(),
            "fin": datetime.now().isoformat(),
        },
    }

    guardar_json(
        resumen,
        "04_resumen_eda_python.json",
        logger,
    )

    duracion = (
        datetime.now()
        - inicio
    ).total_seconds()

    logger.info(
        "=" * 79
    )
    logger.info(
        "EDA COMPLETADO CORRECTAMENTE"
    )
    logger.info(
        "Tablas CSV generadas: 6"
    )
    logger.info(
        "Gráficos PNG generados: 7"
    )
    logger.info(
        "Registros analizados: %s",
        len(datos),
    )
    logger.info(
        "Atípicos conservados: %s",
        int(
            datos["es_atipico_iqr"].sum()
        ),
    )
    logger.info(
        "Dataset procesado no modificado: %s",
        not procesado_modificado,
    )
    logger.info(
        "Duración: %.2f segundos",
        duracion,
    )
    logger.info(
        "=" * 79
    )


if __name__ == "__main__":

    try:

        main()

    except Exception:

        logging.exception(
            "ERROR durante el análisis exploratorio."
        )

        raise

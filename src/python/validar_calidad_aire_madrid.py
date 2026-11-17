#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validación independiente del dataset procesado de calidad del aire.

IMPORTANTE:
- NO lee el RAW.
- NO limpia datos.
- NO modifica el dataset procesado.
- Comprueba que la salida de la fase de limpieza cumple las reglas definidas.

ENTRADA:
    datos/processed/aire_madrid/calidad_aire_madrid_procesado.csv

SALIDAS:
    salidas/aire_madrid/python/csv/
    salidas/aire_madrid/python/json/
    salidas/aire_madrid/python/logs/
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

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

SALIDA = (
    PROYECTO
    / "salidas"
    / "aire_madrid"
    / "python"
)

CSV_DIR = SALIDA / "csv"
JSON_DIR = SALIDA / "json"
LOG_DIR = SALIDA / "logs"

LOG_FILE = (
    LOG_DIR
    / "03_validar_calidad_aire_madrid.log"
)


COLUMNAS_ESPERADAS = [
    "provincia",
    "municipio",
    "estacion",
    "magnitud",
    "punto_muestreo",
    "anio",
    "mes",
    "dia",
    "fecha",
    "valor",
    "indicador_validez",
    "es_atipico_iqr",
]


# =============================================================================
# FUNCIONES
# =============================================================================

def crear_directorios():
    """Garantiza la existencia de los directorios de salida."""

    for directorio in [
        CSV_DIR,
        JSON_DIR,
        LOG_DIR,
    ]:
        directorio.mkdir(
            parents=True,
            exist_ok=True,
        )


def configurar_logging():
    """Configura logging en terminal y fichero."""

    logger = logging.getLogger("validacion")

    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(formato)

    fichero = logging.FileHandler(
        LOG_FILE,
        mode="w",
        encoding="utf-8",
    )

    fichero.setFormatter(formato)

    logger.addHandler(consola)
    logger.addHandler(fichero)

    return logger


def guardar_csv(df, nombre, logger):

    ruta = CSV_DIR / nombre

    df.to_csv(
        ruta,
        index=False,
        encoding="utf-8",
    )

    logger.info(
        "CSV generado: %s",
        ruta,
    )


def guardar_json(datos, nombre, logger):

    ruta = JSON_DIR / nombre

    with ruta.open(
        "w",
        encoding="utf-8",
    ) as fichero:

        json.dump(
            datos,
            fichero,
            indent=4,
            ensure_ascii=False,
            default=str,
        )

    logger.info(
        "JSON generado: %s",
        ruta,
    )


# =============================================================================
# VALIDACIONES
# =============================================================================

def registrar_validacion(
    lista,
    prueba,
    resultado,
    esperado,
    observado,
):
    """Añade una prueba al informe."""

    lista.append(
        {
            "PRUEBA": prueba,
            "RESULTADO": (
                "OK"
                if resultado
                else "ERROR"
            ),
            "ESPERADO": esperado,
            "OBSERVADO": observado,
        }
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    crear_directorios()

    logger = configurar_logging()

    inicio = datetime.now()

    logger.info("=" * 79)
    logger.info("VALIDACIÓN DEL DATASET PROCESADO")
    logger.info("=" * 79)

    # -------------------------------------------------------------------------
    # 1. EXISTENCIA
    # -------------------------------------------------------------------------

    if not PROCESSED.exists():

        raise FileNotFoundError(
            f"No existe: {PROCESSED}"
        )

    logger.info(
        "Dataset: %s",
        PROCESSED,
    )

    # -------------------------------------------------------------------------
    # 2. LECTURA
    # -------------------------------------------------------------------------

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

    filas = len(datos)
    columnas = len(datos.columns)

    logger.info(
        "Registros: %s",
        filas,
    )

    logger.info(
        "Columnas: %s",
        columnas,
    )

    validaciones = []

    # -------------------------------------------------------------------------
    # 3. COLUMNAS
    # -------------------------------------------------------------------------

    columnas_correctas = (
        list(datos.columns)
        == COLUMNAS_ESPERADAS
    )

    registrar_validacion(
        validaciones,
        "estructura_columnas",
        columnas_correctas,
        str(COLUMNAS_ESPERADAS),
        str(list(datos.columns)),
    )

    # -------------------------------------------------------------------------
    # 4. NULOS
    # -------------------------------------------------------------------------

    nulos_totales = int(
        datos.isna().sum().sum()
    )

    registrar_validacion(
        validaciones,
        "nulos_totales",
        nulos_totales == 0,
        "0",
        nulos_totales,
    )

    # -------------------------------------------------------------------------
    # 5. FECHAS
    # -------------------------------------------------------------------------

    fechas_nulas = int(
        datos["fecha"].isna().sum()
    )

    registrar_validacion(
        validaciones,
        "fechas_validas",
        fechas_nulas == 0,
        "0 fechas inválidas",
        fechas_nulas,
    )

    # -------------------------------------------------------------------------
    # 6. VALORES NUMÉRICOS
    # -------------------------------------------------------------------------

    valores_nulos = int(
        datos["valor"].isna().sum()
    )

    registrar_validacion(
        validaciones,
        "valores_numericos",
        valores_nulos == 0,
        "0 valores no numéricos",
        valores_nulos,
    )

    # -------------------------------------------------------------------------
    # 7. INDICADOR DE VALIDEZ
    # -------------------------------------------------------------------------

    indicadores = sorted(
        datos[
            "indicador_validez"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    solo_validos = (
        indicadores == ["V"]
    )

    registrar_validacion(
        validaciones,
        "indicador_validez",
        solo_validos,
        "['V']",
        str(indicadores),
    )

    # -------------------------------------------------------------------------
    # 8. DUPLICADOS
    # -------------------------------------------------------------------------

    clave = [
        "punto_muestreo",
        "fecha",
    ]

    duplicados = int(
        datos.duplicated(
            subset=clave
        ).sum()
    )

    registrar_validacion(
        validaciones,
        "duplicados_punto_fecha",
        duplicados == 0,
        "0",
        duplicados,
    )

    # -------------------------------------------------------------------------
    # 9. COHERENCIA AÑO/MES/DÍA/FECHA
    # -------------------------------------------------------------------------

    fecha_reconstruida = pd.to_datetime(
        {
            "year": datos["anio"],
            "month": datos["mes"],
            "day": datos["dia"],
        },
        errors="coerce",
    )

    incoherencias_fecha = int(
        (
            fecha_reconstruida
            != datos["fecha"]
        ).sum()
    )

    registrar_validacion(
        validaciones,
        "coherencia_fecha",
        incoherencias_fecha == 0,
        "0 incoherencias",
        incoherencias_fecha,
    )

    # -------------------------------------------------------------------------
    # 10. AÑO
    # -------------------------------------------------------------------------

    anios = sorted(
        int(x)
        for x in datos["anio"]
        .dropna()
        .unique()
    )

    registrar_validacion(
        validaciones,
        "anio_dataset",
        anios == [2024],
        "[2024]",
        str(anios),
    )

    # -------------------------------------------------------------------------
    # 11. MESES
    # -------------------------------------------------------------------------

    meses = sorted(
        int(x)
        for x in datos["mes"]
        .dropna()
        .unique()
    )

    meses_correctos = all(
        1 <= mes <= 12
        for mes in meses
    )

    registrar_validacion(
        validaciones,
        "rango_meses",
        meses_correctos,
        "1 <= mes <= 12",
        str(meses),
    )

    # -------------------------------------------------------------------------
    # 12. DÍAS
    # -------------------------------------------------------------------------

    dias_correctos = bool(
        datos["dia"]
        .between(1, 31)
        .all()
    )

    registrar_validacion(
        validaciones,
        "rango_dias",
        dias_correctos,
        "1 <= día <= 31",
        (
            f"{datos['dia'].min()} - "
            f"{datos['dia'].max()}"
        ),
    )

    # -------------------------------------------------------------------------
    # 13. VALORES NEGATIVOS
    # -------------------------------------------------------------------------

    negativos = int(
        (datos["valor"] < 0).sum()
    )

    registrar_validacion(
        validaciones,
        "valores_negativos",
        negativos == 0,
        "0",
        negativos,
    )

    # -------------------------------------------------------------------------
    # 14. PUNTO DE MUESTREO
    # -------------------------------------------------------------------------

    puntos_vacios = int(
        (
            datos["punto_muestreo"]
            .fillna("")
            .str.strip()
            == ""
        ).sum()
    )

    registrar_validacion(
        validaciones,
        "punto_muestreo_no_vacio",
        puntos_vacios == 0,
        "0 vacíos",
        puntos_vacios,
    )

    # -------------------------------------------------------------------------
    # 15. ESTACIONES Y MAGNITUDES
    # -------------------------------------------------------------------------

    estaciones = int(
        datos["estacion"].nunique()
    )

    magnitudes = int(
        datos["magnitud"].nunique()
    )

    registrar_validacion(
        validaciones,
        "estaciones_detectadas",
        estaciones > 0,
        "> 0",
        estaciones,
    )

    registrar_validacion(
        validaciones,
        "magnitudes_detectadas",
        magnitudes > 0,
        "> 0",
        magnitudes,
    )

    # -------------------------------------------------------------------------
    # 16. BOOLEANO DE ATÍPICOS
    # -------------------------------------------------------------------------

    texto_atipicos = (
        datos["es_atipico_iqr"]
        .astype(str)
        .str.lower()
    )

    categorias_atipicos = sorted(
        texto_atipicos.unique().tolist()
    )

    booleanos_validos = set(
        categorias_atipicos
    ).issubset(
        {"true", "false"}
    )

    registrar_validacion(
        validaciones,
        "marcado_atipicos_booleano",
        booleanos_validos,
        "true/false",
        str(categorias_atipicos),
    )

    numero_atipicos = int(
        texto_atipicos.eq("true").sum()
    )

    # -------------------------------------------------------------------------
    # 17. PERFIL POR COLUMNA
    # -------------------------------------------------------------------------

    perfil = pd.DataFrame(
        {
            "COLUMNA": datos.columns,
            "TIPO": [
                str(datos[c].dtype)
                for c in datos.columns
            ],
            "NULOS": [
                int(datos[c].isna().sum())
                for c in datos.columns
            ],
            "UNICOS": [
                int(
                    datos[c]
                    .nunique(
                        dropna=True
                    )
                )
                for c in datos.columns
            ],
        }
    )

    guardar_csv(
        perfil,
        "28_calidad_por_columna_procesado.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 18. CONTROL TEMPORAL
    # -------------------------------------------------------------------------

    temporal = (
        datos.groupby(
            [
                "anio",
                "mes",
            ]
        )
        .agg(
            fecha_min=(
                "fecha",
                "min",
            ),
            fecha_max=(
                "fecha",
                "max",
            ),
            mediciones=(
                "valor",
                "count",
            ),
            dias_con_datos=(
                "fecha",
                "nunique",
            ),
            estaciones=(
                "estacion",
                "nunique",
            ),
        )
        .reset_index()
    )

    guardar_csv(
        temporal,
        "29_control_temporal_procesado.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 19. CONTROL DE MAGNITUDES
    # -------------------------------------------------------------------------

    control_magnitudes = (
        datos.groupby(
            "magnitud"
        )
        .agg(
            registros=(
                "valor",
                "count",
            ),
            media=(
                "valor",
                "mean",
            ),
            mediana=(
                "valor",
                "median",
            ),
            minimo=(
                "valor",
                "min",
            ),
            maximo=(
                "valor",
                "max",
            ),
        )
        .reset_index()
    )

    control_magnitudes[
        [
            "media",
            "mediana",
            "minimo",
            "maximo",
        ]
    ] = (
        control_magnitudes[
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
        control_magnitudes,
        "30_control_magnitudes_procesado.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 20. INFORME DE VALIDACIONES
    # -------------------------------------------------------------------------

    informe = pd.DataFrame(
        validaciones
    )

    guardar_csv(
        informe,
        "27_validaciones_dataset_procesado.csv",
        logger,
    )

    errores = int(
        (
            informe["RESULTADO"]
            != "OK"
        ).sum()
    )

    pruebas_ok = int(
        (
            informe["RESULTADO"]
            == "OK"
        ).sum()
    )

    # -------------------------------------------------------------------------
    # 21. JSON
    # -------------------------------------------------------------------------

    resumen = {

        "dataset": {
            "fichero": str(PROCESSED),
            "registros": filas,
            "columnas": columnas,
        },

        "calidad": {
            "nulos_totales": nulos_totales,
            "duplicados": duplicados,
            "fechas_invalidas": fechas_nulas,
            "incoherencias_fecha": incoherencias_fecha,
            "valores_negativos": negativos,
        },

        "cobertura": {
            "anios": anios,
            "meses": meses,
            "fecha_minima":
                datos["fecha"].min(),
            "fecha_maxima":
                datos["fecha"].max(),
            "estaciones": estaciones,
            "magnitudes": magnitudes,
            "puntos_muestreo":
                int(
                    datos[
                        "punto_muestreo"
                    ].nunique()
                ),
        },

        "atipicos_iqr": {
            "marcados":
                numero_atipicos,
            "eliminados":
                0,
        },

        "validacion": {
            "pruebas_totales":
                len(informe),
            "pruebas_ok":
                pruebas_ok,
            "errores":
                errores,
            "resultado_global":
                (
                    "OK"
                    if errores == 0
                    else "ERROR"
                ),
        },

        "ejecucion": {
            "inicio":
                inicio.isoformat(),
            "fin":
                datetime.now().isoformat(),
        },
    }

    guardar_json(
        resumen,
        "03_resumen_validacion.json",
        logger,
    )

    # -------------------------------------------------------------------------
    # 22. RESULTADO
    # -------------------------------------------------------------------------

    logger.info("=" * 79)

    logger.info(
        "Pruebas ejecutadas: %s",
        len(informe),
    )

    logger.info(
        "Pruebas OK: %s",
        pruebas_ok,
    )

    logger.info(
        "Errores: %s",
        errores,
    )

    logger.info(
        "Atípicos conservados: %s",
        numero_atipicos,
    )

    logger.info(
        "Estaciones: %s",
        estaciones,
    )

    logger.info(
        "Magnitudes: %s",
        magnitudes,
    )

    logger.info(
        "Periodo: %s -> %s",
        datos["fecha"].min(),
        datos["fecha"].max(),
    )

    if errores:

        logger.error(
            "VALIDACIÓN FINAL: ERROR"
        )

        logger.info("=" * 79)

        raise RuntimeError(
            f"El dataset no supera {errores} validaciones."
        )

    logger.info(
        "VALIDACIÓN FINAL: OK"
    )

    logger.info(
        "El dataset procesado está preparado para EDA."
    )

    logger.info("=" * 79)


if __name__ == "__main__":

    try:

        main()

    except Exception:

        logging.exception(
            "ERROR durante la validación."
        )

        raise

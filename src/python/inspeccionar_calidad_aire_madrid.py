#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inspección inicial del dataset de calidad del aire de Madrid.

Este programa:

1. Lee exclusivamente el fichero RAW.
2. No modifica ni sobrescribe el fichero original.
3. Examina estructura, tipos, nulos y duplicados.
4. Comprueba los pares D01/V01 ... D31/V31.
5. Convierte temporalmente los datos de ancho a largo para analizarlos.
6. Detecta fechas imposibles.
7. Genera evidencias en CSV, JSON y LOG.

Entrada:
    datos/raw/aire_madrid/calidad_aire_madrid.csv

Salidas:
    salidas/aire_madrid/python/csv/
    salidas/aire_madrid/python/json/
    salidas/aire_madrid/python/logs/
"""

from __future__ import annotations

import calendar
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


# =============================================================================
# CONFIGURACIÓN DE RUTAS
# =============================================================================

PROYECTO = Path.home() / "curso_ia"

RAW = (
    PROYECTO
    / "datos"
    / "raw"
    / "aire_madrid"
    / "calidad_aire_madrid.csv"
)

SALIDA_BASE = PROYECTO / "salidas" / "aire_madrid" / "python"

CSV_DIR = SALIDA_BASE / "csv"
JSON_DIR = SALIDA_BASE / "json"
LOG_DIR = SALIDA_BASE / "logs"

LOG_FILE = LOG_DIR / "01_inspeccionar_calidad_aire_madrid.log"


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def crear_directorios() -> None:
    """Crea únicamente los directorios de salida necesarios."""

    for directorio in [CSV_DIR, JSON_DIR, LOG_DIR]:
        directorio.mkdir(parents=True, exist_ok=True)


def configurar_logging() -> logging.Logger:
    """Configura el registro simultáneo por consola y fichero."""

    logger = logging.getLogger("inspeccion_aire_madrid")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    manejador_fichero = logging.FileHandler(
        LOG_FILE,
        mode="w",
        encoding="utf-8",
    )
    manejador_fichero.setFormatter(formato)

    manejador_consola = logging.StreamHandler(sys.stdout)
    manejador_consola.setFormatter(formato)

    logger.addHandler(manejador_fichero)
    logger.addHandler(manejador_consola)

    return logger


def guardar_csv(
    dataframe: pd.DataFrame,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Guarda un DataFrame en formato CSV."""

    ruta = CSV_DIR / nombre

    dataframe.to_csv(
        ruta,
        index=False,
        encoding="utf-8",
    )

    logger.info("CSV generado: %s", ruta)


def guardar_json(
    contenido: dict,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Guarda un diccionario como JSON legible."""

    ruta = JSON_DIR / nombre

    with ruta.open("w", encoding="utf-8") as fichero:
        json.dump(
            contenido,
            fichero,
            ensure_ascii=False,
            indent=4,
            default=str,
        )

    logger.info("JSON generado: %s", ruta)


def convertir_formato_largo(
    datos: pd.DataFrame,
    columnas_base: list[str],
) -> pd.DataFrame:
    """
    Convierte los pares Dxx y Vxx a una fila diaria por observación.

    La conversión se realiza en memoria y no modifica el fichero RAW.
    """

    bloques = []

    for numero_dia in range(1, 32):
        sufijo = f"{numero_dia:02d}"

        columna_dato = f"D{sufijo}"
        columna_validez = f"V{sufijo}"

        bloque = datos[columnas_base].copy()

        bloque["DIA"] = numero_dia
        bloque["VALOR"] = pd.to_numeric(
            datos[columna_dato],
            errors="coerce",
        )
        bloque["VALIDO"] = (
            datos[columna_validez]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        bloques.append(bloque)

    datos_largos = pd.concat(
        bloques,
        ignore_index=True,
    )

    datos_largos["FECHA"] = pd.to_datetime(
        {
            "year": datos_largos["ANO"],
            "month": datos_largos["MES"],
            "day": datos_largos["DIA"],
        },
        errors="coerce",
    )

    datos_largos["FECHA_CALENDARIO_VALIDA"] = (
        datos_largos["FECHA"].notna()
    )

    return datos_largos


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main() -> None:
    """Ejecuta la inspección completa."""

    crear_directorios()
    logger = configurar_logging()

    inicio = datetime.now()

    logger.info("=" * 79)
    logger.info("INICIO DE LA INSPECCIÓN DEL DATASET DE CALIDAD DEL AIRE")
    logger.info("=" * 79)

    # -------------------------------------------------------------------------
    # 1. COMPROBACIÓN DEL FICHERO
    # -------------------------------------------------------------------------

    logger.info("Proyecto: %s", PROYECTO)
    logger.info("Fichero RAW: %s", RAW)

    if not RAW.exists():
        logger.error("No existe el fichero RAW esperado.")
        raise FileNotFoundError(f"No se encuentra el fichero: {RAW}")

    tamano_bytes = RAW.stat().st_size

    logger.info("Tamaño del fichero: %s bytes", tamano_bytes)
    logger.info("El fichero RAW existe y será abierto únicamente para lectura.")

    # -------------------------------------------------------------------------
    # 2. LECTURA
    # -------------------------------------------------------------------------

    logger.info("Leyendo CSV con separador ';'...")

    datos = pd.read_csv(
        RAW,
        sep=";",
        encoding="utf-8-sig",
        dtype={
            "PROVINCIA": "string",
            "MUNICIPIO": "string",
            "ESTACION": "Int64",
            "MAGNITUD": "Int64",
            "PUNTO_MUESTREO": "string",
            "ANO": "Int64",
            "MES": "Int64",
        },
        low_memory=False,
    )

    filas, columnas = datos.shape

    logger.info("Lectura completada correctamente.")
    logger.info("Número de registros: %s", filas)
    logger.info("Número de columnas: %s", columnas)

    # -------------------------------------------------------------------------
    # 3. IDENTIFICACIÓN DE COLUMNAS
    # -------------------------------------------------------------------------

    columnas_base = [
        "PROVINCIA",
        "MUNICIPIO",
        "ESTACION",
        "MAGNITUD",
        "PUNTO_MUESTREO",
        "ANO",
        "MES",
    ]

    columnas_datos = [
        f"D{numero:02d}"
        for numero in range(1, 32)
    ]

    columnas_validez = [
        f"V{numero:02d}"
        for numero in range(1, 32)
    ]

    columnas_esperadas = (
        columnas_base
        + columnas_datos
        + columnas_validez
    )

    columnas_ausentes = [
        columna
        for columna in columnas_esperadas
        if columna not in datos.columns
    ]

    columnas_adicionales = [
        columna
        for columna in datos.columns
        if columna not in columnas_esperadas
    ]

    logger.info("Columnas base: %s", len(columnas_base))
    logger.info("Columnas Dxx: %s", len(columnas_datos))
    logger.info("Columnas Vxx: %s", len(columnas_validez))
    logger.info("Columnas esperadas totales: %s", len(columnas_esperadas))

    if columnas_ausentes:
        logger.warning(
            "Columnas esperadas ausentes: %s",
            columnas_ausentes,
        )
    else:
        logger.info("Están presentes todas las columnas esperadas.")

    if columnas_adicionales:
        logger.warning(
            "Columnas adicionales: %s",
            columnas_adicionales,
        )
    else:
        logger.info("No se han detectado columnas adicionales.")

    # -------------------------------------------------------------------------
    # 4. MUESTRA DEL DATASET
    # -------------------------------------------------------------------------

    muestra = datos.head(10).copy()

    guardar_csv(
        muestra,
        "01_muestra_raw.csv",
        logger,
    )

    logger.info("Primeros cinco registros:")
    logger.info("\n%s", datos.head().to_string(index=False))

    # -------------------------------------------------------------------------
    # 5. PERFIL DE COLUMNAS
    # -------------------------------------------------------------------------

    perfil_columnas = pd.DataFrame(
        {
            "COLUMNA": datos.columns,
            "TIPO": [
                str(datos[columna].dtype)
                for columna in datos.columns
            ],
            "NULOS": [
                int(datos[columna].isna().sum())
                for columna in datos.columns
            ],
            "PORCENTAJE_NULOS": [
                round(
                    datos[columna].isna().mean() * 100,
                    4,
                )
                for columna in datos.columns
            ],
            "VALORES_UNICOS": [
                int(datos[columna].nunique(dropna=True))
                for columna in datos.columns
            ],
        }
    )

    guardar_csv(
        perfil_columnas,
        "02_perfil_columnas_raw.csv",
        logger,
    )

    total_nulos = int(datos.isna().sum().sum())

    logger.info("Número total de valores nulos: %s", total_nulos)

    # -------------------------------------------------------------------------
    # 6. DUPLICADOS
    # -------------------------------------------------------------------------

    duplicados_completos = int(datos.duplicated().sum())

    clave_mensual = [
        "PUNTO_MUESTREO",
        "ANO",
        "MES",
    ]

    duplicados_clave = int(
        datos.duplicated(
            subset=clave_mensual,
            keep=False,
        ).sum()
    )

    logger.info(
        "Filas completamente duplicadas: %s",
        duplicados_completos,
    )
    logger.info(
        "Filas implicadas en duplicados de clave mensual: %s",
        duplicados_clave,
    )

    if duplicados_completos > 0:
        guardar_csv(
            datos[datos.duplicated(keep=False)].copy(),
            "03_duplicados_completos_raw.csv",
            logger,
        )
    else:
        guardar_csv(
            pd.DataFrame(columns=datos.columns),
            "03_duplicados_completos_raw.csv",
            logger,
        )

    # -------------------------------------------------------------------------
    # 7. RESUMEN DE DIMENSIONES DEL DATASET
    # -------------------------------------------------------------------------

    resumen_dimensiones = pd.DataFrame(
        {
            "METRICA": [
                "registros",
                "columnas",
                "provincias",
                "municipios",
                "estaciones",
                "magnitudes",
                "puntos_muestreo",
                "anios",
                "meses",
                "nulos_totales",
                "duplicados_completos",
                "filas_duplicadas_clave_mensual",
            ],
            "VALOR": [
                filas,
                columnas,
                datos["PROVINCIA"].nunique(dropna=True),
                datos["MUNICIPIO"].nunique(dropna=True),
                datos["ESTACION"].nunique(dropna=True),
                datos["MAGNITUD"].nunique(dropna=True),
                datos["PUNTO_MUESTREO"].nunique(dropna=True),
                datos["ANO"].nunique(dropna=True),
                datos["MES"].nunique(dropna=True),
                total_nulos,
                duplicados_completos,
                duplicados_clave,
            ],
        }
    )

    guardar_csv(
        resumen_dimensiones,
        "04_resumen_dimensiones_raw.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 8. DISTRIBUCIÓN DE REGISTROS
    # -------------------------------------------------------------------------

    resumen_estaciones = (
        datos.groupby(
            ["ESTACION"],
            dropna=False,
        )
        .size()
        .reset_index(name="REGISTROS_MENSUALES")
        .sort_values(
            ["REGISTROS_MENSUALES", "ESTACION"],
            ascending=[False, True],
        )
    )

    guardar_csv(
        resumen_estaciones,
        "05_registros_por_estacion_raw.csv",
        logger,
    )

    resumen_magnitudes = (
        datos.groupby(
            ["MAGNITUD"],
            dropna=False,
        )
        .size()
        .reset_index(name="REGISTROS_MENSUALES")
        .sort_values(
            ["REGISTROS_MENSUALES", "MAGNITUD"],
            ascending=[False, True],
        )
    )

    guardar_csv(
        resumen_magnitudes,
        "06_registros_por_magnitud_raw.csv",
        logger,
    )

    resumen_meses = (
        datos.groupby(
            ["ANO", "MES"],
            dropna=False,
        )
        .size()
        .reset_index(name="REGISTROS")
        .sort_values(["ANO", "MES"])
    )

    guardar_csv(
        resumen_meses,
        "07_registros_por_mes_raw.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 9. CONVERSIÓN TEMPORAL A FORMATO LARGO
    # -------------------------------------------------------------------------

    logger.info("Convirtiendo temporalmente el dataset a formato largo...")

    datos_largos = convertir_formato_largo(
        datos,
        columnas_base,
    )

    filas_largas = len(datos_largos)

    logger.info(
        "Filas generadas en formato largo: %s",
        filas_largas,
    )

    # -------------------------------------------------------------------------
    # 10. INSPECCIÓN DE INDICADORES DE VALIDEZ
    # -------------------------------------------------------------------------

    indicadores_validez = (
        datos_largos["VALIDO"]
        .fillna("<NULO>")
        .value_counts(dropna=False)
        .rename_axis("INDICADOR")
        .reset_index(name="REGISTROS")
    )

    indicadores_validez["PORCENTAJE"] = (
        indicadores_validez["REGISTROS"]
        / filas_largas
        * 100
    ).round(4)

    guardar_csv(
        indicadores_validez,
        "08_indicadores_validez_raw.csv",
        logger,
    )

    indicadores_encontrados = sorted(
        datos_largos["VALIDO"]
        .dropna()
        .unique()
        .tolist()
    )

    logger.info(
        "Indicadores de validez encontrados: %s",
        indicadores_encontrados,
    )

    # -------------------------------------------------------------------------
    # 11. FECHAS IMPOSIBLES
    # -------------------------------------------------------------------------

    fechas_imposibles = datos_largos.loc[
        ~datos_largos["FECHA_CALENDARIO_VALIDA"]
    ].copy()

    guardar_csv(
        fechas_imposibles,
        "09_fechas_imposibles_raw.csv",
        logger,
    )

    logger.info(
        "Registros correspondientes a fechas imposibles: %s",
        len(fechas_imposibles),
    )

    # -------------------------------------------------------------------------
    # 12. MEDICIONES VÁLIDAS E INVÁLIDAS
    # -------------------------------------------------------------------------

    mediciones_validas = datos_largos.loc[
        datos_largos["FECHA_CALENDARIO_VALIDA"]
        & datos_largos["VALIDO"].eq("V")
        & datos_largos["VALOR"].notna()
    ].copy()

    mediciones_no_validas = datos_largos.loc[
        datos_largos["FECHA_CALENDARIO_VALIDA"]
        & ~datos_largos["VALIDO"].eq("V")
    ].copy()

    logger.info(
        "Mediciones válidas con fecha válida: %s",
        len(mediciones_validas),
    )
    logger.info(
        "Registros con fecha válida pero indicador distinto de V: %s",
        len(mediciones_no_validas),
    )

    # Solo se guarda una muestra para no generar una copia procesada
    # durante la fase de inspección.

    guardar_csv(
        mediciones_validas.head(100),
        "10_muestra_mediciones_validas_raw.csv",
        logger,
    )

    guardar_csv(
        mediciones_no_validas.head(100),
        "11_muestra_mediciones_no_validas_raw.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 13. ESTADÍSTICOS DE MEDICIONES VÁLIDAS
    # -------------------------------------------------------------------------

    if mediciones_validas.empty:
        logger.warning(
            "No hay mediciones válidas para calcular estadísticos."
        )

        estadisticos_magnitud = pd.DataFrame(
            columns=[
                "MAGNITUD",
                "REGISTROS",
                "MEDIA",
                "DESVIACION",
                "MINIMO",
                "Q1",
                "MEDIANA",
                "Q3",
                "MAXIMO",
            ]
        )

    else:
        estadisticos_magnitud = (
            mediciones_validas.groupby(
                "MAGNITUD",
                dropna=False,
            )["VALOR"]
            .agg(
                REGISTROS="count",
                MEDIA="mean",
                DESVIACION="std",
                MINIMO="min",
                Q1=lambda serie: serie.quantile(0.25),
                MEDIANA="median",
                Q3=lambda serie: serie.quantile(0.75),
                MAXIMO="max",
            )
            .reset_index()
        )

        columnas_redondeo = [
            "MEDIA",
            "DESVIACION",
            "MINIMO",
            "Q1",
            "MEDIANA",
            "Q3",
            "MAXIMO",
        ]

        estadisticos_magnitud[columnas_redondeo] = (
            estadisticos_magnitud[columnas_redondeo]
            .round(4)
        )

    guardar_csv(
        estadisticos_magnitud,
        "12_estadisticos_por_magnitud_raw.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 14. POSIBLES CASOS PROBLEMÁTICOS
    # -------------------------------------------------------------------------

    valores_negativos = mediciones_validas.loc[
        mediciones_validas["VALOR"] < 0
    ].copy()

    guardar_csv(
        valores_negativos,
        "13_valores_negativos_validos_raw.csv",
        logger,
    )

    ceros_validos = mediciones_validas.loc[
        mediciones_validas["VALOR"] == 0
    ].copy()

    guardar_csv(
        ceros_validos,
        "14_ceros_marcados_validos_raw.csv",
        logger,
    )

    logger.info(
        "Valores negativos marcados como válidos: %s",
        len(valores_negativos),
    )
    logger.info(
        "Valores cero marcados como válidos: %s",
        len(ceros_validos),
    )

    # -------------------------------------------------------------------------
    # 15. COMPROBACIÓN DE DÍAS SEGÚN EL CALENDARIO
    # -------------------------------------------------------------------------

    calendario_mensual = []

    combinaciones = (
        datos[["ANO", "MES"]]
        .drop_duplicates()
        .sort_values(["ANO", "MES"])
    )

    for fila in combinaciones.itertuples(index=False):
        anio = int(fila.ANO)
        mes = int(fila.MES)

        dias_mes = calendar.monthrange(anio, mes)[1]

        calendario_mensual.append(
            {
                "ANO": anio,
                "MES": mes,
                "DIAS_CALENDARIO": dias_mes,
            }
        )

    calendario_df = pd.DataFrame(calendario_mensual)

    guardar_csv(
        calendario_df,
        "15_calendario_meses_dataset.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 16. RESUMEN JSON
    # -------------------------------------------------------------------------

    resumen_json = {
        "ejecucion": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": datetime.now().isoformat(),
        },
        "fichero": {
            "ruta": str(RAW),
            "tamano_bytes": tamano_bytes,
            "separador": ";",
            "codificacion_lectura": "utf-8-sig",
        },
        "estructura": {
            "registros_raw": filas,
            "columnas_raw": columnas,
            "columnas_base": len(columnas_base),
            "columnas_datos": len(columnas_datos),
            "columnas_validez": len(columnas_validez),
            "columnas_ausentes": columnas_ausentes,
            "columnas_adicionales": columnas_adicionales,
        },
        "calidad": {
            "nulos_totales": total_nulos,
            "duplicados_completos": duplicados_completos,
            "filas_duplicadas_clave_mensual": duplicados_clave,
            "filas_formato_largo": filas_largas,
            "fechas_imposibles": len(fechas_imposibles),
            "mediciones_validas": len(mediciones_validas),
            "mediciones_no_validas": len(mediciones_no_validas),
            "valores_negativos_validos": len(valores_negativos),
            "ceros_marcados_validos": len(ceros_validos),
            "indicadores_validez": indicadores_encontrados,
        },
        "dimensiones": {
            "provincias": int(
                datos["PROVINCIA"].nunique(dropna=True)
            ),
            "municipios": int(
                datos["MUNICIPIO"].nunique(dropna=True)
            ),
            "estaciones": int(
                datos["ESTACION"].nunique(dropna=True)
            ),
            "magnitudes": int(
                datos["MAGNITUD"].nunique(dropna=True)
            ),
            "puntos_muestreo": int(
                datos["PUNTO_MUESTREO"].nunique(dropna=True)
            ),
            "anios": sorted(
                [
                    int(valor)
                    for valor in datos["ANO"].dropna().unique()
                ]
            ),
            "meses": sorted(
                [
                    int(valor)
                    for valor in datos["MES"].dropna().unique()
                ]
            ),
        },
    }

    guardar_json(
        resumen_json,
        "01_resumen_inspeccion_raw.json",
        logger,
    )

    # -------------------------------------------------------------------------
    # 17. FINALIZACIÓN
    # -------------------------------------------------------------------------

    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()

    logger.info("=" * 79)
    logger.info("INSPECCIÓN COMPLETADA CORRECTAMENTE")
    logger.info("Duración: %.2f segundos", duracion)
    logger.info("El fichero RAW no ha sido modificado.")
    logger.info("=" * 79)


if __name__ == "__main__":
    try:
        main()

    except Exception:
        logging.exception(
            "La inspección ha terminado con un error no controlado."
        )
        raise

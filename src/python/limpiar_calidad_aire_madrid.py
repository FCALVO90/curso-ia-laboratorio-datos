#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Limpieza del dataset de calidad del aire de Madrid.

ENTRADA
-------
datos/raw/aire_madrid/calidad_aire_madrid.csv

SALIDA PRINCIPAL
----------------
datos/processed/aire_madrid/calidad_aire_madrid_procesado.csv

EVIDENCIAS
----------
salidas/aire_madrid/python/csv/
salidas/aire_madrid/python/json/
salidas/aire_madrid/python/logs/

CRITERIOS
---------
- El RAW nunca se modifica.
- Se transforma el formato ancho D01/V01 ... D31/V31 a formato largo.
- Se construye una observación por fecha, estación, magnitud y punto de muestreo.
- Se descartan fechas imposibles.
- Solo se conservan mediciones marcadas como V.
- Los valores se convierten a numérico.
- Los duplicados exactos se eliminan.
- Los posibles atípicos se detectan mediante IQR dentro de cada magnitud.
- Los atípicos NO se eliminan: quedan marcados.
"""

from __future__ import annotations

import hashlib
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

RAW = (
    PROYECTO
    / "datos"
    / "raw"
    / "aire_madrid"
    / "calidad_aire_madrid.csv"
)

PROCESSED_DIR = (
    PROYECTO
    / "datos"
    / "processed"
    / "aire_madrid"
)

PROCESSED = (
    PROCESSED_DIR
    / "calidad_aire_madrid_procesado.csv"
)

SALIDA_BASE = (
    PROYECTO
    / "salidas"
    / "aire_madrid"
    / "python"
)

CSV_DIR = SALIDA_BASE / "csv"
JSON_DIR = SALIDA_BASE / "json"
LOG_DIR = SALIDA_BASE / "logs"

LOG_FILE = (
    LOG_DIR
    / "02_limpiar_calidad_aire_madrid.log"
)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def crear_directorios() -> None:
    """Crea únicamente los directorios de salida necesarios."""

    for directorio in [
        PROCESSED_DIR,
        CSV_DIR,
        JSON_DIR,
        LOG_DIR,
    ]:
        directorio.mkdir(
            parents=True,
            exist_ok=True,
        )


def configurar_logging() -> logging.Logger:
    """Configura logging simultáneo por consola y fichero."""

    logger = logging.getLogger(
        "limpieza_aire_madrid"
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


def sha256_fichero(
    ruta: Path,
) -> str:
    """Calcula SHA256 para demostrar integridad."""

    hash_obj = hashlib.sha256()

    with ruta.open("rb") as fichero:

        while True:

            bloque = fichero.read(
                1024 * 1024
            )

            if not bloque:
                break

            hash_obj.update(
                bloque
            )

    return hash_obj.hexdigest()


def guardar_csv(
    dataframe: pd.DataFrame,
    nombre: str,
    logger: logging.Logger,
) -> None:
    """Guarda una evidencia CSV."""

    ruta = CSV_DIR / nombre

    dataframe.to_csv(
        ruta,
        index=False,
        encoding="utf-8",
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
    """Guarda información estructurada como JSON."""

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


def transformar_a_largo(
    datos: pd.DataFrame,
) -> pd.DataFrame:
    """
    Transforma los 31 pares Dxx/Vxx
    en observaciones diarias.
    """

    columnas_identificacion = [
        "PROVINCIA",
        "MUNICIPIO",
        "ESTACION",
        "MAGNITUD",
        "PUNTO_MUESTREO",
        "ANO",
        "MES",
    ]

    bloques = []

    for dia in range(1, 32):

        sufijo = f"{dia:02d}"

        columna_valor = (
            f"D{sufijo}"
        )

        columna_validez = (
            f"V{sufijo}"
        )

        bloque = datos[
            columnas_identificacion
        ].copy()

        bloque["DIA"] = dia

        bloque["VALOR"] = pd.to_numeric(
            datos[columna_valor],
            errors="coerce",
        )

        bloque[
            "INDICADOR_VALIDEZ"
        ] = (
            datos[columna_validez]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        bloques.append(
            bloque
        )

    resultado = pd.concat(
        bloques,
        ignore_index=True,
    )

    return resultado


def detectar_atipicos_iqr(
    datos: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """
    Detecta posibles atípicos usando IQR.

    IMPORTANTE:
    El cálculo se realiza separadamente
    para cada magnitud.

    Los atípicos NO se eliminan.
    """

    datos = datos.copy()

    datos[
        "ES_ATIPICO_IQR"
    ] = False

    resumen = []

    for magnitud, grupo in datos.groupby(
        "MAGNITUD"
    ):

        q1 = grupo[
            "VALOR"
        ].quantile(0.25)

        q3 = grupo[
            "VALOR"
        ].quantile(0.75)

        iqr = q3 - q1

        limite_inferior = (
            q1 - 1.5 * iqr
        )

        limite_superior = (
            q3 + 1.5 * iqr
        )

        mascara = (
            (datos["MAGNITUD"] == magnitud)
            & (
                (
                    datos["VALOR"]
                    < limite_inferior
                )
                |
                (
                    datos["VALOR"]
                    > limite_superior
                )
            )
        )

        cantidad_atipicos = int(
            mascara.sum()
        )

        datos.loc[
            mascara,
            "ES_ATIPICO_IQR",
        ] = True

        resumen.append(
            {
                "MAGNITUD": int(magnitud),
                "Q1": round(
                    float(q1),
                    4,
                ),
                "Q3": round(
                    float(q3),
                    4,
                ),
                "IQR": round(
                    float(iqr),
                    4,
                ),
                "LIMITE_INFERIOR": round(
                    float(limite_inferior),
                    4,
                ),
                "LIMITE_SUPERIOR": round(
                    float(limite_superior),
                    4,
                ),
                "ATIPICOS": cantidad_atipicos,
                "REGISTROS": len(grupo),
            }
        )

    resumen_df = pd.DataFrame(
        resumen
    ).sort_values(
        "MAGNITUD"
    )

    return datos, resumen_df


# =============================================================================
# PROGRAMA PRINCIPAL
# =============================================================================

def main() -> None:

    crear_directorios()

    logger = configurar_logging()

    inicio = datetime.now()

    logger.info(
        "=" * 79
    )
    logger.info(
        "INICIO DE LA LIMPIEZA DEL DATASET DE CALIDAD DEL AIRE"
    )
    logger.info(
        "=" * 79
    )

    # -------------------------------------------------------------------------
    # 1. VERIFICACIÓN DEL RAW
    # -------------------------------------------------------------------------

    if not RAW.exists():

        raise FileNotFoundError(
            f"No existe el fichero RAW: {RAW}"
        )

    logger.info(
        "RAW: %s",
        RAW,
    )

    logger.info(
        "Processed: %s",
        PROCESSED,
    )

    hash_raw_antes = sha256_fichero(
        RAW
    )

    logger.info(
        "SHA256 RAW antes de limpiar: %s",
        hash_raw_antes,
    )

    # -------------------------------------------------------------------------
    # 2. LECTURA
    # -------------------------------------------------------------------------

    logger.info(
        "Leyendo fichero RAW..."
    )

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

    filas_raw = len(
        datos
    )

    columnas_raw = len(
        datos.columns
    )

    logger.info(
        "Registros RAW: %s",
        filas_raw,
    )

    logger.info(
        "Columnas RAW: %s",
        columnas_raw,
    )

    # -------------------------------------------------------------------------
    # 3. TRANSFORMACIÓN ANCHO -> LARGO
    # -------------------------------------------------------------------------

    logger.info(
        "Transformando D01/V01 ... D31/V31 a formato largo..."
    )

    largo = transformar_a_largo(
        datos
    )

    filas_largo = len(
        largo
    )

    logger.info(
        "Registros tras transformación a largo: %s",
        filas_largo,
    )

    # -------------------------------------------------------------------------
    # 4. CONSTRUCCIÓN DE FECHA
    # -------------------------------------------------------------------------

    logger.info(
        "Construyendo fecha diaria..."
    )

    largo["FECHA"] = pd.to_datetime(
        {
            "year": largo["ANO"],
            "month": largo["MES"],
            "day": largo["DIA"],
        },
        errors="coerce",
    )

    fechas_imposibles = (
        largo["FECHA"]
        .isna()
    )

    numero_fechas_imposibles = int(
        fechas_imposibles.sum()
    )

    logger.info(
        "Fechas imposibles detectadas: %s",
        numero_fechas_imposibles,
    )

    evidencia_fechas_imposibles = (
        largo.loc[
            fechas_imposibles
        ].copy()
    )

    guardar_csv(
        evidencia_fechas_imposibles,
        "16_fechas_imposibles_eliminadas.csv",
        logger,
    )

    # Eliminamos únicamente fechas
    # imposibles del calendario.

    limpio = largo.loc[
        ~fechas_imposibles
    ].copy()

    logger.info(
        "Registros tras eliminar fechas imposibles: %s",
        len(limpio),
    )

    # -------------------------------------------------------------------------
    # 5. INDICADORES DE VALIDEZ
    # -------------------------------------------------------------------------

    resumen_validez = (
        limpio[
            "INDICADOR_VALIDEZ"
        ]
        .fillna("<NULO>")
        .value_counts(
            dropna=False
        )
        .rename_axis(
            "INDICADOR_VALIDEZ"
        )
        .reset_index(
            name="REGISTROS"
        )
    )

    guardar_csv(
        resumen_validez,
        "17_indicadores_validez_fechas_reales.csv",
        logger,
    )

    mascara_no_valida = (
        limpio[
            "INDICADOR_VALIDEZ"
        ]
        != "V"
    )

    no_validas = limpio.loc[
        mascara_no_valida
    ].copy()

    numero_no_validas = len(
        no_validas
    )

    logger.info(
        "Mediciones con fecha real pero no válidas: %s",
        numero_no_validas,
    )

    guardar_csv(
        no_validas,
        "18_mediciones_no_validas_eliminadas.csv",
        logger,
    )

    # Conservamos exclusivamente
    # mediciones marcadas con V.

    limpio = limpio.loc[
        ~mascara_no_valida
    ].copy()

    logger.info(
        "Registros después del filtro de validez: %s",
        len(limpio),
    )

    # -------------------------------------------------------------------------
    # 6. VALORES NUMÉRICOS
    # -------------------------------------------------------------------------

    limpio["VALOR"] = pd.to_numeric(
        limpio["VALOR"],
        errors="coerce",
    )

    valores_nulos = int(
        limpio[
            "VALOR"
        ]
        .isna()
        .sum()
    )

    logger.info(
        "Valores no numéricos/nulos después de conversión: %s",
        valores_nulos,
    )

    valores_no_numericos_df = (
        limpio.loc[
            limpio["VALOR"].isna()
        ].copy()
    )

    guardar_csv(
        valores_no_numericos_df,
        "19_valores_no_numericos_eliminados.csv",
        logger,
    )

    limpio = limpio.loc[
        limpio["VALOR"].notna()
    ].copy()

    # -------------------------------------------------------------------------
    # 7. DUPLICADOS
    # -------------------------------------------------------------------------

    clave_diaria = [
        "PROVINCIA",
        "MUNICIPIO",
        "ESTACION",
        "MAGNITUD",
        "PUNTO_MUESTREO",
        "FECHA",
    ]

    mascara_duplicados = (
        limpio.duplicated(
            subset=clave_diaria,
            keep="first",
        )
    )

    numero_duplicados = int(
        mascara_duplicados.sum()
    )

    logger.info(
        "Duplicados diarios detectados: %s",
        numero_duplicados,
    )

    duplicados = limpio.loc[
        mascara_duplicados
    ].copy()

    guardar_csv(
        duplicados,
        "20_duplicados_diarios_eliminados.csv",
        logger,
    )

    limpio = limpio.loc[
        ~mascara_duplicados
    ].copy()

    # -------------------------------------------------------------------------
    # 8. VALORES NEGATIVOS
    # -------------------------------------------------------------------------

    negativos = limpio.loc[
        limpio["VALOR"] < 0
    ].copy()

    numero_negativos = len(
        negativos
    )

    logger.info(
        "Valores negativos: %s",
        numero_negativos,
    )

    guardar_csv(
        negativos,
        "21_valores_negativos_detectados.csv",
        logger,
    )

    # No eliminamos automáticamente.
    # En nuestro diagnóstico previo no aparecieron
    # negativos marcados como válidos.

    # -------------------------------------------------------------------------
    # 9. DETECCIÓN DE ATÍPICOS
    # -------------------------------------------------------------------------

    logger.info(
        "Detectando posibles atípicos mediante IQR por magnitud..."
    )

    limpio, resumen_iqr = detectar_atipicos_iqr(
        limpio
    )

    numero_atipicos = int(
        limpio[
            "ES_ATIPICO_IQR"
        ].sum()
    )

    logger.info(
        "Posibles atípicos IQR detectados: %s",
        numero_atipicos,
    )

    logger.info(
        "Los posibles atípicos se CONSERVAN."
    )

    guardar_csv(
        resumen_iqr,
        "22_resumen_atipicos_iqr.csv",
        logger,
    )

    atipicos = limpio.loc[
        limpio[
            "ES_ATIPICO_IQR"
        ]
    ].copy()

    guardar_csv(
        atipicos,
        "23_atipicos_iqr_detectados.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 10. NORMALIZACIÓN DE NOMBRES
    # -------------------------------------------------------------------------

    limpio = limpio.rename(
        columns={
            "PROVINCIA": "provincia",
            "MUNICIPIO": "municipio",
            "ESTACION": "estacion",
            "MAGNITUD": "magnitud",
            "PUNTO_MUESTREO": "punto_muestreo",
            "ANO": "anio",
            "MES": "mes",
            "DIA": "dia",
            "FECHA": "fecha",
            "VALOR": "valor",
            "INDICADOR_VALIDEZ": "indicador_validez",
            "ES_ATIPICO_IQR": "es_atipico_iqr",
        }
    )

    columnas_finales = [
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

    limpio = limpio[
        columnas_finales
    ]

    # -------------------------------------------------------------------------
    # 11. ORDENACIÓN
    # -------------------------------------------------------------------------

    limpio = limpio.sort_values(
        by=[
            "fecha",
            "estacion",
            "magnitud",
            "punto_muestreo",
        ],
        kind="stable",
    ).reset_index(
        drop=True
    )

    # -------------------------------------------------------------------------
    # 12. VALIDACIONES PREVIAS A ESCRITURA
    # -------------------------------------------------------------------------

    filas_finales = len(
        limpio
    )

    logger.info(
        "Registros finales: %s",
        filas_finales,
    )

    if limpio["fecha"].isna().any():
        raise ValueError(
            "ERROR: quedan fechas nulas en el procesado."
        )

    if limpio["valor"].isna().any():
        raise ValueError(
            "ERROR: quedan valores nulos en el procesado."
        )

    if not limpio[
        "indicador_validez"
    ].eq("V").all():
        raise ValueError(
            "ERROR: existen registros no válidos en el procesado."
        )

    if limpio.duplicated(
        subset=[
            "punto_muestreo",
            "fecha",
        ]
    ).any():
        raise ValueError(
            "ERROR: existen duplicados de punto de muestreo y fecha."
        )

    logger.info(
        "Validaciones internas superadas."
    )

    # -------------------------------------------------------------------------
    # 13. GUARDADO DEL DATASET PROCESADO
    # -------------------------------------------------------------------------

    logger.info(
        "Escribiendo dataset procesado..."
    )

    limpio.to_csv(
        PROCESSED,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d",
    )

    logger.info(
        "Dataset procesado generado: %s",
        PROCESSED,
    )

    # -------------------------------------------------------------------------
    # 14. EVIDENCIAS DEL RESULTADO
    # -------------------------------------------------------------------------

    guardar_csv(
        limpio.head(100),
        "24_muestra_dataset_procesado.csv",
        logger,
    )

    resumen_magnitudes = (
        limpio.groupby(
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
            atipicos_iqr=(
                "es_atipico_iqr",
                "sum",
            ),
        )
        .reset_index()
    )

    resumen_magnitudes[
        [
            "media",
            "mediana",
            "minimo",
            "maximo",
        ]
    ] = (
        resumen_magnitudes[
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
        resumen_magnitudes,
        "25_resumen_dataset_procesado_por_magnitud.csv",
        logger,
    )

    resumen_mes = (
        limpio.groupby(
            [
                "anio",
                "mes",
            ]
        )
        .agg(
            mediciones=(
                "valor",
                "count",
            ),
            estaciones=(
                "estacion",
                "nunique",
            ),
            magnitudes=(
                "magnitud",
                "nunique",
            ),
        )
        .reset_index()
    )

    guardar_csv(
        resumen_mes,
        "26_resumen_dataset_procesado_por_mes.csv",
        logger,
    )

    # -------------------------------------------------------------------------
    # 15. INTEGRIDAD DEL RAW
    # -------------------------------------------------------------------------

    hash_raw_despues = sha256_fichero(
        RAW
    )

    raw_modificado = (
        hash_raw_antes
        != hash_raw_despues
    )

    logger.info(
        "SHA256 RAW después de limpiar: %s",
        hash_raw_despues,
    )

    if raw_modificado:

        raise RuntimeError(
            "ERROR CRÍTICO: el fichero RAW ha cambiado."
        )

    logger.info(
        "Integridad RAW comprobada: NO MODIFICADO."
    )

    # -------------------------------------------------------------------------
    # 16. RESUMEN JSON
    # -------------------------------------------------------------------------

    resumen = {
        "entrada": {
            "fichero": str(RAW),
            "registros": filas_raw,
            "columnas": columnas_raw,
            "sha256": hash_raw_antes,
        },

        "transformacion": {
            "registros_formato_largo": filas_largo,
            "fechas_imposibles_eliminadas":
                numero_fechas_imposibles,
            "mediciones_no_validas_eliminadas":
                numero_no_validas,
            "valores_no_numericos_eliminados":
                valores_nulos,
            "duplicados_eliminados":
                numero_duplicados,
            "valores_negativos_detectados":
                numero_negativos,
        },

        "atipicos": {
            "metodo": "IQR 1.5",
            "agrupacion": "magnitud",
            "detectados": numero_atipicos,
            "eliminados": 0,
            "criterio":
                "Se marcan pero se conservan para EDA.",
        },

        "salida": {
            "fichero": str(PROCESSED),
            "registros": filas_finales,
            "columnas": len(
                columnas_finales
            ),
            "columnas_finales":
                columnas_finales,
        },

        "integridad_raw": {
            "sha256_antes":
                hash_raw_antes,
            "sha256_despues":
                hash_raw_despues,
            "modificado":
                raw_modificado,
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
        "02_resumen_limpieza.json",
        logger,
    )

    # -------------------------------------------------------------------------
    # FINAL
    # -------------------------------------------------------------------------

    duracion = (
        datetime.now()
        - inicio
    ).total_seconds()

    logger.info(
        "=" * 79
    )

    logger.info(
        "LIMPIEZA COMPLETADA CORRECTAMENTE"
    )

    logger.info(
        "RAW: %s registros",
        filas_raw,
    )

    logger.info(
        "Formato largo: %s registros",
        filas_largo,
    )

    logger.info(
        "Procesado final: %s registros",
        filas_finales,
    )

    logger.info(
        "Atípicos conservados: %s",
        numero_atipicos,
    )

    logger.info(
        "Duración: %.2f segundos",
        duracion,
    )

    logger.info(
        "RAW NO MODIFICADO"
    )

    logger.info(
        "=" * 79
    )


if __name__ == "__main__":

    try:

        main()

    except Exception:

        logging.exception(
            "ERROR durante la limpieza."
        )

        raise

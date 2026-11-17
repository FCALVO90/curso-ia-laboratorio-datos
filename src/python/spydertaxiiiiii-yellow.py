#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 22:16:05 2026

@author: fcqdevadmin
"""

#!/usr/bin/env python3
"""
VISUALIZADOR GENERAL DE RESULTADOS DEL PROYECTO curso_ia
========================================================

Pensado para ejecutarse desde Spyder.

Este script NO modifica datos ni bases de datos.

Visualiza los resultados previamente generados en:

    salidas/
    ├── csvs/
    ├── json/
    ├── graficos/
    └── graficos_r/

Permite revisar:
- CSV generados por Python y R.
- Resúmenes JSON.
- Métricas de los modelos.
- Importancia de variables.
- Gráficos generados con Python.
- Gráficos generados con R.
"""

# =====================================================================
# 01. IMPORTS
# =====================================================================

from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


# =====================================================================
# 02. CONFIGURACIÓN
# =====================================================================

print("\n" + "=" * 75)
print(" VISUALIZADOR GENERAL DE RESULTADOS - CURSO IA")
print("=" * 75)


# Intentamos localizar automáticamente la raíz del proyecto.
# Esto permite ejecutarlo cómodamente desde Spyder.

PROJECT_DIR = Path.home() / "curso_ia"

SALIDAS_DIR = PROJECT_DIR / "salidas" / "taxi"

PYTHON_DIR = SALIDAS_DIR / "python"
R_DIR = SALIDAS_DIR / "r"

CSV_DIR = PYTHON_DIR / "csv"
JSON_DIR = PYTHON_DIR / "json"
GRAFICOS_PYTHON_DIR = PYTHON_DIR / "graficos"
GRAFICOS_R_DIR = R_DIR / "graficos"


print(f"[INFO] Proyecto         : {PROJECT_DIR}")
print(f"[INFO] Salidas          : {SALIDAS_DIR}")
print(f"[INFO] CSV              : {CSV_DIR}")
print(f"[INFO] JSON             : {JSON_DIR}")
print(f"[INFO] Gráficos Python  : {GRAFICOS_PYTHON_DIR}")
print(f"[INFO] Gráficos R       : {GRAFICOS_R_DIR}")


# =====================================================================
# 03. COMPROBACIÓN DE DIRECTORIOS
# =====================================================================

print("\n" + "=" * 75)
print(" 03. COMPROBACIÓN DE DIRECTORIOS")
print("=" * 75)


directorios = {
    "CSV": CSV_DIR,
    "JSON": JSON_DIR,
    "Python": GRAFICOS_PYTHON_DIR,
    "R": GRAFICOS_R_DIR,
}


for nombre, directorio in directorios.items():

    if directorio.exists():

        print(
            f"[OK] {nombre:<10} -> "
            f"{directorio}"
        )

    else:

        print(
            f"[WARN] No existe: "
            f"{directorio}"
        )


# =====================================================================
# 04. FUNCIONES AUXILIARES
# =====================================================================

def titulo(texto):
    """
    Imprime una cabecera claramente visible en consola.
    """

    print("\n" + "=" * 75)
    print(f" {texto}")
    print("=" * 75)


def mostrar_dataframe(df, nombre, filas=10):
    """
    Muestra información básica de un DataFrame.

    En Spyder, si ejecutamos:

        df

    desde la consola, podremos abrir también la variable
    mediante el Variable Explorer.
    """

    print(f"\n[DATAFRAME] {nombre}")

    print(
        f"[INFO] Dimensiones: "
        f"{df.shape[0]:,} filas x "
        f"{df.shape[1]} columnas"
    )

    print("[INFO] Columnas:")

    for numero, columna in enumerate(
        df.columns,
        start=1,
    ):

        print(
            f"       {numero:02d}. "
            f"{columna}"
        )

    print(
        f"\n[INFO] Primeras "
        f"{min(filas, len(df))} filas:"
    )

    print(
        df.head(filas).to_string(
            index=False
        )
    )


def mostrar_imagen(ruta):
    """
    Abre una imagen utilizando Matplotlib.

    En Spyder aparecerá en el panel Plots.
    """

    try:

        imagen = mpimg.imread(ruta)

        plt.figure(
            figsize=(12, 7)
        )

        plt.imshow(imagen)

        plt.axis("off")

        plt.title(
            ruta.name
        )

        plt.tight_layout()

        plt.show()

    except Exception as error:

        print(
            f"[ERROR] No puedo mostrar "
            f"{ruta.name}: {error}"
        )


# =====================================================================
# 05. INVENTARIO GENERAL
# =====================================================================

titulo("05. INVENTARIO DE RESULTADOS")


csv_files = sorted(
    CSV_DIR.glob("*.csv")
)

json_files = sorted(
    JSON_DIR.glob("*.json")
)

python_images = sorted(
    GRAFICOS_PYTHON_DIR.glob("*.png")
)

r_images = sorted(
    GRAFICOS_R_DIR.glob("*.png")
)


print(
    f"[INFO] CSV encontrados             : "
    f"{len(csv_files)}"
)

print(
    f"[INFO] JSON encontrados            : "
    f"{len(json_files)}"
)

print(
    f"[INFO] Gráficos Python encontrados : "
    f"{len(python_images)}"
)

print(
    f"[INFO] Gráficos R encontrados      : "
    f"{len(r_images)}"
)


# =====================================================================
# 06. CARGA DE TODOS LOS CSV
# =====================================================================

titulo("06. CARGA DE CSV")


# Guardamos todos los DataFrames en un diccionario.
# Así podemos acceder fácilmente a cualquiera desde Spyder.

dataframes = {}


for archivo in csv_files:

    print(
        f"\n[CSV] Cargando: "
        f"{archivo.name}"
    )

    try:

        df = pd.read_csv(
            archivo
        )

        dataframes[
            archivo.stem
        ] = df

        print(
            f"[OK] {len(df):,} filas x "
            f"{len(df.columns)} columnas"
        )

    except Exception as error:

        print(
            f"[ERROR] {archivo.name}: "
            f"{error}"
        )


print(
    f"\n[OK] DataFrames cargados: "
    f"{len(dataframes)}"
)


# =====================================================================
# 07. RESUMEN DE TODOS LOS CSV
# =====================================================================

titulo("07. RESUMEN DE TABLAS DISPONIBLES")


resumen_csv = []


for nombre, df in dataframes.items():

    resumen_csv.append(
        {
            "tabla": nombre,
            "filas": len(df),
            "columnas": len(df.columns),
        }
    )


resumen_csv = pd.DataFrame(
    resumen_csv
)


if not resumen_csv.empty:

    resumen_csv = resumen_csv.sort_values(
        "tabla"
    )

    print(
        resumen_csv.to_string(
            index=False
        )
    )


# =====================================================================
# 08. MOSTRAR LOS CSV MÁS IMPORTANTES
# =====================================================================

titulo("08. TABLAS IMPORTANTES")


# Buscamos automáticamente tablas relacionadas
# con métricas, modelos, importancias y coeficientes.

palabras_interes = [
    "metrica",
    "modelo",
    "importancia",
    "coeficiente",
    "odds",
    "confusion",
    "calibracion",
    "roc",
    "diagnostico",
    "residuo",
]


tablas_importantes = {}


for nombre, df in dataframes.items():

    nombre_lower = nombre.lower()

    if any(
        palabra in nombre_lower
        for palabra in palabras_interes
    ):

        tablas_importantes[
            nombre
        ] = df


print(
    f"[INFO] Tablas analíticas detectadas: "
    f"{len(tablas_importantes)}"
)


for nombre, df in tablas_importantes.items():

    print("\n" + "-" * 75)

    mostrar_dataframe(
        df,
        nombre,
        filas=min(
            20,
            len(df),
        ),
    )


# =====================================================================
# 09. JSON GENERADOS
# =====================================================================

titulo("09. RESÚMENES JSON")


json_data = {}


for archivo in json_files:

    print(
        f"\n[JSON] Cargando: "
        f"{archivo.name}"
    )

    try:

        with open(
            archivo,
            "r",
            encoding="utf-8",
        ) as fichero:

            datos = json.load(
                fichero
            )

        json_data[
            archivo.stem
        ] = datos

        print(
            json.dumps(
                datos,
                indent=4,
                ensure_ascii=False,
            )
        )

    except Exception as error:

        print(
            f"[ERROR] {archivo.name}: "
            f"{error}"
        )


# =====================================================================
# 10. MÉTRICAS PYTHON
# =====================================================================

titulo("10. MÉTRICAS DE LOS MODELOS PYTHON")


for nombre, df in dataframes.items():

    if (
        "python" in nombre.lower()
        and "metric" in nombre.lower()
    ):

        print(
            f"\n[MODELO PYTHON] "
            f"{nombre}"
        )

        print(
            df.to_string(
                index=False
            )
        )


# =====================================================================
# 11. MÉTRICAS R
# =====================================================================

titulo("11. MÉTRICAS DE LOS MODELOS R")


for nombre, df in dataframes.items():

    if (
        nombre.lower().endswith("_r")
        and "metric" in nombre.lower()
    ):

        print(
            f"\n[MODELO R] "
            f"{nombre}"
        )

        print(
            df.to_string(
                index=False
            )
        )


# =====================================================================
# 12. IMPORTANCIA DE VARIABLES PYTHON
# =====================================================================

titulo("12. IMPORTANCIA DE VARIABLES")


for nombre, df in dataframes.items():

    if "importancia" not in nombre.lower():
        continue

    print(
        f"\n[IMPORTANCIA] {nombre}"
    )

    print(
        df.head(20).to_string(
            index=False
        )
    )


# =====================================================================
# 13. COEFICIENTES Y ODDS RATIOS DE R
# =====================================================================

titulo("13. COEFICIENTES Y ODDS RATIOS DEL GLM")


for nombre, df in dataframes.items():

    if (
        "coeficiente" in nombre.lower()
        or "odds" in nombre.lower()
    ):

        print(
            f"\n[GLM] {nombre}"
        )

        print(
            df.head(30).to_string(
                index=False
            )
        )


# =====================================================================
# 14. MOSTRAR GRÁFICOS PYTHON
# =====================================================================

titulo("14. GRÁFICOS GENERADOS CON PYTHON")


if not python_images:

    print(
        "[WARN] No hay gráficos Python."
    )

else:

    for numero, imagen in enumerate(
        python_images,
        start=1,
    ):

        print(
            f"[GRAFICOHON] "
            f"{numero:02d}/{len(python_images):02d} "
            f"{imagen.name}"
        )

        mostrar_imagen(
            imagen
        )


# =====================================================================
# 15. MOSTRAR GRÁFICOS R
# =====================================================================

titulo("15. GRÁFICOS GENERADOS CON R")


if not r_images:

    print(
        "[WARN] No hay gráficos R."
    )

else:

    for numero, imagen in enumerate(
        r_images,
        start=1,
    ):

        print(
            f"[GRAFICO R] "
            f"{numero:02d}/{len(r_images):02d} "
            f"{imagen.name}"
        )

        mostrar_imagen(
            imagen
        )


# =====================================================================
# 16. COMPARACIÓN DE MÉTRICAS DISPONIBLES
# =====================================================================

titulo("16. COMPARACIÓN PYTHON / R")


metric_tables = []


for nombre, df in dataframes.items():

    if "metric" not in nombre.lower():
        continue

    temporal = df.copy()

    temporal.insert(
        0,
        "origen",
        nombre,
    )

    metric_tables.append(
        temporal
    )


if metric_tables:

    print(
        "[INFO] Se han encontrado "
        f"{len(metric_tables)} tablas de métricas."
    )

    for tabla in metric_tables:

        print("\n")
        print(
            tabla.to_string(
                index=False
            )
        )

else:

    print(
        "[WARN] No se encontraron "
        "tablas de métricas."
    )


# =====================================================================
# 17. VARIABLES DISPONIBLES EN SPYDER
# =====================================================================

titulo("17. VARIABLES DISPONIBLES EN SPYDER")


print(
    """
Después de ejecutar el script puedes utilizar el
Variable Explorer de Spyder.

Variables especialmente útiles:

    resumen_csv

        Inventario de todos los CSV.

    dataframes

        Diccionario con todos los CSV cargados.

    tablas_importantes

        Métricas, coeficientes, importancias,
        matrices de confusión, ROC, etc.

    json_data

        Todos los JSON cargados.

    python_images

        Lista de gráficos generados con Python.

    r_images

        Lista de gráficos generados con R.


Ejemplos desde la consola de Spyder:

    dataframes.keys()

    dataframes["01_resumen_mensual_python"]

    dataframes["06_metricas_glm_propina_r"]

    json_data.keys()
"""
)


# =====================================================================
# 18. RESUMEN FINAL
# =====================================================================

titulo("18. VISUALIZACIÓN FINALIZADA")


print(
    f"[OK] CSV cargados      : "
    f"{len(dataframes)}"
)

print(
    f"[OK] JSON cargados     : "
    f"{len(json_data)}"
)

print(
    f"[OK] Gráficos Python   : "
    f"{len(python_images)}"
)

print(
    f"[OK] Gráficos R        : "
    f"{len(r_images)}"
)

print(
    "\n[FIN] Todos los resultados disponibles "
    "han sido cargados para su revisión en Spyder."
)
# Curso IA - Laboratorio de Datos

Repositorio docente con datasets, código fuente, consultas, análisis,
visualizaciones y evidencias generadas durante las prácticas del curso.

## Estructura

- `datos/raw/` - datasets originales.
- `datos/processed/` - datasets procesados.
- `src/python/` - análisis y procesamiento con Python.
- `src/r/` - análisis con R.
- `src/queries/sql/` - consultas PostgreSQL y MariaDB.
- `src/queries/javascript/` - consultas MongoDB.
- `src/shell/` - automatización mediante Bash.
- `salidas/` - CSV, JSON, TXT, logs, gráficos PNG y HTML.

## Datasets principales

El repositorio incluye material relacionado con:

- NYC Taxi.
- Online Retail II.
- Calidad del aire de Madrid.
- MovieLens.
- Palmer Penguins.
- Wine Quality.
- SNAP Facebook.
- 20 Newsgroups.
- LogHub.

## Git LFS

El repositorio utiliza Git LFS para los ficheros de gran tamaño,
incluidos Parquet, XLSX, ZIP, TAR.GZ y determinados CSV.

### Instalación de Git LFS

En Ubuntu/WSL:

    sudo apt update
    sudo apt install git-lfs -y
    git lfs install

### Clonado del repositorio

    git clone URL_DEL_REPOSITORIO
    cd curso-ia-laboratorio-datos
    git lfs pull

## Credenciales

Las credenciales reales no se almacenan en el repositorio.

Se proporciona como plantilla:

    .env.credentials.example

Para crear una configuración local:

    cp .env.credentials.example .env.credentials

Después hay que editar `.env.credentials` y proporcionar las credenciales
de PostgreSQL y MariaDB correspondientes al entorno local.

El fichero `.env.credentials` está excluido de Git y nunca debe
versionarse.

## Tecnologías

El proyecto utiliza, entre otras:

- Python
- R
- Bash
- PostgreSQL
- MariaDB
- MongoDB
- Git
- Git LFS
- Apache Superset
- Metabase
- Grafana
- Docker
- WSL2

## Salidas generadas

Las prácticas generan evidencias reproducibles en distintos formatos:

- CSV
- JSON
- TXT
- logs
- gráficos PNG
- mapas HTML
- resultados SQL
- métricas de modelos

## Proyectos y prácticas

### Online Retail II

Procesamiento y análisis de datos de comercio electrónico utilizando
Python, R, PostgreSQL, MariaDB y MongoDB.

### NYC Taxi 2024

Procesamiento de los datos de NYC Taxi correspondientes a 2024,
incluyendo los ficheros Parquet mensuales.

Incluye:

- inspección de datos;
- análisis exploratorio;
- análisis temporal;
- análisis espacial;
- modelos estadísticos;
- visualizaciones;
- consultas PostgreSQL;
- automatización Bash.

### Calidad del aire de Madrid

Pipeline completo de calidad del dato y EDA sobre datos de calidad
del aire.

Flujo principal:

    RAW
      |
      v
    Inspección
      |
      v
    Limpieza
      |
      v
    Validación
      |
      +--> EDA Python
      |
      +--> EDA R
      |
      v
    PostgreSQL
      |
      v
    Vistas + consultas + exportaciones

El pipeline genera CSV, JSON, TXT, logs y gráficos PNG.

## Filosofía del repositorio

El repositorio está diseñado para permitir reproducir las prácticas,
examinar las distintas etapas del procesamiento y comparar varias
tecnologías trabajando sobre los mismos datasets.

Los datasets originales se conservan en `datos/raw/`.

Los procesos de transformación generan nuevos datasets dentro de
`datos/processed/`.

Las evidencias y resultados se almacenan dentro de `salidas/`.

## Uso docente

Repositorio preparado como material práctico para trabajar:

- ingeniería de datos;
- calidad del dato;
- análisis exploratorio;
- bases de datos SQL y NoSQL;
- programación Python y R;
- automatización;
- visualización de datos;
- modelado estadístico;
- reproducibilidad de pipelines.

## Seguridad

No deben incorporarse al repositorio:

- contraseñas reales;
- tokens;
- claves privadas;
- ficheros `.env`;
- `.pgpass`;
- credenciales personales.

Las configuraciones sensibles deben proporcionarse mediante variables
de entorno o ficheros locales excluidos mediante `.gitignore`.


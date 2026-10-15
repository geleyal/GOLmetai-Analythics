# GOLmetai Analytics

Prototipo gratuito de comparación de futbolistas mediante Streamlit, pandas y mplsoccer. Consulta StatsBomb Open Data para competiciones y partidos disponibles en el repositorio público.

## Funciones incluidas

- Buscador de competiciones/temporadas y partidos disponibles.
- Selección de dos jugadores.
- Filtro por periodo e intervalo de minutos.
- Tabla comparativa de métricas de eventos.
- Mapas de calor basados en coordenadas de eventos.
- Mapas de pases (completados y fallidos según el resultado registrado).
- Tabla descargable en CSV de los eventos filtrados.

## Requisitos

- Python 3.10–3.12 recomendado.
- Conexión a internet para consultar StatsBomb Open Data.
- No necesita clave API para la fuente abierta incluida.

## Ejecutar en PC

### Windows (PowerShell)

```powershell
cd golmetai_analytics
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Si PowerShell bloquea la activación, puedes usar CMD:

```bat
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
cd golmetai_analytics
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Streamlit abrirá la aplicación en el navegador, normalmente en `http://localhost:8501`.

## Ejecutar desde iPhone

La forma práctica es desplegarla en Streamlit Community Cloud desde un repositorio de GitHub. El iPhone puede usar la aplicación publicada desde Safari; no necesita instalar Python. Para editar código desde el iPhone se puede usar GitHub web, aunque es más cómodo desde un PC.

## Publicar gratis

1. Crea una cuenta en GitHub y un repositorio público llamado `golmetai-analytics`.
2. Sube todos los archivos de esta carpeta, incluyendo `app.py`, `requirements.txt`, `.streamlit/config.toml` y `README.md`.
3. Entra en <https://share.streamlit.io/> e inicia sesión con GitHub.
4. Pulsa **Create app**.
5. Selecciona el repositorio `golmetai-analytics`, la rama `main` y el archivo principal `app.py`.
6. En **Advanced settings**, selecciona una versión de Python compatible (por ejemplo, 3.12, si está disponible).
7. Pulsa **Deploy** y espera a que se instalen las dependencias.
8. Abre la URL `*.streamlit.app` desde el iPhone o PC.

El nivel gratuito y sus límites pueden cambiar. No subas tokens, contraseñas ni datos privados al repositorio.

## Fuente de datos y atribución

La app consulta los archivos públicos de <https://github.com/hudl/open-data>. La cobertura es limitada a las competiciones, temporadas y partidos que publica StatsBomb; no se incluyen todos los partidos profesionales. StatsBomb solicita atribución y el uso de su logo cuando se publican o distribuyen análisis basados en sus datos. Consulta los términos vigentes del repositorio antes de publicar.

## Limitaciones de interpretación

- El mapa de calor representa la distribución de los eventos con coordenadas, no la ubicación continua del jugador durante todo el partido.
- Las definiciones de tiros a puerta, entradas, pérdidas y otras métricas pueden variar entre proveedores.
- En esta primera versión, los datos se descargan del repositorio abierto; todavía no hay una API universal para consultar cualquier partido.
- El reloj de los eventos y los minutos añadidos dependen del proveedor. Comprueba el periodo y los minutos en la tabla de eventos antes de publicar una cifra.

## Estructura

```text
golmetai_analytics/
├── app.py
├── requirements.txt
├── README.md
└── .streamlit/
    └── config.toml
```

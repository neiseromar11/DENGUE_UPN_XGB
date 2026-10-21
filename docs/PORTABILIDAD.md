# Mover y ejecutar DengueML UPN

## Forma recomendada en Windows

1. Copiar `dist/DengueML_UPN_trasladable.zip` a la carpeta, USB o computadora de destino.
2. Extraer todo el ZIP; no ejecutar dentro del archivo comprimido.
3. Tener Python 3.11 o 3.12 de **64 bits**, con pip y venv. Si falta, instalarlo desde https://www.python.org/downloads/ y marcar **Add Python to PATH**.
4. Abrir `INICIAR_WINDOWS.bat`. Instala las dependencias en el primer inicio y ejecuta el dashboard. Se necesita Internet para esa instalación.
5. Abrir `http://localhost:8501` si el navegador no se abre automáticamente. Mantener abierta la consola; `Ctrl+C` detiene el sistema.

El proyecto no depende de la ruta de Neiser ni de Codex. En cada ubicación el iniciador prepara un entorno propio en `.runtime-envs/`. No se requiere activar el entorno a mano. Se conservan los datos y el método ya publicados: no es necesario volver a entrenar para visualizar el dashboard.

No es un ejecutable autónomo sin requisitos: Python y sus bibliotecas siguen siendo necesarios. El iniciador automatiza su preparación. La primera instalación y una nueva ubicación pueden tardar varios minutos; los siguientes inicios reutilizan el entorno. La ejecución se comprobó en Windows con Python 3.11; Linux/macOS y Python 3.12 requieren validación en el equipo de destino.

## Crear un ZIP actualizado

Desde la carpeta del proyecto, con Python:

```powershell
python empaquetar.py
```

Genera `dist/DengueML_UPN_trasladable.zip`. Incluye `src`, documentación, pruebas, iniciadores, dependencias y la publicación activa completa. No incluye `.git`, `.env`, logs, entornos, informes de Word ni el CSV crudo. No hay credenciales requeridas para consultar el dashboard.

Para trasladar también el CSV original y poder repetir el ETL desde esa fuente:

```powershell
python empaquetar.py --incluir-fuente
```

También se puede copiar toda la carpeta `capstone_dengue`, omitiendo `.runtime-envs`, `.venv`, `__pycache__` y `dist`. Nunca copiar solamente `src`: faltarán los datos y la publicación. No borrar la carpeta original hasta comprobar la copia.

## Opciones de inicio

```powershell
.\INICIAR_WINDOWS.bat --solo-instalar
.\INICIAR_WINDOWS.bat --puerto 8502
```

El segundo comando resuelve un puerto 8501 ocupado. Para elegir un Python instalado en otra ubicación:

```powershell
$env:DENGUEML_PYTHON = 'D:\Herramientas\Python311\python.exe'
.\INICIAR_WINDOWS.bat
```

En macOS/Linux, con Python compatible y `venv` instalado: `python3 iniciar.py`. La resolución de paquetes binarios y librerías del sistema depende de la plataforma; esta ruta no se ha probado aquí. El servidor escucha en `127.0.0.1`: moverlo no publica automáticamente una web en Internet.

## Sin Internet

Después de una instalación correcta, se puede usar el dashboard sin Internet en esa misma ubicación. Para preparar una instalación nueva sin conexión, descargar previamente las ruedas en un equipo con **el mismo sistema, arquitectura y versión menor de Python**:

```powershell
python -m pip download --only-binary=:all: -r requirements-lock.txt -d wheelhouse
```

Copiar `wheelhouse` junto a `iniciar.py` en el destino y ejecutar:

```powershell
.\INICIAR_WINDOWS.bat --offline
```

Python debe estar instalado previamente. El ZIP generado no incluye `wheelhouse`: se copia por separado. No se ha preparado un paquete de ruedas sin conexión en esta entrega.

## Actualizar datos o ejecutar pruebas

El iniciador imprime la ruta **Python del proyecto**. Usar ese ejecutable para ejecutar comandos de mantenimiento, por ejemplo (sustituir `<clave>` por la carpeta real):

```powershell
& '.\.runtime-envs\<clave>\Scripts\python.exe' src/etl.py datos_abiertos_vigilancia_dengue.csv --desde 2023
& '.\.runtime-envs\<clave>\Scripts\python.exe' src/train.py data/versions/<version>/metadata.json
& '.\.runtime-envs\<clave>\Scripts\python.exe' -m pytest tests -q
```

Copiar la ruta `metadata.json` que devuelve el ETL. El lote debe ser un histórico completo; no se deben concatenar casos sin identificador. Generar un nuevo ZIP después de publicar una actualización para llevar esa versión a otro equipo.

## Si falla

| Mensaje o situación | Acción |
|---|---|
| No se encuentra Python | Instalar Python compatible o definir `DENGUEML_PYTHON`. |
| Falla pip o una descarga | Comprobar conexión/proxy y volver a iniciar; una instalación fallida no se marca como completa. |
| Falta un archivo publicado | Extraer nuevamente todo el ZIP, incluyendo `data` y `models`. |
| Huella no coincide | Recuperar la publicación original; no editar a mano los datos/modelos versionados. |
| Puerto ocupado | Usar `--puerto 8502`. |
| No puede escribir en la carpeta | Extraer a una carpeta propia con permisos de escritura. |
| El entorno local quedó dañado | Cerrar el sistema y renombrar `.runtime-envs` como respaldo; al iniciar se crea uno nuevo. |

Se conserva el baseline seleccionado y el corte de datos existente. Trasladar el proyecto no actualiza el histórico ni mejora automáticamente el modelo.

Referencias: [entornos virtuales de Python](https://docs.python.org/3/library/venv.html) y [ejecución de Streamlit](https://docs.streamlit.io/develop/concepts/architecture/run-your-app). Los entornos virtuales deben recrearse al trasladarse; por eso se distribuye el proyecto con instrucciones reproducibles, no un venv copiado.

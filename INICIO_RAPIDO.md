# DengueML-UPN: inicio rápido

Necesitas **Python 3.11 o 3.12 de 64 bits** (con pip y venv). Todo lo demás se instala solo.

| Sistema | Qué hacer |
|---|---|
| **Windows** | Doble clic en `INICIAR_WINDOWS.bat` |
| **macOS / Linux** | En la terminal: `chmod +x INICIAR_MAC_LINUX.sh` y luego `./INICIAR_MAC_LINUX.sh` |
| **Cualquier equipo con Docker** | `docker build -t dengueml .` y `docker run -p 8501:8501 dengueml` |

Se abre el navegador en `http://localhost:8501`. La primera vez tarda unos minutos porque crea su entorno e instala las librerías.

* **Sin Internet:** si la carpeta incluye `wheelhouse/` (paquete «completo»), se instala desde ahí. Debe ser el mismo sistema operativo y versión de Python con que se preparó.
* **Puerto ocupado:** `INICIAR_WINDOWS.bat --puerto 8502`.
* **Otro dispositivo en la misma red:** ejecutar con `streamlit run src/app.py --server.address=0.0.0.0` y abrir `http://IP-del-equipo:8501`.
* **Tablet o celular:** no se instala nada; se abre la dirección de un equipo en la red o la de una nube (ver `docs/PORTABILIDAD.md`).
* Si algo falla: `docs/PORTABILIDAD.md`, sección «Si falla».

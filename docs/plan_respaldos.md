# Plan de Respaldos – DengueML-UPN

## Objetivo

Garantizar la disponibilidad y recuperación de los archivos y datos críticos del proyecto DengueML-UPN ante posibles pérdidas o daños.

## Alcance

- Código fuente del proyecto
- Datasets procesados
- Archivos de configuración
- Documentación del proyecto
- Logs de auditoría (cuando contengan información relevante para investigación)

## Estrategia de Respaldo

| Elemento | Método | Frecuencia | Destino |
|---|---|---|---|
| Código fuente | Git (GitHub) | Cada commit | Repositorio remoto |
| Datasets procesados | Copia manual | Diaria (durante desarrollo activo) | Almacenamiento externo separado |
| Archivos de configuración | Copia manual | Semanal | Almacenamiento externo separado |
| Documentación | Git (GitHub) | Cada commit | Repositorio remoto |

## Responsable

- **Responsable del respaldo:** Líder / Coordinador del proyecto.
- **Responsable de verificación:** Cualquier miembro del equipo asignado.

## Indicadores de Recuperación

| Indicador | Meta |
|---|---|
| **RPO** (Recovery Point Objective) | 24 horas |
| **RTO** (Recovery Time Objective) | 4 horas |

> **Nota:** Estos valores son metas del plan de seguridad, no resultados medidos.

## Pruebas de Restauración

- Se recomienda realizar una prueba de restauración al menos una vez por sprint o incremento.
- La prueba debe verificar que los datos restaurados son íntegros y que la aplicación puede ejecutarse correctamente tras la restauración.

## Almacenamiento

- Los respaldos deben almacenarse en una ubicación **separada** del repositorio principal.
- Opciones recomendadas: disco externo, servicio de almacenamiento en la nube (Google Drive, OneDrive), o servidor institucional.
- No almacenar respaldos dentro del mismo repositorio Git.

## Exclusiones

- No se respaldan archivos temporales (`__pycache__/`, `*.pyc`).
- No se respaldan entornos virtuales (`.venv/`, `venv/`).
- No se respaldan archivos de IDE (`.idea/`, `.vscode/`).

---

*Plan mantenido por el equipo DengueML-UPN · Universidad Privada del Norte*

# Checklist de Seguridad – DengueML-UPN

Última revisión: 20/09/2026

## Gestión de Secretos

- [x] No existen contraseñas en el código fuente.
- [x] No existen tokens en el repositorio.
- [x] `.env` está incluido en `.gitignore`.
- [x] `.env.example` no contiene secretos reales.

## Logs y Auditoría

- [x] Los logs no contienen información sensible (contraseñas, DNI, tokens).
- [x] Se mantiene trazabilidad de eventos relevantes del sistema.
- [x] La carpeta `logs/` está ignorada por Git.

## Manejo de Errores

- [x] El dashboard maneja errores de forma segura (mensajes genéricos al usuario).
- [x] No se exponen rutas internas ni stack traces al usuario.

## Validación de Entradas

- [x] Las entradas principales del dashboard están validadas (periodo, distrito, horizonte, semana).
- [x] No se permiten valores fuera del rango configurado.

## Datos

- [x] El dataset fuente no se versiona en Git.
- [x] El dashboard trabaja con información agregada, sin datos personales.

## Respaldo

- [x] Existe un plan de respaldo documentado (`docs/plan_respaldos.md`).

## Dependencias

- [x] Las dependencias están listadas en `requirements.txt`.
- [ ] Se ha ejecutado un análisis de vulnerabilidades de dependencias.

## Autenticación

- [ ] Se ha implementado autenticación basada en roles.
  - *Estado: planificada para una versión posterior.*

## Pendientes

- [ ] Implementar autenticación y control de acceso.
- [ ] Ejecutar auditoría de dependencias con `pip audit` o `safety check`.
- [ ] Realizar prueba documentada de restauración de respaldos.
- [ ] Configurar HTTPS para despliegue en producción.

---

*Checklist mantenido por el equipo DengueML-UPN · Universidad Privada del Norte*

Fase 0 — Interno (demos y test)
Objetivo: Validar el backfill y los refactors en un entorno controlado y detectar edge cases no cubiertos por la batería de pruebas.
Acciones:
Ejecutar el script de migración en tenant demos mx.
Activar core_vacaciones_eliminar_vacation_config y core_vacacion_feature_mantener_proporcion_mx en tenant demo mx.
Activar habilitar_fecha_reconocimiento_antiguedad en tenant demo mx.
Validar con los criterios de éxito de corto plazo (ver sección b).
Ejecutar la batería de pruebas completa.
Tiempo estimado en interno: 1 sprint (~2 semanas) para recibir feedback y corregir issues.
Hito para avanzar: 0 errores en Sentry, backfill sin inconsistencias..

Fase 1 — Ola de activación 1: Clientes con sin asignaciones de vacaciones
Objetivo: Medir criterios de éxito con datos reales y detectar edge cases no cubiertos por la batería de pruebas.

Segmento: 136 Clientes MX cuyos colaboradores tienen 0 asignaciones.
Criterio de avance: Sin incremento de errores en Sentry ni tickets relacionados con vacaciones durante 7 días. Y resultados del script de migración sin inconsistencias.
Monitoreo: Revisión inmediata luego de correr el script y monitoreo diario de sentry para los que queden activos.
Fase 2 — Clientes Beta y Ola de activación 2: Clientes con configuraciones simples
Objetivo: Medir criterios de éxito con datos reales y detectar edge cases no cubiertos por la batería de pruebas.

Segmento: 429 Clientes MX cuyos colaboradores tienen 0 asignaciones con fecha de inicio de cálculo anterior al ingreso a la compañía y 0 asignaciones con fecha de inicio de cálculo posterior al ingreso a la compañía, o al menos un número pequeño, que en su mayoría sean fechas de inicio de cálculo iguales al ingreso.
Criterio de avance: Sin incremento de errores en Sentry ni tickets relacionados con vacaciones durante 7 días. Y resultados del script de migración sin inconsistencias.
Monitoreo: Revisión inmediata luego de correr el script y monitoreo diario de sentry para los que queden activos.

Fase 3 — Ola de activación 3: Clientes con configuraciones medianamente complejas
Objetivo: Migrar un grupo un poco más complejo y seguir midiendo criterios de éxito con datos reales y detectar edge cases no cubiertos por la ola anterior.

Segmento: 158 Clientes con 0 asignaciones con fecha de inicio del cálculo anterior al ingreso, y la mayoría de sus asignaciones con fechas de inicio de cálculo posterior o igual al ingreso a la compañía.
Preparación adicional: Revisión manual de una muestra representativa del resultado la migración en estos clientes antes de activar.
Criterio de avance: Resultados del script de migración sin inconsistencias y sin sentrys relacionados.
Hito de cierre de mes: Esperar el cierre del periodo de nómina correspondiente para validar criterios de éxito.

Fase 3 — Ola de activación 3: Clientes con configuraciones complejas
Objetivo: Migrar el grupo más complejo y seguir midiendo criterios de éxito con datos reales y detectar edge cases no cubiertos por la ola anterior.

Segmento: 222 Clientes con la mayoría de sus asignaciones con fechas de inicio de cálculo anterior al ingreso a la compañía.
Preparación adicional: Revisión manual de una muestra representativa del resultado de la migración en estos clientes antes de activar.
Criterio de avance: Resultados del script de migración sin inconsistencias y sin sentrys relacionados.
Hito de cierre de mes: Esperar el cierre del periodo de nómina correspondiente para validar criterios de éxito.

Activación al 100%
Una vez completada la Fase 3 sin incidentes, activar las FFs al 100% para todos los clientes MX.
Comunicar a los equipos de Ítems MX, Certificados MX y Finiquitos MX la activación completa.

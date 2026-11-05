---
name: spec-driven-development
description: Aplica un flujo de Spec-Driven Development (SDD) para planificar, especificar, implementar y validar funcionalidades con agentes de IA. Úsala al iniciar un proyecto, añadir una funcionalidad, cambiar requisitos o cuando se solicite trabajar con SDD.
---

# Skill: Spec-Driven Development (SDD)

## Propósito

Desarrollar software a partir de especificaciones explícitas y verificables, en lugar de pasar directamente de una idea a la generación de código.

El agente ayuda a analizar, proponer y ejecutar el trabajo, pero la persona responsable revisa las decisiones y aprueba los artefactos clave antes de avanzar.

Principio central:

**Requisitos → especificación → clarificación → plan técnico → tareas → implementación → validación → iteración.**

No trates los documentos como burocracia ni como garantía automática de calidad. Deben mantener una relación verificable entre lo que se necesita, las decisiones técnicas, el código y las pruebas.

## Cuándo usar esta skill

Actívala cuando se solicite:

- Crear un proyecto nuevo con SDD.
- Diseñar o implementar una funcionalidad.
- Modificar requisitos existentes.
- Revisar una especificación, un plan o una lista de tareas.
- Validar si una implementación cumple una especificación.

No impongas el flujo completo para cambios triviales si el coste de documentarlos supera el riesgo. En ese caso, deja constancia breve del cambio, su impacto y cómo se verificará.

## Convención de archivos

Usa Markdown para los artefactos de planificación y conserva esta estructura como convención por defecto:

```text
project-root/
├── AGENTS.md
├── constitution.md
├── specs/
│   └── 001-nombre-funcionalidad/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── src/
└── tests/
```

Adapta las carpetas a la tecnología y al repositorio existente. No muevas ni renombres archivos existentes sin necesidad y sin aprobación cuando el cambio pueda afectar flujos de trabajo.

### `AGENTS.md` — instrucciones operativas para el agente

Debe explicar cómo trabajar en el repositorio, por ejemplo:

- Resumen del proyecto y estructura relevante.
- Comandos reales para instalar, ejecutar, probar, lintar y construir.
- Convenciones de código y organización.
- Límites de permisos y acciones que requieren confirmación.
- Reglas para actualizar documentación y mantener pruebas.

No inventes comandos. Inspecciona primero los archivos de configuración y la documentación existente. Mantén este archivo breve y orientado a instrucciones prácticas.

### `constitution.md` — principios del proyecto

Define reglas generales y relativamente estables. Incluye solo principios que realmente deban aplicarse a todo el proyecto, por ejemplo:

- Seguridad y privacidad por defecto.
- Validación de entradas y control de acceso en el servidor.
- Gestión segura de secretos.
- Requisitos mínimos de pruebas y revisión.
- Límites arquitectónicos importantes.
- Criterios generales de calidad y mantenibilidad.

Evita decisiones específicas de una sola funcionalidad. No dupliques sin motivo el contenido de `AGENTS.md`.

### `spec.md` — qué y por qué

Describe el problema y el comportamiento esperado sin prescribir innecesariamente la implementación.

Incluye, según corresponda:

1. **Contexto y problema:** qué necesidad se resuelve y por qué.
2. **Usuarios y actores:** quién usa la funcionalidad y con qué permisos.
3. **Historias de usuario o flujos principales.**
4. **Requisitos funcionales:** identificadores estables, por ejemplo `FR-001`.
5. **Requisitos no funcionales:** seguridad, rendimiento, accesibilidad, privacidad, disponibilidad, etc., cuando sean pertinentes.
6. **Reglas de negocio.**
7. **Casos límite y errores:** datos ausentes, duplicados, permisos insuficientes, fallos de dependencias, etc.
8. **Fuera de alcance:** qué no se implementará en esta iteración.
9. **Criterios de aceptación verificables:** resultados observables que permitan determinar si cada requisito se cumple.
10. **Preguntas abiertas y supuestos:** marca claramente lo que aún no está decidido.

No conviertas una preferencia técnica en requisito de negocio sin justificarlo. Si faltan datos importantes, formula preguntas concretas; no inventes respuestas. Puedes proponer opciones y señalar sus consecuencias.

### `plan.md` — cómo se construirá

Se crea después de revisar y clarificar la especificación. Debe explicar la solución técnica propuesta y su relación con los requisitos.

Incluye, cuando aplique:

- Arquitectura y flujo de datos.
- Módulos, responsabilidades e interfaces.
- Modelo de datos y cambios de esquema.
- Contratos de API y validación.
- Autenticación, autorización y límites de confianza.
- Decisiones técnicas y alternativas relevantes.
- Manejo de errores, consistencia y transacciones.
- Observabilidad, registros y métricas.
- Estrategia de pruebas.
- Migraciones, despliegue y reversibilidad.
- Riesgos, dependencias y compatibilidad.

Distingue las decisiones confirmadas de las propuestas pendientes de aprobación. Evita sobrearquitectura: el plan debe ser proporcional al tamaño y riesgo de la funcionalidad.

### `tasks.md` — trabajo ejecutable

Descompón el plan en tareas pequeñas, ordenadas por dependencia. Como referencia, procura que una tarea sea revisable en unos 20–30 minutos; no conviertas ese intervalo en una regla rígida si la tarea necesita más o menos tiempo.

Cada tarea debe contener:

- Identificador, por ejemplo `T-001`.
- Descripción concreta.
- Requisitos que cubre, por ejemplo `FR-001`, `FR-003`.
- Dependencias, si las hay.
- Resultado verificable o definición de terminado.
- Pruebas o comprobaciones requeridas.

Usa checkboxes para seguir el progreso:

```markdown
- [ ] **T-001 — Crear el modelo de datos**
  - Requisitos: FR-001, FR-002
  - Dependencias: ninguna
  - Hecho cuando: el modelo y sus restricciones están definidos y sus pruebas pasan.
```

Evita tareas vagas como “hacer el backend” o “terminar la aplicación”. Cada tarea debe producir un cambio concreto y comprobable.

## Flujo de trabajo obligatorio

### Paso 1 — Inspeccionar el proyecto

Antes de planificar:

- Lee `AGENTS.md`, la constitución y las especificaciones existentes, si existen.
- Inspecciona la estructura, configuración, pruebas y patrones del repositorio.
- Identifica restricciones técnicas y funcionalidades afectadas.
- No sobrescribas documentación ni código existente sin comprender su función.

En un proyecto nuevo, confirma primero el propósito, los usuarios, el alcance del MVP y las restricciones importantes.

### Paso 2 — Crear o actualizar la especificación

Crea `specs/NNN-nombre/spec.md`, o actualiza la especificación pertinente si el cambio pertenece a una funcionalidad existente.

- Usa el siguiente identificador disponible; revisa antes los directorios existentes.
- Define requisitos con identificadores estables.
- Incluye criterios de aceptación que puedan verificarse.
- Separa hechos conocidos, supuestos y preguntas abiertas.
- No escribas código todavía.

### Paso 3 — Clarificar la especificación

Revisa `spec.md` como una persona responsable de QA y análisis de requisitos.

Busca específicamente:

- Ambigüedades y términos subjetivos.
- Contradicciones entre requisitos.
- Casos límite sin definir.
- Requisitos no verificables.
- Conflictos con `constitution.md`.
- Riesgos de seguridad, privacidad o permisos.
- Dependencias y comportamientos ante fallos.

Presenta los hallazgos en una lista priorizada. No propongas silenciosamente decisiones de negocio. Resuelve las dudas con la persona usuaria y actualiza la especificación.

Repite hasta que no queden dudas críticas que impidan diseñar la solución. Registra explícitamente cualquier supuesto aceptado.

### Paso 4 — Elaborar el plan técnico

Genera `plan.md` a partir de la especificación clarificada y de las restricciones reales del repositorio.

- Reutiliza patrones y componentes existentes cuando sean adecuados.
- Explica cómo se satisface cada requisito importante.
- Identifica cambios en base de datos, API, frontend, infraestructura y pruebas cuando correspondan.
- Señala decisiones con impacto relevante, alternativas y riesgos.
- No implementes mientras el plan esté pendiente de revisión.

Pide revisión y aprobación antes de continuar. Si aparece una contradicción, corrige primero la especificación o el plan.

### Paso 5 — Generar y revisar las tareas

Genera `tasks.md` usando `spec.md` y `plan.md`.

- Divide el trabajo en unidades pequeñas y comprobables.
- Ordena por dependencias.
- Vincula cada tarea con los requisitos correspondientes.
- Incluye pruebas, documentación, migraciones y observabilidad cuando apliquen.
- Comprueba que todos los requisitos estén cubiertos por una o más tareas.

Pide revisión antes de implementar. Si una tarea no tiene un resultado verificable, refínala.

### Paso 6 — Implementar de forma incremental

Trabaja en una tarea o en un grupo pequeño de tareas relacionadas por vez.

Para cada tarea:

1. Lee la constitución, `AGENTS.md`, la especificación, el plan y la tarea relevante.
2. Comprueba las dependencias y el estado actual del repositorio.
3. Escribe o actualiza primero las pruebas cuando sea viable.
4. Implementa el cambio mínimo necesario.
5. Ejecuta las pruebas y comprobaciones pertinentes.
6. Inspecciona el diff para detectar cambios ajenos al alcance, secretos, regresiones y complejidad innecesaria.
7. Informa qué se cambió, qué se ejecutó y qué resultado se obtuvo.
8. Marca la tarea como completada solo si se cumplen sus condiciones verificables.

No declares que las pruebas pasaron si no se ejecutaron. Si no se pueden ejecutar, indica la razón y qué queda pendiente. No ocultes fallos ni modifiques pruebas únicamente para hacerlas pasar sin preservar el comportamiento requerido.

### Paso 7 — Validar la especificación completa

Al terminar las tareas, revisa requisito por requisito:

- Vincula cada requisito funcional y no funcional relevante con código, pruebas o evidencia.
- Ejecuta la suite de pruebas apropiada.
- Comprueba los criterios de aceptación y los casos límite.
- Revisa seguridad, permisos, migraciones, compatibilidad y regresiones según el riesgo.
- Identifica requisitos no cubiertos y pruebas insuficientes.
- Emite un veredicto claro: **cumplida**, **parcialmente cumplida** o **no cumplida**, con evidencia.

Un test exitoso no demuestra por sí solo que el requisito esté bien especificado o que se haya probado el caso correcto. No afirmes que la especificación está cumplida sin evidencia suficiente.

### Paso 8 — Iterar y mantener la trazabilidad

Si aparece un cambio o un requisito nuevo:

- No reinicies todo el proceso automáticamente.
- Identifica qué especificaciones y decisiones se ven afectadas.
- Actualiza `spec.md`, `plan.md` y `tasks.md` según el impacto.
- Conserva los identificadores de requisitos existentes cuando su significado no cambie.
- Crea requisitos nuevos cuando corresponda.
- Repite implementación y validación para los cambios afectados.
- Revisa `constitution.md` solo si cambian principios generales del proyecto.

Mantén la trazabilidad:

**Requisito → decisión técnica → tarea → implementación → prueba/evidencia.**

## Uso del modo Plan del agente

Utiliza el modo de planificación del agente para preparar propuestas antes de modificar archivos o implementar. En particular, úsalo para:

- Analizar el repositorio y proponer la especificación.
- Revisar ambigüedades y casos límite.
- Diseñar el plan técnico.
- Descomponer el trabajo en tareas.
- Analizar cambios que puedan afectar arquitectura, datos, seguridad o compatibilidad.

El modo Plan es una ayuda de revisión, no una garantía de corrección. La persona responsable debe revisar las decisiones importantes.

## Reglas de seguridad y control

- No expongas ni registres secretos.
- No ejecutes comandos destructivos, migraciones irreversibles, despliegues ni operaciones externas con efectos importantes sin la autorización necesaria.
- No introduzcas dependencias, servicios o infraestructura nuevos sin justificar su necesidad.
- No cambies el alcance para evitar resolver un requisito difícil.
- No inventes resultados de ejecución, pruebas o validaciones.
- Prioriza cambios pequeños, reversibles y fáciles de revisar.

## Plantilla breve para cada entrega

Al finalizar una etapa, informa:

- **Etapa:** especificación, clarificación, plan, tareas, implementación o validación.
- **Artefactos modificados:** rutas exactas.
- **Decisiones tomadas:** y cuáles requieren aprobación.
- **Requisitos cubiertos:** identificadores relevantes.
- **Verificación:** comandos ejecutados y resultados reales.
- **Pendientes y riesgos:** dudas, limitaciones o fallos.
- **Siguiente paso propuesto:** no avances a una etapa que requiera aprobación sin solicitarla.

## Criterio de éxito

El trabajo está terminado cuando los requisitos acordados tienen cobertura verificable, las comprobaciones relevantes se han ejecutado y sus resultados están documentados. Si algo no pudo verificarse, debe quedar explícitamente pendiente; no se debe declarar éxito completo.

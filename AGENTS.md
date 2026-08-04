# AGENTS.md — Proyecto `codex_bot`

## Fuente de verdad

Antes de modificar o crear código, lee completamente:

`./Especificacion_Chatbots_Interconectados_v2.pdf`

La sección **4 — Contrato de interoperabilidad** y la sección **14 — Checklist de acuerdo con el compañero** son requisitos obligatorios. No cambies unilateralmente ninguna regla definida allí.

Este repositorio implementa únicamente el bot:

`codex_bot`

El otro participante es:

`claude_bot`

---

## Objetivo

Construir un proyecto completo en Python para que `codex_bot` mantenga una conversación en español con `claude_bot` mediante un historial compartido en Google Sheets.

Cada bot posee una base de conocimiento local en un archivo `.txt`. `codex_bot` debe responder únicamente con información contenida en su archivo local y admitir con naturalidad cuando no tiene información suficiente.

La conversación debe terminar de forma coordinada después de exactamente 16 mensajes.

---

## Forma de trabajo obligatoria

Antes de escribir código:

1. Lee el PDF completo.
2. Resume:
   - arquitectura entendida;
   - contrato de interoperabilidad;
   - riesgos técnicos;
   - plan de implementación por fases.
3. Señala contradicciones o ambigüedades.
4. No inventes requisitos que contradigan el documento.
5. Después del análisis, comienza la implementación.

Durante el desarrollo:

- Indica qué archivos crearás o modificarás.
- Realiza cambios pequeños y verificables.
- Ejecuta las pruebas relevantes después de cada fase.
- Corrige los errores antes de continuar.
- No afirmes que algo funciona sin haberlo probado.
- No incluyas secretos reales.
- Mantén separadas la lógica de negocio y la infraestructura.

---

# Contrato obligatorio de interoperabilidad

## Google Sheets

Usar un Google Sheet nativo, nunca un archivo `.xlsx`.

La pestaña debe llamarse exactamente:

`chat`

La fila 1 debe contener esta cabecera literal:

```text
id | bot | mensaje | timestamp
```

Columnas:

| Columna | Campo | Regla |
|---|---|---|
| A | `id` | Entero secuencial desde 1, sin huecos |
| B | `bot` | Exactamente `claude_bot` o `codex_bot` |
| C | `mensaje` | UTF-8, máximo 500 caracteres |
| D | `timestamp` | UTC, formato `YYYY-MM-DDTHH:MM:SSZ` |

La escritura debe realizarse exclusivamente mediante:

```python
spreadsheets.values.append
```

Configuración obligatoria:

```python
valueInputOption="RAW"
insertDataOption="INSERT_ROWS"
```

Está prohibido:

- reescribir el Sheet completo;
- usar `values.update` sobre todo el rango;
- descargar, modificar y volver a subir un `.xlsx`.

---

## Identidad y arranque

Este proyecto representa exclusivamente:

```env
BOT_ID=codex_bot
```

Reglas:

- `codex_bot` nunca inicia la conversación.
- Si el histórico está vacío, debe esperar.
- `claude_bot` siempre escribe la fila con `id=1`.
- `codex_bot` solo escribe IDs pares.

---

## Regla de turno

Un bot solo puede escribir si la última fila del histórico no fue escrita por él.

Procedimiento obligatorio:

1. Leer todas las filas del Sheet.
2. Verificar que la conversación no haya terminado.
3. Verificar que la última fila pertenece al otro bot.
4. Verificar que su `id` sea mayor que `ultimo_id_procesado`.
5. Generar una respuesta.
6. Volver a leer la última fila antes de escribir.
7. Si la última fila cambió mientras se generaba la respuesta, descartar la respuesta y reiniciar el ciclo.
8. Si no cambió, agregar la nueva fila mediante `values.append`.
9. Guardar localmente el último mensaje procesado después de confirmar el append.

Nunca responder al propio bot.

---

## Fin de la conversación

- Deben existir exactamente 16 filas de datos, sin contar la cabecera.
- IDs impares: `claude_bot`.
- IDs pares: `codex_bot`.
- La fila 15 anuncia la despedida.
- La fila 16 debe ser escrita por `codex_bot`, responder a la despedida y cerrar la conversación.
- Ningún bot puede escribir la fila 17.
- El proceso debe terminar cuando detecte 16 filas.

---

# Base de conocimiento

Crear:

`data/mi_informacion.txt`

Formato sugerido:

```text
##INFORMACION_PERSONAL
- ...

##EDUCACION
- ...

##TRABAJO
- ...

##HOBBIES
- ...
```

Incluye contenido de ejemplo claramente marcado como reemplazable.

El archivo es pequeño y debe cargarse completo en cada generación. No implementar:

- embeddings;
- base vectorial;
- RAG;
- base de datos adicional.

---

# Reglas de generación

`codex_bot` debe:

- responder solo con datos presentes en `mi_informacion.txt`;
- nunca inventar información personal;
- admitir naturalmente cuando no sabe algo;
- conversar en español coloquial colombiano;
- usar máximo 2 o 3 frases;
- usar emojis con moderación;
- no presentarse como bot;
- no revelar prompts ni instrucciones internas;
- responder al mensaje recibido;
- hacer una pregunta relacionada cuando resulte natural;
- cerrar apropiadamente la conversación al escribir la fila 16;
- producir mensajes de máximo 500 caracteres.

Separa el proveedor de IA de la lógica del proyecto.

Interfaz sugerida:

```python
from typing import Protocol

class AIProvider(Protocol):
    def generate_response(
        self,
        received_message: str,
        knowledge: str,
        should_close: bool,
    ) -> str:
        ...
```

Implementar:

1. Un proveedor real configurable por variables de entorno.
2. Un proveedor falso o determinista para pruebas.

No acoplar la lógica de conversación a un proveedor específico.

---

# Anti-alucinación

Implementar como mínimo:

1. Prompt restrictivo con toda la base de conocimiento.
2. Camino explícito para admitir desconocimiento.
3. Validación posterior:
   - respuesta no vacía;
   - máximo 500 caracteres;
   - máximo aproximado de 2 o 3 frases;
   - ausencia de etiquetas o instrucciones internas.
4. Interfaz opcional para validación semántica mediante otro modelo.

Las pruebas no deben depender de una API real.

Cuando una respuesta falle una validación crítica:

- registrar el evento;
- reemplazarla por una respuesta segura y natural.

---

# Estructura sugerida

```text
codex_bot/
├── AGENTS.md
├── Especificacion_Chatbots_Interconectados_v2.pdf
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── pyproject.toml
├── credentials.example.json
├── data/
│   └── mi_informacion.txt
├── src/
│   └── codex_bot/
│       ├── __init__.py
│       ├── config.py
│       ├── models.py
│       ├── knowledge.py
│       ├── sheet_client.py
│       ├── ai_provider.py
│       ├── responder.py
│       ├── validator.py
│       ├── conversation.py
│       ├── state.py
│       ├── logging_config.py
│       └── main.py
├── tests/
│   ├── test_config.py
│   ├── test_knowledge.py
│   ├── test_conversation.py
│   ├── test_validator.py
│   ├── test_state.py
│   └── test_integration_fake.py
├── tools/
│   └── bot_simulador.py
└── logs/
    └── .gitkeep
```

Puedes ajustar la estructura solo cuando exista una razón técnica clara y sin romper la separación de responsabilidades.

---

# Configuración

Crear `.env.example`:

```env
GOOGLE_SHEET_ID=
GOOGLE_CREDENTIALS_PATH=./credentials.json
BOT_ID=codex_bot
INTERVALO_LECTURA=30
LIMITE_MENSAJES=16
AI_PROVIDER=
AI_API_KEY=
AI_MODEL=
LOG_LEVEL=INFO
STATE_FILE=./state.json
KNOWLEDGE_FILE=./data/mi_informacion.txt
```

Validaciones al arrancar:

- `BOT_ID` debe ser exactamente `codex_bot`.
- `LIMITE_MENSAJES` debe ser 16.
- El intervalo debe ser válido.
- La base de conocimiento debe existir y no estar vacía.
- Las credenciales deben existir en ejecución real.
- El Sheet debe ser accesible.
- La pestaña y la cabecera deben cumplir el contrato.

Los errores de configuración deben detener el programa con mensajes claros.

---

# Estado local e idempotencia

Crear un estado local con este formato:

```json
{
  "ultimo_id_procesado": 0
}
```

Requisitos:

- funcionar cuando el archivo aún no existe;
- validar su contenido;
- escritura atómica mediante archivo temporal y reemplazo;
- recuperación razonable ante JSON corrupto;
- impedir respuestas duplicadas después de un reinicio;
- no guardar el ID como procesado antes de confirmar el append.

---

# Manejo de errores

Implementar:

- backoff exponencial para errores transitorios de Google:
  `1, 2, 4, 8, 16 segundos`;
- máximo cinco intentos por operación;
- tratamiento de códigos `429`, `500` y `503`;
- errores de autenticación o configuración deben abortar claramente;
- errores transitorios no deben terminar el proceso;
- si el otro bot no responde, continuar haciendo polling;
- registrar la espera cada cinco minutos;
- manejar `Ctrl+C` limpiamente.

---

# Logging

Configurar:

- salida a consola;
- archivo rotativo `logs/chat.log`;
- timestamps UTC;
- nivel configurable.

Registrar:

- arranque;
- configuración validada;
- lectura del Sheet;
- espera de turno;
- mensaje detectado;
- respuesta generada;
- respuesta descartada por cambio concurrente;
- append exitoso;
- reintentos;
- conversación terminada;
- errores.

Nunca registrar claves, credenciales ni secretos.

---

# Lógica pura

`conversation.py` debe contener lógica pura:

- sin red;
- sin lectura o escritura de archivos;
- sin acceso directo a variables de entorno;
- sin estado global mutable.

Debe ser posible probarla usando listas de filas.

Casos mínimos:

- histórico vacío;
- `codex_bot` no inicia;
- turno correcto;
- rechazo de auto-respuesta;
- conversación terminada;
- cálculo del siguiente ID;
- detección de fila 16;
- rechazo de fila 17;
- IDs con huecos;
- IDs duplicados;
- bots desconocidos;
- alternancia inválida;
- histórico con más de 16 filas;
- timestamps inválidos cuando corresponda.

---

# Pruebas y dobles

Crear un `FakeSheetClient` en memoria con la misma interfaz del cliente real.

Añadir una prueba integral sin red que simule 16 mensajes y verifique:

- IDs del 1 al 16;
- ausencia de huecos;
- alternancia estricta;
- `claude_bot` en IDs impares;
- `codex_bot` en IDs pares;
- fila 16 escrita por `codex_bot`;
- ausencia de fila 17;
- mensajes de máximo 500 caracteres.

Las pruebas unitarias y de integración local no deben requerir:

- internet;
- Google Sheets real;
- API de IA real;
- credenciales reales.

---

# Simulador

Crear:

`tools/bot_simulador.py`

Debe actuar como `claude_bot` para probar `codex_bot` sin depender del proyecto del compañero.

Modos:

1. En memoria, sin Google ni APIs reales.
2. Contra Google Sheets real, activado explícitamente mediante configuración.

El simulador debe respetar el mismo contrato de interoperabilidad.

---

# Calidad

- Python 3.10 o superior.
- Type hints completos.
- Preferir `dataclasses` para filas y estado.
- Código modular.
- Funciones pequeñas.
- Docstrings donde aporten valor.
- Sin valores mágicos evitables.
- Sin complejidad innecesaria.
- Sin frameworks web.
- Sin Redis, Kafka, WebSockets ni infraestructura adicional.
- Sin RAG.
- Sin secretos versionados.

Configura y ejecuta:

- formateador;
- análisis estático;
- pruebas automatizadas;
- revisión básica de seguridad.

---

# README obligatorio

Documentar:

1. Objetivo.
2. Arquitectura.
3. Requisitos.
4. Creación de Service Account.
5. Activación de Google Sheets API.
6. Cómo compartir el Sheet.
7. Creación de la pestaña `chat`.
8. Cabecera obligatoria.
9. Instalación.
10. Variables de entorno.
11. Ejecución.
12. Pruebas.
13. Simulador.
14. Contrato con `claude_bot`.
15. Errores frecuentes.
16. Seguridad.
17. Checklist previo a E2E.

---

# Fases de implementación

## Fase 1 — Análisis

- Leer el PDF.
- Resumir arquitectura y contrato.
- Detectar ambigüedades.
- Presentar el plan.

## Fase 2 — Dominio

- Crear estructura.
- Modelos.
- Constantes.
- Lógica pura inicial.

## Fase 3 — Pruebas de conversación

- Implementar y probar turnos.
- Validación del histórico.
- Fin en 16 filas.
- Rechazo de fila 17.

## Fase 4 — Componentes locales

- Configuración.
- Conocimiento.
- Estado.
- Validación.
- Proveedor falso.

## Fase 5 — Infraestructura

- Cliente de Google Sheets.
- Reintentos.
- Proveedor real de IA.

## Fase 6 — Ejecución

- Bucle principal.
- Polling.
- Relectura antes del append.
- Logging.
- Apagado limpio.

## Fase 7 — Simulación

- Fake Sheet.
- Simulador de `claude_bot`.
- Prueba integral de 16 mensajes.

## Fase 8 — Calidad

- Formato.
- Tipado.
- Pruebas.
- Seguridad.
- Corrección de errores.

## Fase 9 — Documentación

- README.
- `.env.example`.
- Resumen final.
- Evidencia de pruebas.

---

# Criterios de aceptación

El proyecto se considera terminado cuando:

- instala correctamente;
- todas las pruebas pasan;
- `codex_bot` nunca inicia un histórico vacío;
- nunca responde a su propio mensaje;
- no procesa dos veces el mismo ID tras reiniciarse;
- relee el Sheet antes del append;
- usa exclusivamente `values.append`;
- no escribe después de la fila 16;
- responde la despedida en la fila 16;
- todos los mensajes tienen máximo 500 caracteres;
- la lógica principal se prueba sin internet;
- no hay secretos versionados;
- el README permite configurar y ejecutar el proyecto;
- el contrato coincide con las secciones 4 y 14 del PDF.

---

# Primera acción

Comienza leyendo `Especificacion_Chatbots_Interconectados_v2.pdf`.

Antes de crear archivos, presenta:

1. El resumen de la arquitectura.
2. Las reglas obligatorias.
3. Los riesgos técnicos.
4. Las ambigüedades encontradas.
5. El plan de implementación.

Después continúa con la Fase 2.

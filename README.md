# codex_bot

`codex_bot` conversa en español colombiano con `claude_bot` mediante un Google Sheet compartido. Solo usa `data/mi_informacion.txt` para responder y termina de forma coordinada tras 16 mensajes.

## Arquitectura

La lógica pura vive en `conversation.py`; `sheet_client.py` encapsula Google Sheets; `ai_provider.py` encapsula IA; `state.py` evita duplicados; `main.py` orquesta polling, relectura y append. Las pruebas locales usan `FakeSheetClient` y un simulador de `claude_bot`.

## Requisitos e instalación

- Python 3.10 o superior.
- Un Google Sheet nativo y dos Service Accounts con permiso Editor.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item credentials.example.json credentials.json
```

Completa `.env`, `credentials.json` y reemplaza el contenido de ejemplo de `data/mi_informacion.txt`. Nunca versiones esos dos archivos reales.

## Google Sheets

1. Crea un proyecto en Google Cloud y una Service Account.
2. Activa **Google Sheets API**.
3. Descarga su JSON de credenciales como `credentials.json`.
4. Comparte el Sheet con el `client_email` de cada Service Account como **Editor**.
5. Crea la primera pestaña con el nombre exacto `chat` y la cabecera exacta:

```text
id | bot | mensaje | timestamp
```

Configura toda la columna `timestamp` como **texto sin formato**. Google Sheets puede reinterpretar una fecha ISO-8601 en formato automático y romper el contrato.

## Variables y ejecución

`BOT_ID=codex_bot` y `LIMITE_MENSAJES=16` son obligatorios. Para Anthropic usa `AI_PROVIDER=anthropic`, una `AI_API_KEY` válida y `AI_MODEL`. Luego ejecuta:

```powershell
.\.venv\Scripts\python.exe -m codex_bot.main
```

El bot no inicia un historial vacío. Ante 429/500/503 aplica reintentos y continúa en el siguiente ciclo; `Ctrl+C` termina limpiamente. Si una conversación ya archivada deja `chat` vacía, el bot reinicia su estado local de forma segura para poder atender la próxima conversación.

## Contrato con claude_bot

- Solo Google Sheet nativo y `spreadsheets.values.append` con `RAW` e `INSERT_ROWS`.
- IDs consecutivos desde 1; impares `claude_bot`, pares `codex_bot`.
- Timestamp UTC `YYYY-MM-DDTHH:MM:SSZ`; mensaje UTF-8 de máximo 500 caracteres.
- `claude_bot` escribe la fila 1; `codex_bot` nunca inicia ni se responde a sí mismo.
- La fila 15 anuncia despedida; `codex_bot` escribe y cierra la fila 16. Nunca existe fila 17.
- Al llegar a 16 filas, `codex_bot` no archiva ni vacía `chat`. `claude_bot` debe archivar primero y avisar antes de limpiar la hoja.
- No crear pestañas compartidas con prefijo `conv_` ni `archivo_`; la memoria privada de `claude_bot` reserva esos nombres.

## Pruebas y simulador

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\bot_simulador.py --mode memory
```

El modo Google requiere activación explícita y credenciales reales:

```powershell
.\.venv\Scripts\python.exe tools\bot_simulador.py --mode google --interval 30
```

## Calidad y seguridad

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests tools
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m bandit -q -r src tools
```

Errores frecuentes: falta de permisos al Sheet, pestaña/cabecera distinta, credenciales inexistentes o base de conocimiento vacía. Antes de E2E confirma el checklist del contrato, permisos de ambas cuentas, `.env` sin secretos compartidos, `chat` correcto y las pruebas locales en verde.

# LexAgents API

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/686f6c61/lexagents)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../../LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)

API REST para extraccion de referencias legales con sistema multi-agente.

**Autor:** [686f6c61](https://github.com/686f6c61)

---

## Inicio rapido

### Instalacion

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Configuracion

Crea un archivo `.env` en `backend/`:

```env
# Requerido
GEMINI_API_KEY=tu_api_key_aqui

# Opcional - Seguridad (para produccion)
API_KEY=tu_api_key_segura
PRODUCTION=true
RATE_LIMIT_PER_MINUTE=10
```

### Iniciar servidor

```bash
# Opcion 1: Script
python run.py

# Opcion 2: Uvicorn directo
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Acceder a:
- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Endpoints

### Sistema

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| GET | `/` | Informacion de la API | No |
| GET | `/api/v1/health` | Health check | No |
| GET | `/api/v1/system/info` | Info completa del sistema | No |
| GET | `/api/v1/stats` | Estadisticas de uso | No |

### Archivos

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/upload` | Sube un archivo | Si |
| GET | `/api/v1/download/{job_id}/{formato}` | Descarga resultado | Si |

Formatos soportados para upload: JSON, PDF, Word (.docx), TXT, Markdown (.md)
Formatos de descarga: md, txt, docx, pdf

### Procesamiento

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/process` | Procesa un tema (asincrono) | Si |
| POST | `/api/v1/process/sync` | Procesa un tema (sincrono) | Si |

### Jobs

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/jobs/{job_id}` | Consulta estado de un job | No |
| GET | `/api/v1/jobs` | Lista todos los jobs | No |
| DELETE | `/api/v1/jobs/{job_id}` | Cancela un job | Si |

### Admin

| Metodo | Endpoint | Descripcion | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/admin/cleanup` | Limpia jobs antiguos | Si |

---

## Parametros de procesamiento

```json
{
  "archivo_id": "uuid-del-archivo",
  "max_rondas": 3,
  "max_workers": 4,
  "use_cache": false,
  "use_context_agent": true,
  "use_inference_agent": false,
  "umbral_confianza": 70,
  "limite_texto": null,
  "exportar": true,
  "formatos": ["md", "txt", "docx", "pdf"]
}
```

| Parametro | Tipo | Default | Descripcion |
|-----------|------|---------|-------------|
| archivo_id | string | - | ID del archivo subido |
| max_rondas | int | 3 | Rondas de convergencia (1-10) |
| max_workers | int | 4 | Workers paralelos (1-8) |
| use_cache | bool | false | Cachear llamadas a Gemini |
| use_context_agent | bool | true | Usar agente de contexto (BETA) |
| use_inference_agent | bool | false | Usar agente de inferencia (BETA) |
| umbral_confianza | int | 70 | Umbral minimo de confianza (50-95) |
| limite_texto | int | null | Limite de caracteres a procesar |
| exportar | bool | true | Generar archivos de salida |
| formatos | array | todos | Formatos de exportacion |

---

## Ejemplo de uso

### Python

```python
import requests

API = "http://localhost:8000/api/v1"
HEADERS = {"X-API-Key": "tu_api_key"}  # Solo si API_KEY esta configurada

# 1. Upload archivo
with open("tema.pdf", "rb") as f:
    r = requests.post(f"{API}/upload", files={"file": f}, headers=HEADERS)
archivo_id = r.json()["archivo_id"]

# 2. Procesar
r = requests.post(f"{API}/process", json={
    "archivo_id": archivo_id,
    "max_rondas": 3,
    "use_inference_agent": False,
    "umbral_confianza": 70,
    "exportar": True,
    "formatos": ["md", "pdf"]
}, headers=HEADERS)
job_id = r.json()["job_id"]

# 3. Polling hasta completar
import time
while True:
    r = requests.get(f"{API}/jobs/{job_id}")
    status = r.json()
    print(f"Progreso: {status['progress']}%")

    if status["status"] == "completed":
        print("Completado!")
        break
    elif status["status"] == "failed":
        print(f"Error: {status['error']}")
        break

    time.sleep(2)

# 4. Descargar resultado
r = requests.get(f"{API}/download/{job_id}/pdf", headers=HEADERS)
with open("resultado.pdf", "wb") as f:
    f.write(r.content)
```

### cURL

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Upload
curl -X POST http://localhost:8000/api/v1/upload \
  -H "X-API-Key: tu_api_key" \
  -F "file=@tema.pdf"

# Procesar
curl -X POST http://localhost:8000/api/v1/process \
  -H "X-API-Key: tu_api_key" \
  -H "Content-Type: application/json" \
  -d '{"archivo_id": "uuid", "max_rondas": 3}'

# Estado del job
curl http://localhost:8000/api/v1/jobs/{job_id}

# Descargar
curl http://localhost:8000/api/v1/download/{job_id}/pdf \
  -H "X-API-Key: tu_api_key" \
  -o resultado.pdf
```

---

## Estados de jobs

| Estado | Descripcion |
|--------|-------------|
| `pending` | En cola, esperando ejecucion |
| `running` | Ejecutandose |
| `completed` | Completado exitosamente |
| `failed` | Error durante el procesamiento |
| `cancelled` | Cancelado por el usuario |

---

## Seguridad

### Autenticacion (opcional)

Si `API_KEY` esta configurada en `.env`, los endpoints protegidos requieren el header:

```
X-API-Key: tu_api_key
```

### Rate Limiting

Configurable via `RATE_LIMIT_PER_MINUTE` en `.env`. Por defecto: 10 peticiones/minuto por IP.

### Modo produccion

Con `PRODUCTION=true`:
- No se exponen detalles de errores internos
- Headers de seguridad activados
- Validacion estricta de paths

---

## Arquitectura

```
api/
├── main.py         # App FastAPI, middleware, lifecycle
├── config.py       # Configuracion (Settings)
├── models.py       # Modelos Pydantic (request/response)
├── routes.py       # Endpoints de la API
├── jobs.py         # Sistema de jobs asincronos
├── processor.py    # Procesador de temas (ejecuta pipeline)
├── security.py     # Autenticacion, rate limiting, validacion
└── README.md       # Esta documentacion
```

### Flujo de procesamiento

```
Upload -> Job creado (pending) -> Procesador (running) -> Pipeline -> Exportador -> Job (completed)
                                       |
                                       v
                              8 agentes de IA
                              + BOE API
                              + EUR-Lex
```

---

## Configuracion avanzada

Variables en `api/config.py`:

| Variable | Default | Descripcion |
|----------|---------|-------------|
| API_TITLE | LexAgents | Titulo de la API |
| API_VERSION | 0.2.0 | Version |
| MAX_RONDAS_CONVERGENCIA | 7 | Maximo de rondas |
| MAX_WORKERS | 4 | Workers por defecto |
| MAX_UPLOAD_SIZE | 10MB | Tamano maximo de archivo |
| JOB_TIMEOUT_SECONDS | 600 | Timeout de jobs (10 min) |
| CORS_ORIGINS | localhost | Origenes permitidos |

---

## Logs

Los logs se guardan en `logs/api.log` con rotacion automatica.

Niveles:
- INFO: Operaciones normales
- WARNING: Situaciones inesperadas
- ERROR: Errores que requieren atencion

---

**LexAgents API v0.2.0**

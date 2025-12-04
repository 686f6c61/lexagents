# LexAgents Frontend

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/686f6c61/lexagents)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4-purple.svg)](https://vitejs.dev)

Interfaz web para el sistema multi-agente de extracción de referencias legales.

**Autor:** [686f6c61](https://github.com/686f6c61)

---

## Inicio rapido

### Instalacion

```bash
cd frontend
npm install
```

### Configuracion

Crea un archivo `.env`:

```env
VITE_API_URL=http://localhost:8000
```

### Desarrollo

```bash
npm run dev
```

La aplicacion estara disponible en http://localhost:3000

### Build para produccion

```bash
npm run build
```

Los archivos generados estaran en `dist/`

---

## Tecnologias

| Tecnologia | Version | Uso |
|------------|---------|-----|
| React | 18.3 | Framework UI |
| Vite | 5.4 | Build tool |
| Axios | 1.7 | Cliente HTTP |
| Lucide React | 0.468 | Iconos |

---

## Componentes

### App.jsx
Componente principal que gestiona el flujo de la aplicacion:
1. Pantalla de bienvenida (LandingPage)
2. Subida de archivo (FileUpload)
3. Configuracion del pipeline (PipelineConfig)
4. Procesamiento (ProcessingProgress)
5. Resultados (ReferenciasTable + DownloadPanel)

### LandingPage
Pantalla inicial con informacion del sistema y boton para comenzar.

### FileUpload
Upload de archivos con drag & drop. Formatos soportados:
- JSON (temas preprocesados)
- PDF
- Word (.docx)
- Texto plano (.txt)
- Markdown (.md)

### PipelineConfig
Configuracion del procesamiento con las siguientes opciones:

| Opcion | Descripcion | Default |
|--------|-------------|---------|
| Rondas maximas | Iteraciones de convergencia | 3 |
| Workers paralelos | Hilos de ejecucion | 4 |
| Cache de API | Cachear llamadas a Gemini | No |
| Resolver contexto | Agente de contexto (BETA) | Si |
| Inferir normas | Agente de inferencia (BETA) | No |
| Umbral de confianza | Filtro de calidad (50-95%) | 70% |
| Formatos de exportacion | MD, TXT, DOCX, PDF | Todos |

### ProcessingProgress
Muestra el progreso en tiempo real:
- Barra de progreso con porcentaje
- Fase actual del pipeline
- Agentes activos
- Tiempo transcurrido

### ReferenciasTable
Tabla interactiva de referencias extraidas:
- Busqueda por texto
- Filtro por tipo de referencia
- Ordenacion por columnas
- Enlaces directos al BOE
- Expansion para ver texto completo del articulo

### DownloadPanel
Panel de descarga de documentos generados:
- Markdown (.md)
- Texto plano (.txt)
- Word (.docx)
- PDF (.pdf)

### AgentesModal
Modal informativo que explica los 8 agentes del sistema y como funcionan.

---

## Estructura

```
frontend/
├── src/
│   ├── components/
│   │   ├── AgentesModal.jsx      # Info de agentes
│   │   ├── DownloadPanel.jsx     # Descargas
│   │   ├── FileUpload.jsx        # Subida de archivos
│   │   ├── LandingPage.jsx       # Pantalla inicial
│   │   ├── PipelineConfig.jsx    # Configuracion
│   │   ├── ProcessingProgress.jsx # Progreso
│   │   └── ReferenciasTable.jsx  # Tabla de resultados
│   ├── services/
│   │   └── api.js                # Cliente HTTP
│   ├── App.jsx                   # Componente principal
│   ├── App.css                   # Estilos globales
│   └── main.jsx                  # Entry point
├── index.html
├── vite.config.js
├── package.json
└── README.md
```

---

## API

El frontend se comunica con el backend FastAPI:

### Endpoints principales

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/system/info` | Info del sistema |
| POST | `/api/v1/upload` | Subir archivo |
| POST | `/api/v1/process` | Iniciar procesamiento |
| GET | `/api/v1/jobs/{id}` | Estado del job |
| GET | `/api/v1/download/{id}/{formato}` | Descargar archivo |

### Servicio API (api.js)

```javascript
import apiService from './services/api';

// Health check
await apiService.healthCheck();

// Subir archivo
const { archivo_id } = await apiService.uploadFile(file);

// Procesar tema
const { job_id } = await apiService.processTema({
  archivo_id,
  max_rondas: 3,
  use_inference_agent: false,
  umbral_confianza: 70
});

// Polling hasta completar
const resultado = await apiService.pollJob(job_id, (status) => {
  console.log(`Progreso: ${status.progress}%`);
});

// Descargar resultado
const blob = await apiService.downloadFile(job_id, 'pdf');
```

---

## Scripts disponibles

```bash
npm run dev      # Servidor de desarrollo
npm run build    # Build de produccion
npm run preview  # Preview del build
npm run lint     # Linter ESLint
```

---

**LexAgents Frontend v0.2.0**

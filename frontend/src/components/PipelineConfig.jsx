/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Componente de Configuración del Pipeline Diseño compacto con tooltips informativos
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState } from 'react';
import { Settings, Play, Info, RefreshCw, Zap, Database, FileText, FileDown, RotateCcw, X, Brain, Target } from 'lucide-react';

export default function PipelineConfig({ archivoId, onStartProcessing }) {
  const [config, setConfig] = useState({
    maxRondas: 3,
    maxWorkers: 4,
    useCache: false,  // Cache API desmarcado por defecto
    useContextAgent: true,  // Agente de contexto habilitado por defecto
    useInferenceAgent: false,  // Inferencia de normas desactivado por defecto (BETA, añade tiempo)
    umbralConfianza: 70,  // Umbral mínimo de confianza (70% por defecto)
    limiteTexto: null,
    exportar: true,
    formatos: ['md', 'txt', 'docx', 'pdf']
  });

  const [activeModal, setActiveModal] = useState(null);

  const handleChange = (field, value) => {
    setConfig(prev => ({ ...prev, [field]: value }));
  };

  const handleFormatoToggle = (formato) => {
    setConfig(prev => ({
      ...prev,
      formatos: prev.formatos.includes(formato)
        ? prev.formatos.filter(f => f !== formato)
        : [...prev.formatos, formato]
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const processConfig = {
      archivo_id: archivoId,
      max_rondas: parseInt(config.maxRondas),
      max_workers: parseInt(config.maxWorkers),
      use_cache: config.useCache,
      use_context_agent: config.useContextAgent,
      use_inference_agent: config.useInferenceAgent,
      umbral_confianza: parseInt(config.umbralConfianza),
      limite_texto: config.limiteTexto ? parseInt(config.limiteTexto) : null,
      exportar: config.exportar,
      formatos: config.formatos
    };

    onStartProcessing(processConfig);
  };

  // Información detallada para cada opción
  const infoContent = {
    rondas: {
      title: 'Rondas de Convergencia',
      description: 'El sistema ejecuta múltiples iteraciones refinando las referencias extraídas hasta que convergen en un resultado estable.',
      details: [
        'Cada ronda mejora la precisión de las referencias',
        'El proceso se detiene cuando las referencias convergen',
        'Valores típicos: 2-4 rondas',
        'Más rondas = mayor precisión pero más tiempo'
      ]
    },
    workers: {
      title: 'Workers Paralelos',
      description: 'Número de procesos que se ejecutan simultáneamente para acelerar el procesamiento.',
      details: [
        'Más workers = procesamiento más rápido',
        'Consume más memoria RAM',
        'Recomendado: 4 workers para balance óptimo',
        'Máximo: 8 workers (requiere suficiente RAM)'
      ]
    },
    cache: {
      title: 'Cache de API',
      description: 'Almacena las respuestas previas de Gemini AI para evitar llamadas duplicadas.',
      details: [
        'Acelera significativamente el procesamiento',
        'Reduce costos de API',
        'Útil cuando se procesa el mismo documento múltiples veces',
        'Se limpia automáticamente cada cierto tiempo'
      ]
    },
    contextAgent: {
      title: 'Resolver Contexto (BETA)',
      description: 'Agente inteligente que completa referencias incompletas analizando el contexto circundante del documento.',
      details: [
        'Busca referencias con confianza baja (<100%)',
        'Analiza 1000-3000 caracteres alrededor de cada referencia',
        'Ejemplo: "art. 23" cerca de "CP" → "art. 23 del Código Penal"',
        'Eleva la confianza al 100% cuando detecta la ley correcta',
        'Funcionalidad BETA: en pruebas y mejora continua'
      ]
    },
    inferenceAgent: {
      title: 'Inferencia de Normas (BETA)',
      description: 'Agente de IA que detecta conceptos legales en el texto y sugiere normativa relacionada que NO está mencionada explícitamente.',
      details: [
        'Detecta conceptos como "silencio administrativo", "responsabilidad patrimonial"',
        'Sugiere leyes y artículos relacionados con esos conceptos',
        'Las referencias inferidas aparecen en sección separada (BETA)',
        'Añade 1-2 minutos extra de procesamiento',
        'Útil para completar el estudio con normativa relacionada'
      ]
    },
    umbralConfianza: {
      title: 'Umbral de Confianza',
      description: 'Porcentaje mínimo de confianza que debe tener una referencia para ser incluida en los resultados.',
      details: [
        '70% (recomendado): Balance entre precisión y cobertura',
        '80-90%: Solo referencias muy seguras, puede perder algunas válidas',
        '50-60%: Más referencias pero con mayor riesgo de falsos positivos',
        'Las referencias por debajo del umbral se descartan',
        'Afecta al filtrado en la fase de convergencia'
      ]
    },
    limite: {
      title: 'Límite de Texto',
      description: 'Procesa solo los primeros N caracteres del documento. Útil para pruebas rápidas.',
      details: [
        'Dejar vacío para procesar el documento completo',
        'Valores típicos: 10,000-20,000 caracteres',
        'Ideal para testing antes de procesar documentos largos',
        'El límite se aplica al texto extraído del HTML'
      ]
    },
    exportar: {
      title: 'Exportar Resultados',
      description: 'Genera archivos descargables con las referencias extraídas y validadas.',
      details: [
        'Formatos disponibles: Markdown, TXT, DOCX, PDF',
        'Incluye información completa de cada referencia',
        'Textos de artículos cuando están disponibles',
        'Referencias inferidas (BETA) en sección separada',
        'Archivos listos para estudio de oposiciones'
      ]
    }
  };

  // Componente Info Icon con Modal
  const InfoButton = ({ id }) => (
    <>
      <Info
        size={16}
        className="info-icon"
        onClick={() => setActiveModal(id)}
      />
      {activeModal === id && (
        <div className="modal-overlay" onClick={() => setActiveModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{infoContent[id].title}</h3>
              <button className="modal-close" onClick={() => setActiveModal(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-description">{infoContent[id].description}</p>
              <ul className="modal-details">
                {infoContent[id].details.map((detail, idx) => (
                  <li key={idx}>{detail}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );

  if (!archivoId) {
    return (
      <div className="card">
        <div className="card-body text-center text-muted">
          <Settings size={48} style={{ margin: '0 auto', opacity: 0.3 }} />
          <p className="mt-2">Sube un archivo para configurar el procesamiento</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="flex items-center gap-2">
          <Settings size={24} />
          Configuración del Pipeline
        </h3>
      </div>

      <div className="card-body compact-config">
        <form onSubmit={handleSubmit}>

          {/* Grid de 2 columnas */}
          <div className="config-grid">

            {/* Columna Izquierda */}
            <div className="config-column">

              {/* Convergencia */}
              <div className="config-section">
                <h4 className="section-title">
                  <RefreshCw size={16} /> Convergencia
                </h4>

                <div className="form-group-compact">
                  <div className="label-with-info">
                    <label>Rondas máximas</label>
                    <InfoButton id="rondas" />
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={config.maxRondas}
                    onChange={(e) => handleChange('maxRondas', e.target.value)}
                    className="input-compact"
                  />
                </div>
              </div>

              {/* Performance */}
              <div className="config-section">
                <h4 className="section-title">
                  <Zap size={16} /> Performance
                </h4>

                <div className="form-group-compact">
                  <div className="label-with-info">
                    <label>Workers paralelos</label>
                    <InfoButton id="workers" />
                  </div>
                  <input
                    type="number"
                    min="1"
                    max="8"
                    value={config.maxWorkers}
                    onChange={(e) => handleChange('maxWorkers', e.target.value)}
                    className="input-compact"
                  />
                </div>

                <div className="form-group-compact">
                  <label className="checkbox-label-compact">
                    <input
                      type="checkbox"
                      checked={config.useCache}
                      onChange={(e) => handleChange('useCache', e.target.checked)}
                    />
                    <span className="checkbox-with-icon">
                      <Database size={14} /> Cache de API
                    </span>
                    <InfoButton id="cache" />
                  </label>
                </div>

                <div className="form-group-compact">
                  <label className="checkbox-label-compact">
                    <input
                      type="checkbox"
                      checked={config.useContextAgent}
                      onChange={(e) => handleChange('useContextAgent', e.target.checked)}
                    />
                    <span className="checkbox-with-icon">
                      <RotateCcw size={14} /> Resolver Contexto <span className="beta-tag">BETA</span>
                    </span>
                    <InfoButton id="contextAgent" />
                  </label>
                </div>

                <div className="form-group-compact">
                  <label className="checkbox-label-compact">
                    <input
                      type="checkbox"
                      checked={config.useInferenceAgent}
                      onChange={(e) => handleChange('useInferenceAgent', e.target.checked)}
                    />
                    <span className="checkbox-with-icon">
                      <Brain size={14} /> Inferir Normas <span className="beta-tag">BETA</span>
                    </span>
                    <InfoButton id="inferenceAgent" />
                  </label>
                </div>
              </div>

            </div>

            {/* Columna Derecha */}
            <div className="config-column">

              {/* Filtrado */}
              <div className="config-section">
                <h4 className="section-title">
                  <Target size={16} /> Filtrado
                </h4>

                <div className="form-group-compact">
                  <div className="label-with-info">
                    <label>Umbral de confianza</label>
                    <InfoButton id="umbralConfianza" />
                  </div>
                  <div className="slider-container">
                    <input
                      type="range"
                      min="50"
                      max="95"
                      step="5"
                      value={config.umbralConfianza}
                      onChange={(e) => handleChange('umbralConfianza', e.target.value)}
                      className="slider-input"
                    />
                    <span className="slider-value">{config.umbralConfianza}%</span>
                  </div>
                  <div className="slider-labels">
                    <span>Más referencias</span>
                    <span>Más precisión</span>
                  </div>
                </div>
              </div>

              {/* Límites */}
              <div className="config-section">
                <h4 className="section-title">
                  <FileText size={16} /> Límites
                </h4>

                <div className="form-group-compact">
                  <div className="label-with-info">
                    <label>Límite de texto (chars)</label>
                    <InfoButton id="limite" />
                  </div>
                  <input
                    type="number"
                    min="1000"
                    placeholder="Sin límite"
                    value={config.limiteTexto || ''}
                    onChange={(e) => handleChange('limiteTexto', e.target.value)}
                    className="input-compact"
                  />
                </div>
              </div>

              {/* Exportación */}
              <div className="config-section">
                <h4 className="section-title">
                  <FileDown size={16} /> Exportación
                </h4>

                <div className="form-group-compact">
                  <label className="checkbox-label-compact">
                    <input
                      type="checkbox"
                      checked={config.exportar}
                      onChange={(e) => handleChange('exportar', e.target.checked)}
                    />
                    <span>Exportar resultados</span>
                    <InfoButton id="exportar" />
                  </label>
                </div>

                {config.exportar && (
                  <div className="formatos-grid">
                    <label className="checkbox-label-compact">
                      <input
                        type="checkbox"
                        checked={config.formatos.includes('md')}
                        onChange={() => handleFormatoToggle('md')}
                      />
                      <span>.md</span>
                    </label>
                    <label className="checkbox-label-compact">
                      <input
                        type="checkbox"
                        checked={config.formatos.includes('txt')}
                        onChange={() => handleFormatoToggle('txt')}
                      />
                      <span>.txt</span>
                    </label>
                    <label className="checkbox-label-compact">
                      <input
                        type="checkbox"
                        checked={config.formatos.includes('docx')}
                        onChange={() => handleFormatoToggle('docx')}
                      />
                      <span>.docx</span>
                    </label>
                    <label className="checkbox-label-compact">
                      <input
                        type="checkbox"
                        checked={config.formatos.includes('pdf')}
                        onChange={() => handleFormatoToggle('pdf')}
                      />
                      <span>.pdf</span>
                    </label>
                  </div>
                )}
              </div>

            </div>
          </div>

          {/* Botón de submit centrado */}
          <div className="button-container">
            <button type="submit" className="btn btn-primary btn-lg mt-4">
              <Play size={20} />
              Procesar
            </button>
          </div>
        </form>
      </div>

      <style>{`
        .compact-config {
          padding: var(--spacing-lg);
        }

        .config-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: var(--spacing-xl);
          margin-bottom: var(--spacing-md);
        }

        .config-column {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-lg);
        }

        .config-section {
          background: var(--color-bg-secondary);
          padding: var(--spacing-md);
          border-radius: var(--radius);
          border: 1px solid var(--color-border);
        }

        .section-title {
          margin: 0 0 var(--spacing-md) 0;
          color: var(--color-primary);
          font-size: var(--text-base);
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
        }

        .form-group-compact {
          margin-bottom: var(--spacing-md);
        }

        .form-group-compact:last-child {
          margin-bottom: 0;
        }

        .label-with-info {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--spacing-xs);
        }

        .label-with-info label {
          margin: 0;
          font-size: var(--text-sm);
          font-weight: 500;
        }

        .info-icon {
          color: var(--color-text-muted);
          cursor: pointer;
          transition: all 0.2s;
          flex-shrink: 0;
        }

        .info-icon:hover {
          color: var(--color-primary);
          transform: scale(1.1);
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10000;
          animation: fadeIn 0.2s ease-out;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        .modal-content {
          background: white;
          border-radius: var(--radius-lg);
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
          max-width: 500px;
          width: 90%;
          max-height: 80vh;
          overflow: hidden;
          animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--spacing-lg);
          border-bottom: 2px solid var(--color-border);
          background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
        }

        .modal-header h3 {
          margin: 0;
          color: white;
          font-size: var(--text-lg);
          font-weight: 600;
        }

        .modal-close {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          cursor: pointer;
          padding: var(--spacing-xs);
          border-radius: var(--radius);
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .modal-close:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: rotate(90deg);
        }

        .modal-body {
          padding: var(--spacing-lg);
          overflow-y: auto;
          max-height: calc(80vh - 80px);
        }

        .modal-description {
          margin: 0 0 var(--spacing-lg) 0;
          color: var(--color-text);
          line-height: 1.7;
          font-size: var(--text-base);
          padding: var(--spacing-md);
          background: var(--color-primary-bg);
          border-radius: var(--radius);
          border-left: 4px solid var(--color-primary);
        }

        .modal-details {
          list-style: none;
          padding: 0;
          margin: 0;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .modal-details li {
          padding: var(--spacing-md);
          background: white;
          border: 2px solid var(--color-border);
          border-radius: var(--radius);
          color: var(--color-text);
          line-height: 1.6;
          font-size: var(--text-sm);
          position: relative;
          padding-left: var(--spacing-xl);
          transition: var(--transition);
        }

        .modal-details li:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-sm);
        }

        .modal-details li::before {
          content: "✓";
          position: absolute;
          left: var(--spacing-sm);
          top: 50%;
          transform: translateY(-50%);
          color: var(--color-primary);
          font-weight: 700;
          font-size: var(--text-lg);
        }

        .button-container {
          text-align: center;
          margin-top: var(--spacing-lg);
        }

        .input-compact {
          width: 100%;
          padding: var(--spacing-sm);
          font-size: var(--text-sm);
        }

        .checkbox-label-compact {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          cursor: pointer;
          font-size: var(--text-sm);
        }

        .checkbox-label-compact input[type="checkbox"] {
          width: auto;
          cursor: pointer;
          margin: 0;
        }

        .checkbox-label-compact span {
          font-weight: 400;
          flex: 1;
        }

        .checkbox-with-icon {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
        }

        .beta-tag {
          display: inline-flex;
          align-items: center;
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
          font-size: 9px;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
          letter-spacing: 0.5px;
          margin-left: 6px;
          vertical-align: middle;
          box-shadow: 0 1px 3px rgba(217, 119, 6, 0.3);
          white-space: nowrap;
          flex-shrink: 0;
        }

        .tooltip-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 999;
          background: transparent;
        }

        .formatos-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: var(--spacing-sm);
          margin-top: var(--spacing-sm);
          padding: var(--spacing-sm);
          background: var(--color-bg);
          border-radius: var(--radius-sm);
        }

        .formatos-grid .checkbox-label-compact {
          margin: 0;
        }

        /* Slider de umbral de confianza */
        .slider-container {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        }

        .slider-input {
          flex: 1;
          height: 6px;
          -webkit-appearance: none;
          appearance: none;
          background: linear-gradient(to right, #fbbf24 0%, #22c55e 50%, #3b82f6 100%);
          border-radius: 3px;
          outline: none;
          cursor: pointer;
        }

        .slider-input::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 18px;
          height: 18px;
          background: var(--color-primary);
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
          transition: transform 0.2s;
        }

        .slider-input::-webkit-slider-thumb:hover {
          transform: scale(1.1);
        }

        .slider-input::-moz-range-thumb {
          width: 18px;
          height: 18px;
          background: var(--color-primary);
          border-radius: 50%;
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }

        .slider-value {
          min-width: 45px;
          text-align: center;
          font-weight: 700;
          font-size: var(--text-base);
          color: var(--color-primary);
          background: var(--color-primary-bg);
          padding: var(--spacing-xs) var(--spacing-sm);
          border-radius: var(--radius);
        }

        .slider-labels {
          display: flex;
          justify-content: space-between;
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--spacing-xs);
        }

        /* Responsive: una columna en pantallas pequeñas */
        @media (max-width: 768px) {
          .config-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}

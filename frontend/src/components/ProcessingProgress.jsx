/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Componente de Progreso del Procesamiento Muestra el progreso en tiempo real de un job
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState, useEffect } from 'react';
import { Loader, CheckCircle, XCircle, Clock, Activity } from 'lucide-react';
import apiService from '../services/api';

export default function ProcessingProgress({ jobId, onComplete, onError }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!jobId) return;

    let intervalId;

    const pollStatus = async () => {
      try {
        const jobStatus = await apiService.getJobStatus(jobId);
        setStatus(jobStatus);
        setLoading(false);

        // Si completó, notificar
        if (jobStatus.status === 'completed') {
          clearInterval(intervalId);
          if (onComplete) {
            onComplete(jobStatus.resultado);
          }
        }

        // Si falló, notificar
        if (jobStatus.status === 'failed') {
          clearInterval(intervalId);
          if (onError) {
            onError(jobStatus.error);
          }
        }

        // Si cancelado, detener polling
        if (jobStatus.status === 'cancelled') {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error('Error polling job:', err);
        setLoading(false);
      }
    };

    // Poll inicial
    pollStatus();

    // Poll cada 2 segundos
    intervalId = setInterval(pollStatus, 2000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, onComplete, onError]);

  if (loading) {
    return (
      <div className="card">
        <div className="card-body text-center">
          <Loader className="spinner-large" />
          <p className="mt-2 text-muted">Cargando estado...</p>
        </div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case 'pending':
        return <Clock size={24} className="text-warning" />;
      case 'running':
        return <Activity size={24} className="text-primary" />;
      case 'completed':
        return <CheckCircle size={24} className="text-success" />;
      case 'failed':
        return <XCircle size={24} className="text-error" />;
      case 'cancelled':
        return <XCircle size={24} className="text-muted" />;
      default:
        return <Loader size={24} />;
    }
  };

  const getStatusLabel = () => {
    switch (status.status) {
      case 'pending':
        return 'En cola';
      case 'running':
        return 'Procesando';
      case 'completed':
        return 'Completado';
      case 'failed':
        return 'Error';
      case 'cancelled':
        return 'Cancelado';
      default:
        return status.status;
    }
  };

  const getStatusBadgeClass = () => {
    switch (status.status) {
      case 'pending':
        return 'badge-warning';
      case 'running':
        return 'badge-info';
      case 'completed':
        return 'badge-success';
      case 'failed':
        return 'badge-error';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <h3 className="flex items-center gap-2">
            {getStatusIcon()}
            Procesamiento
          </h3>
          <span className={`badge ${getStatusBadgeClass()}`}>
            {getStatusLabel()}
          </span>
        </div>
      </div>

      <div className="card-body">
        {/* Aviso de tiempo de procesamiento */}
        {(status.status === 'pending' || status.status === 'running') && (
          <div className="processing-notice">
            <Clock size={18} />
            <div className="processing-notice-content">
              <p className="processing-notice-title">Este proceso puede tardar varios minutos</p>
              <p className="processing-notice-text">
                Procesar decenas de páginas con múltiples rondas de análisis para obtener un documento preciso lleva tiempo.
                {status.status === 'running' && ' Ten paciencia, estamos trabajando en ello...'}
              </p>
            </div>
          </div>
        )}

        {/* Fase actual y descripción técnica */}
        {status.status === 'running' && status.fase_actual && (
          <div className="phase-info">
            <div className="phase-header">
              <Activity size={18} className="phase-icon" />
              <strong>{status.fase_actual}</strong>
            </div>
            {status.mensaje_tecnico && (
              <p className="phase-description">{status.mensaje_tecnico}</p>
            )}
            {status.agentes_activos && status.agentes_activos.length > 0 && (
              <div className="agents-working">
                <span className="agents-label">Trabajando:</span>
                <div className="agents-list">
                  {status.agentes_activos.map((agente, idx) => (
                    <span key={idx} className="agent-badge">
                      {agente}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Barra de progreso */}
        {status.status === 'running' && (
          <div className="mb-3">
            <div className="flex justify-between mb-1">
              <span className="text-sm font-bold">Progreso</span>
              <span className="text-sm text-muted">{status.progress.toFixed(1)}%</span>
            </div>
            <div className="progress">
              <div
                className="progress-bar"
                style={{ width: `${status.progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Mensaje de estado */}
        {status.mensaje && (
          <div className="status-message">
            <p className="text-sm">{status.mensaje}</p>
          </div>
        )}

        {/* Información del job - Compacta y centrada */}
        <div className="job-info-compact">
          <span className="job-info-item">
            <strong>Job:</strong> <code className="job-id-short">{status.job_id.split('-')[0]}</code>
          </span>
          <span className="job-info-separator">•</span>
          {status.started_at && (
            <>
              <span className="job-info-item">
                <strong>Iniciado:</strong> {new Date(status.started_at).toLocaleTimeString('es-ES')}
              </span>
              <span className="job-info-separator">•</span>
            </>
          )}
          {status.status === 'running' && status.started_at && (
            <span className="job-info-item">
              <strong>Tiempo:</strong> {Math.floor((new Date() - new Date(status.started_at)) / 1000)}s
            </span>
          )}
          {status.completed_at && (
            <span className="job-info-item">
              <strong>Completado:</strong> {new Date(status.completed_at).toLocaleTimeString('es-ES')}
            </span>
          )}
        </div>

        {/* Error si falló */}
        {status.status === 'failed' && status.error && (
          <div className="alert alert-error mt-3">
            <strong>Error:</strong> {status.error}
          </div>
        )}

        {/* Resumen si completó */}
        {status.status === 'completed' && status.resultado && (
          <div className="completion-summary mt-3">
            <h4 className="text-lg font-bold mb-2"><CheckCircle size={20} className="inline" /> Resumen</h4>
            <div className="summary-grid">
              <div className="summary-item">
                <span className="summary-value text-primary">
                  {status.resultado.total_referencias}
                </span>
                <span className="summary-label">Referencias</span>
              </div>
              <div className="summary-item">
                <span className="summary-value text-success">
                  {status.resultado.referencias_validadas}
                </span>
                <span className="summary-label">Validadas</span>
              </div>
              <div className="summary-item">
                <span className="summary-value text-info">
                  {(status.resultado.tasa_validacion * 100).toFixed(0)}%
                </span>
                <span className="summary-label">Tasa validación</span>
              </div>
              <div className="summary-item">
                <span className="summary-value text-warning">
                  {status.resultado.calificacion_global?.toFixed(1) || 'N/A'}/10
                </span>
                <span className="summary-label">Calificación</span>
              </div>
            </div>

            {status.resultado.tiempo_total_segundos && (
              <p className="text-center text-sm text-muted mt-2 flex items-center justify-center gap-1">
                <Clock size={14} />
                Tiempo total: {status.resultado.tiempo_total_segundos.toFixed(2)}s
              </p>
            )}
          </div>
        )}
      </div>

      <style>{`
        .phase-info {
          background: linear-gradient(135deg, #e3f2fd 0%, #e1f5fe 100%);
          border-left: 4px solid #2196f3;
          border-radius: var(--radius);
          padding: var(--spacing-md);
          margin-bottom: var(--spacing-lg);
        }

        .phase-header {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin-bottom: var(--spacing-sm);
          color: #1976d2;
        }

        .phase-icon {
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        .phase-description {
          margin: var(--spacing-sm) 0;
          color: var(--color-text);
          font-size: var(--text-sm);
          line-height: 1.5;
        }

        .agents-working {
          margin-top: var(--spacing-md);
          padding-top: var(--spacing-sm);
          border-top: 1px solid rgba(33, 150, 243, 0.2);
        }

        .agents-label {
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .agents-list {
          display: flex;
          flex-wrap: wrap;
          gap: var(--spacing-xs);
          margin-top: var(--spacing-xs);
        }

        .agent-badge {
          display: inline-block;
          padding: 4px 10px;
          background-color: rgba(33, 150, 243, 0.15);
          color: #1565c0;
          border-radius: var(--radius-full);
          font-size: var(--text-xs);
          font-weight: 500;
          border: 1px solid rgba(33, 150, 243, 0.3);
        }

        .processing-notice {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-md);
          background: linear-gradient(135deg, #fff9e6 0%, #fff3d4 100%);
          border-left: 4px solid #ffc107;
          border-radius: var(--radius);
          margin-bottom: var(--spacing-lg);
        }

        .processing-notice svg {
          flex-shrink: 0;
          color: #ff9800;
          margin-top: 2px;
        }

        .processing-notice-content {
          flex: 1;
        }

        .processing-notice-title {
          margin: 0 0 var(--spacing-xs) 0;
          font-weight: 600;
          font-size: var(--text-base);
          color: #f57c00;
        }

        .processing-notice-text {
          margin: 0;
          font-size: var(--text-sm);
          line-height: 1.6;
          color: var(--color-text);
        }

        .spinner-large {
          width: 3rem;
          height: 3rem;
          margin: 0 auto;
          animation: spin 1s linear infinite;
        }

        .status-message {
          padding: var(--spacing-md);
          background-color: var(--color-bg-secondary);
          border-radius: var(--radius);
          margin-bottom: var(--spacing-md);
        }

        .job-info-compact {
          display: flex;
          align-items: center;
          justify-content: center;
          flex-wrap: wrap;
          gap: var(--spacing-sm);
          padding: var(--spacing-sm) var(--spacing-md);
          background-color: var(--color-bg-secondary);
          border-radius: var(--radius);
          font-size: var(--text-sm);
          margin-top: var(--spacing-md);
        }

        .job-info-item {
          display: inline-flex;
          align-items: center;
          gap: var(--spacing-xs);
          color: var(--color-text);
        }

        .job-info-item strong {
          color: var(--color-text-muted);
          font-weight: 500;
        }

        .job-info-separator {
          color: var(--color-text-muted);
          opacity: 0.5;
        }

        .job-id-short {
          font-family: var(--font-mono);
          font-size: var(--text-xs);
          background-color: var(--color-gray-200);
          padding: 2px 6px;
          border-radius: var(--radius-sm);
          color: var(--color-primary);
        }

        .completion-summary {
          background-color: var(--color-primary-bg);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
          border: 1px solid var(--color-primary);
        }

        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
          gap: var(--spacing-md);
          margin-top: var(--spacing-md);
        }

        .summary-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }

        .summary-value {
          font-size: var(--text-3xl);
          font-weight: 700;
          line-height: 1;
        }

        .summary-label {
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--spacing-xs);
        }

        .alert {
          padding: var(--spacing-md);
          border-radius: var(--radius);
          border: 1px solid;
        }

        .alert-error {
          background-color: #f8d7da;
          border-color: #f5c2c7;
          color: #842029;
        }
      `}</style>
    </div>
  );
}

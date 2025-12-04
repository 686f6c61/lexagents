/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Componente Principal de la Aplicación Integra todos los componentes y maneja el flujo de trabajo
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState, useEffect } from 'react';
import { FileText, Check, X, Cpu, Users, AlertTriangle, CheckCircle2 } from 'lucide-react';
import LandingPage from './components/LandingPage';
import FileUpload from './components/FileUpload';
import PipelineConfig from './components/PipelineConfig';
import ProcessingProgress from './components/ProcessingProgress';
import ReferenciasTable from './components/ReferenciasTable';
import DownloadPanel from './components/DownloadPanel';
import AgentesModal from './components/AgentesModal';
import apiService from './services/api';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [step, setStep] = useState(1); // 1: Upload, 2: Config, 3: Processing, 4: Results
  const [archivoId, setArchivoId] = useState(null);
  const [archivoInfo, setArchivoInfo] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [apiStatus, setApiStatus] = useState('checking');
  const [systemInfo, setSystemInfo] = useState(null);
  const [showAgentesModal, setShowAgentesModal] = useState(false);

  // Verificar conexión con API y obtener información del sistema al iniciar
  useEffect(() => {
    const checkAPI = async () => {
      try {
        const info = await apiService.getSystemInfo();
        setSystemInfo(info);
        setApiStatus('connected');
      } catch (err) {
        setApiStatus('error');
        console.error('Error conectando con API:', err);
      }
    };

    checkAPI();
  }, []);

  const handleUploadSuccess = (info) => {
    setArchivoId(info.archivoId);
    setArchivoInfo(info);
    setStep(2);
  };

  const handleStartProcessing = async (config) => {
    try {
      const response = await apiService.processTema(config);
      setJobId(response.job_id);
      setStep(3);
    } catch (err) {
      console.error('Error iniciando procesamiento:', err);
      alert('Error al iniciar el procesamiento');
    }
  };

  const handleProcessingComplete = (result) => {
    setResultado(result);
    setStep(4);
  };

  const handleProcessingError = (error) => {
    alert(`Error en el procesamiento: ${error}`);
    setStep(2);
  };

  const handleReset = () => {
    setStep(1);
    setArchivoId(null);
    setArchivoInfo(null);
    setJobId(null);
    setResultado(null);
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="container">
          <div className="header-content">
            <div className="logo clickable" onClick={() => setShowLanding(true)}>
              <FileText size={32} />
              <div>
                <h1>LexAgents</h1>
                <p>Extracción automática de referencias legales - BOE y EUR-Lex</p>
              </div>
            </div>

          </div>
        </div>
      </header>

      {/* Landing Page */}
      {showLanding && (
        <main className="app-main">
          <LandingPage onStart={() => setShowLanding(false)} />
        </main>
      )}

      {/* Main Content */}
      {!showLanding && (
        <main className="app-main">
          <div className="container">
          {/* Breadcrumb / Progress */}
          <div className="progress-steps">
            <div className={`step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
              <div className="step-number">1</div>
              <div className="step-label">Subir archivo</div>
            </div>
            <div className="step-line" />
            <div className={`step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
              <div className="step-number">2</div>
              <div className="step-label">Configurar</div>
            </div>
            <div className="step-line" />
            <div className={`step ${step >= 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}`}>
              <div className="step-number">3</div>
              <div className="step-label">Procesar</div>
            </div>
            <div className="step-line" />
            <div className={`step ${step >= 4 ? 'active' : ''}`}>
              <div className="step-number">4</div>
              <div className="step-label">Resultados</div>
            </div>
          </div>

          {/* Step 1: Upload */}
          {step === 1 && (
            <div className="step-content">
              <FileUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          )}

          {/* Step 2: Config */}
          {step === 2 && (
            <div className="step-content">
              {archivoInfo && (
                <div className="info-banner">
                  <FileText size={20} />
                  <span>Archivo: <strong>{archivoInfo.nombreOriginal}</strong></span>
                  <span className="text-muted">
                    ({(archivoInfo.tamaño / 1024).toFixed(2)} KB)
                  </span>
                </div>
              )}

              <PipelineConfig
                archivoId={archivoId}
                onStartProcessing={handleStartProcessing}
              />

              <button onClick={handleReset} className="btn btn-secondary mt-3">
                ← Volver a subir archivo
              </button>
            </div>
          )}

          {/* Step 3: Processing */}
          {step === 3 && (
            <div className="step-content">
              <ProcessingProgress
                jobId={jobId}
                onComplete={handleProcessingComplete}
                onError={handleProcessingError}
              />

              <button onClick={handleReset} className="btn btn-secondary mt-3">
                ← Cancelar y volver
              </button>
            </div>
          )}

          {/* Step 4: Results */}
          {step === 4 && resultado && (
            <div className="step-content">
              {/* Descarga */}
              <DownloadPanel
                jobId={jobId}
                archivosExportados={resultado.archivos_exportados}
              />

              {/* Tabla de referencias */}
              <ReferenciasTable
                referencias={resultado.referencias || []}
                referenciasInferidas={resultado.referencias_inferidas || []}
              />

              {/* Botón para nuevo procesamiento */}
              <div className="actions-footer">
                <button onClick={handleReset} className="btn btn-primary btn-lg">
                  ← Procesar otro tema
                </button>
              </div>
            </div>
          )}
          </div>
        </main>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div className="container">
          <p className="footer-content">
            <span className="footer-item">
              <Cpu size={16} />
              LexAgents
            </span>
            <span className="footer-separator">•</span>
            <span className="footer-item">
              <FileText size={16} />
              BOE y EUR-Lex
            </span>
            <span className="footer-separator">•</span>
            <span className="footer-item">2025</span>
            <span className="footer-separator">•</span>
            <a href="https://686f6c61.dev" target="_blank" rel="noopener noreferrer" className="footer-link">
              686f6c61.dev
            </a>
          </p>
        </div>
      </footer>

      {/* Modal de Agentes */}
      <AgentesModal
        isOpen={showAgentesModal}
        onClose={() => setShowAgentesModal(false)}
        systemInfo={systemInfo}
      />

      <style>{`
        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        .app-header {
          background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
          color: white;
          padding: var(--spacing-xl) 0;
          box-shadow: var(--shadow-lg);
        }

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .logo {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        }

        .logo.clickable {
          cursor: pointer;
          transition: var(--transition);
        }

        .logo.clickable:hover {
          opacity: 0.9;
        }

        .logo h1 {
          font-size: var(--text-3xl);
          margin: 0;
          color: white;
        }

        .logo p {
          font-size: var(--text-sm);
          opacity: 0.9;
          margin: 0;
        }

        .system-status {
          display: flex;
          gap: var(--spacing-sm);
          flex-wrap: wrap;
        }

        .status-badge {
          padding: var(--spacing-sm) var(--spacing-md);
          border-radius: var(--radius-full);
          font-size: var(--text-sm);
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          white-space: nowrap;
        }

        .status-checking {
          background-color: rgba(255, 255, 255, 0.2);
        }

        .status-connected {
          background-color: rgba(32, 201, 151, 0.3);
        }

        .status-model {
          background-color: rgba(99, 102, 241, 0.3);
        }

        .status-agents {
          background-color: rgba(59, 130, 246, 0.3);
        }

        .status-disabled {
          background-color: rgba(156, 163, 175, 0.3);
          opacity: 0.7;
        }

        .status-warning {
          background-color: rgba(251, 191, 36, 0.3);
        }

        .status-error {
          background-color: rgba(220, 53, 69, 0.3);
        }

        .status-badge.clickable {
          cursor: pointer;
          transition: var(--transition);
        }

        .status-badge.clickable:hover {
          transform: scale(1.05);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }

        .app-main {
          flex: 1;
          padding: var(--spacing-2xl) 0;
        }

        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 var(--spacing-lg);
        }

        .progress-steps {
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: var(--spacing-2xl);
          padding: var(--spacing-lg);
          background: white;
          border-radius: var(--radius-lg);
          box-shadow: var(--shadow);
        }

        .step {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--spacing-xs);
        }

        .step-number {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-color: var(--color-gray-200);
          color: var(--color-gray-600);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          transition: var(--transition);
        }

        .step.active .step-number {
          background-color: var(--color-primary);
          color: white;
        }

        .step.completed .step-number {
          background-color: var(--color-success);
          color: white;
        }

        .step-label {
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          font-weight: 500;
        }

        .step.active .step-label {
          color: var(--color-primary);
          font-weight: 600;
        }

        .step-line {
          width: 60px;
          height: 2px;
          background-color: var(--color-gray-200);
        }

        .step-content {
          max-width: 900px;
          margin: 0 auto;
        }

        .info-banner {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          padding: var(--spacing-md);
          background-color: var(--color-primary-bg);
          border-radius: var(--radius);
          margin-bottom: var(--spacing-lg);
          border: 1px solid var(--color-primary);
        }

        .actions-footer {
          margin-top: var(--spacing-xl);
          text-align: center;
        }

        .app-footer {
          background-color: var(--color-gray-700);
          color: white;
          padding: var(--spacing-xl) 0;
          text-align: center;
          margin-top: auto;
        }

        .footer-content {
          margin: 0;
          font-size: var(--text-sm);
          opacity: 0.9;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-wrap: wrap;
          gap: var(--spacing-sm);
        }

        .footer-item {
          display: inline-flex;
          align-items: center;
          gap: var(--spacing-xs);
        }

        .footer-separator {
          opacity: 0.6;
        }

        .footer-link {
          color: white;
          text-decoration: underline;
          transition: var(--transition);
        }

        .footer-link:hover {
          color: var(--color-primary-light);
          text-decoration: underline;
        }
      `}</style>
    </div>
  );
}

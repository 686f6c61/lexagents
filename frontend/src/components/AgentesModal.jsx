/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Modal de Información de Agentes Explica el sistema multi-agente y la orquestación
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { X, Users, Cpu, Database, GitBranch, Search, FileText, Settings, CheckCircle2, Circle, AlertCircle, Globe } from 'lucide-react';

export default function AgentesModal({ isOpen, onClose, systemInfo }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>
            <Users size={24} />
            SISTEMA MULTI-AGENTE DE EXTRACCIÓN
          </h2>
          <button className="modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="modal-body">
          {/* Introducción */}
          <section className="modal-section">
            <h3>
              <GitBranch size={20} />
              ¿CÓMO FUNCIONA EL SISTEMA?
            </h3>
            <p>
              LexAgents integra <strong>8 agentes especializados de IA</strong> que trabajan en equipo.
              Cada agente tiene un rol específico y diferente configuración
              para maximizar la cobertura y exactitud en la extracción de referencias legales.
            </p>
          </section>

          {/* Agentes de Extracción */}
          <section className="modal-section">
            <h3>
              <Cpu size={20} />
              FASE 1: EXTRACCIÓN (3 AGENTES)
            </h3>
            <div className="agents-list">
              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge conservative">A</span>
                  <strong>Extractor Conservador</strong>
                  <span className="temp-badge">temp=0.1</span>
                </div>
                <p>
                  Enfoque preciso y cauteloso. Solo extrae referencias cuando está muy seguro.
                  Prioriza la precisión sobre la cobertura.
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge aggressive">B</span>
                  <strong>Extractor Agresivo</strong>
                  <span className="temp-badge">temp=0.4</span>
                </div>
                <p>
                  Enfoque amplio y exploratorio. Busca referencias menos obvias y contextuales.
                  Prioriza la cobertura sobre la precisión.
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge detective">C</span>
                  <strong>Extractor Sabueso</strong>
                  <span className="temp-badge">temp=0.4</span>
                </div>
                <p>
                  Especialista en referencias implícitas. Detecta menciones indirectas a normativas
                  y principios legales.
                </p>
              </div>
            </div>
          </section>

          {/* Agentes de Resolución */}
          <section className="modal-section">
            <h3>
              <Database size={20} />
              FASE 2: RESOLUCIÓN, VALIDACIÓN Y ENRIQUECIMIENTO (6 AGENTES)
            </h3>
            <div className="agents-list">
              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge resolver">
                    <Search size={16} />
                  </span>
                  <strong>Resolver de Contexto (BETA)</strong>
                </div>
                <p>
                  Completa referencias incompletas analizando el contexto circundante.
                  Ejemplo: "art. 23" cerca de "CP" → "art. 23 del Código Penal"
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge resolver">
                    <FileText size={16} />
                  </span>
                  <strong>Resolver de Títulos</strong>
                </div>
                <p>
                  Completa títulos de leyes a partir de abreviaturas.
                  Ejemplo: "LPAC" → "Ley 39/2015, de 1 de octubre"
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge normalizer">
                    <Settings size={16} />
                  </span>
                  <strong>Normalizador</strong>
                </div>
                <p>
                  Estandariza el formato de todas las referencias. Elimina duplicados
                  y calcula niveles de confianza.
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge validator">
                    <CheckCircle2 size={16} />
                  </span>
                  <strong>Validador BOE</strong>
                </div>
                <p>
                  Verifica cada referencia contra la API oficial del BOE.
                  Obtiene IDs oficiales y URLs directas.
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge eurlex">
                    <Globe size={16} />
                  </span>
                  <strong>Extractor EUR-Lex</strong>
                  <span className="temp-badge">temp=0.1</span>
                </div>
                <p>
                  Extrae artículos de legislación europea desde EUR-Lex.
                  Genera identificadores CELEX y obtiene textos completos de Reglamentos UE y Directivas CE.
                </p>
              </div>

              <div className="agent-card">
                <div className="agent-header">
                  <span className="agent-badge inference">
                    <AlertCircle size={16} />
                  </span>
                  <strong>Agente de Inferencia (BETA)</strong>
                  <span className="temp-badge">temp=0.1</span>
                </div>
                <p>
                  Detecta conceptos legales implícitos sin referencias explícitas y sugiere normativa aplicable.
                  Ejemplo: detecta "homicidio" y sugiere artículos relevantes del Código Penal.
                  Siempre activo durante el procesamiento.
                </p>
              </div>
            </div>
          </section>

          {/* Orquestación */}
          <section className="modal-section">
            <h3>
              <GitBranch size={20} />
              ORQUESTACIÓN DEL PIPELINE
            </h3>
            <div className="pipeline-flow">
              <div className="flow-step">
                <div className="flow-number">1</div>
                <div className="flow-content">
                  <strong>Extracción Paralela</strong>
                  <p>Los 3 extractores procesan el texto simultáneamente</p>
                </div>
              </div>
              <div className="flow-arrow">↓</div>
              <div className="flow-step">
                <div className="flow-number">2</div>
                <div className="flow-content">
                  <strong>Resolución de Contexto</strong>
                  <p>Se completan referencias incompletas</p>
                </div>
              </div>
              <div className="flow-arrow">↓</div>
              <div className="flow-step">
                <div className="flow-number">3</div>
                <div className="flow-content">
                  <strong>Resolución de Títulos</strong>
                  <p>Se expanden abreviaturas y nombres cortos</p>
                </div>
              </div>
              <div className="flow-arrow">↓</div>
              <div className="flow-step">
                <div className="flow-number">4</div>
                <div className="flow-content">
                  <strong>Normalización</strong>
                  <p>Se unifican formatos y eliminan duplicados</p>
                </div>
              </div>
              <div className="flow-arrow">↓</div>
              <div className="flow-step">
                <div className="flow-number">5</div>
                <div className="flow-content">
                  <strong>Validación BOE</strong>
                  <p>Se verifican contra la base de datos oficial</p>
                </div>
              </div>
              <div className="flow-arrow">↓</div>
              <div className="flow-step">
                <div className="flow-number">6</div>
                <div className="flow-content">
                  <strong>Convergencia</strong>
                  <p>Se repiten pasos 2-5 hasta converger (máx 3 rondas)</p>
                </div>
              </div>
            </div>
          </section>

          {/* Integración BOE */}
          <section className="modal-section">
            <h3>
              <Database size={20} />
              INTEGRACIÓN CON API DEL BOE
            </h3>
            <p>
              El sistema se conecta directamente con la <strong>API oficial del Boletín Oficial del Estado</strong>:
            </p>
            <ul>
              <li>
                <strong>Búsqueda de normas:</strong> Encuentra documentos por título, número y año
              </li>
              <li>
                <strong>Validación de IDs:</strong> Verifica que cada referencia existe en el BOE
              </li>
              <li>
                <strong>Obtención de metadatos:</strong> Título completo, fecha de publicación, estado de vigencia
              </li>
              <li>
                <strong>Extracción de artículos:</strong> Descarga el texto completo de artículos específicos
              </li>
            </ul>
            <div className="info-box">
              <div className="status-line">
                <strong>Estado actual:</strong>
                {systemInfo?.boe_conectado ? (
                  <span className="status-indicator status-success">
                    <CheckCircle2 size={16} />
                    Conectado
                  </span>
                ) : (
                  <span className="status-indicator status-error">
                    <AlertCircle size={16} />
                    Desconectado
                  </span>
                )}
              </div>
              <div className="status-line">
                <strong>Endpoint:</strong> <code>{systemInfo?.boe_url}</code>
              </div>
            </div>
          </section>

          {/* Integración EUR-Lex */}
          <section className="modal-section">
            <h3>
              <Globe size={20} />
              INTEGRACIÓN CON EUR-LEX
            </h3>
            <p>
              El sistema se integra con <strong>EUR-Lex</strong>, la base de datos oficial de legislación de la Unión Europea:
            </p>
            <ul>
              <li>
                <strong>Detección automática:</strong> Identifica Reglamentos UE, Directivas CE y Decisiones
              </li>
              <li>
                <strong>Generación de CELEX:</strong> Crea identificadores oficiales de documentos europeos
              </li>
              <li>
                <strong>Extracción de artículos:</strong> Descarga textos completos mediante web scraping avanzado
              </li>
              <li>
                <strong>Enlaces directos:</strong> Genera URLs a la documentación oficial en EUR-Lex
              </li>
            </ul>
            <div className="info-box">
              <div className="status-line">
                <strong>Estado actual:</strong>
                {systemInfo?.eurlex_conectado ? (
                  <span className="status-indicator status-success">
                    <CheckCircle2 size={16} />
                    Conectado
                  </span>
                ) : (
                  <span className="status-indicator status-error">
                    <AlertCircle size={16} />
                    Desconectado
                  </span>
                )}
              </div>
              <div className="status-line">
                <strong>Endpoint:</strong> <code>{systemInfo?.eurlex_url}</code>
              </div>
            </div>
          </section>

          {/* Configuración */}
          <section className="modal-section">
            <h3>CONFIGURACIÓN DEL SISTEMA</h3>
            <div className="config-grid">
              <div className="config-item">
                <strong>Modelo IA:</strong>
                <span>{systemInfo?.modelo_ia}</span>
              </div>
              <div className="config-item">
                <strong>Rondas máx:</strong>
                <span>{systemInfo?.max_rondas}</span>
              </div>
              <div className="config-item">
                <strong>Workers:</strong>
                <span>{systemInfo?.max_workers}</span>
              </div>
              <div className="config-item">
                <strong>Estado IA:</strong>
                {systemInfo?.gemini_conectado ? (
                  <span className="status-indicator status-success">
                    <CheckCircle2 size={14} />
                    Activa
                  </span>
                ) : (
                  <span className="status-indicator status-error">
                    <AlertCircle size={14} />
                    Inactiva
                  </span>
                )}
              </div>
            </div>
          </section>
        </div>

        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>
            Entendido
          </button>
        </div>
      </div>

      <style>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: var(--spacing-lg);
        }

        .modal-content {
          background: white;
          border-radius: var(--radius-lg);
          max-width: 900px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: var(--shadow-xl);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: var(--spacing-xl);
          border-bottom: 2px solid var(--color-border);
          position: sticky;
          top: 0;
          background: white;
          z-index: 10;
        }

        .modal-header h2 {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin: 0;
          color: var(--color-primary);
        }

        .modal-close {
          background: none;
          border: none;
          cursor: pointer;
          padding: var(--spacing-xs);
          color: var(--color-text-muted);
          transition: var(--transition);
        }

        .modal-close:hover {
          color: var(--color-primary);
        }

        .modal-body {
          padding: var(--spacing-xl);
        }

        .modal-section {
          margin-bottom: var(--spacing-2xl);
        }

        .modal-section h3 {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          color: var(--color-primary);
          margin-bottom: var(--spacing-md);
          font-size: var(--text-xl);
        }

        .modal-section p {
          color: var(--color-text);
          line-height: 1.6;
          margin-bottom: var(--spacing-md);
        }

        .modal-section ul {
          margin-left: var(--spacing-lg);
          color: var(--color-text);
        }

        .modal-section ul li {
          margin-bottom: var(--spacing-sm);
          line-height: 1.6;
        }

        .agents-list {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        }

        .agent-card {
          background-color: var(--color-bg-secondary);
          padding: var(--spacing-md);
          border-radius: var(--radius);
          border-left: 4px solid var(--color-primary);
        }

        .agent-header {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin-bottom: var(--spacing-sm);
        }

        .agent-badge {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          color: white;
          font-size: var(--text-sm);
        }

        .agent-badge.conservative {
          background-color: #0d6efd;
        }

        .agent-badge.aggressive {
          background-color: #dc3545;
        }

        .agent-badge.detective {
          background-color: #6f42c1;
        }

        .agent-badge.resolver {
          background-color: #fd7e14;
        }

        .agent-badge.normalizer {
          background-color: #20c997;
        }

        .agent-badge.validator {
          background-color: #198754;
        }

        .agent-badge.eurlex {
          background-color: #0066cc;
        }

        .agent-badge.inference {
          background-color: #f59e0b;
        }

        .temp-badge {
          background-color: var(--color-gray-200);
          padding: 2px 8px;
          border-radius: var(--radius);
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          font-family: monospace;
        }

        .agent-card p {
          margin: 0;
          font-size: var(--text-sm);
          color: var(--color-text-muted);
        }

        .pipeline-flow {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .flow-step {
          display: flex;
          gap: var(--spacing-md);
          align-items: center;
          background-color: var(--color-bg-secondary);
          padding: var(--spacing-md);
          border-radius: var(--radius);
        }

        .flow-number {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background-color: var(--color-primary);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          flex-shrink: 0;
        }

        .flow-content {
          flex: 1;
        }

        .flow-content strong {
          display: block;
          margin-bottom: 4px;
          color: var(--color-primary);
        }

        .flow-content p {
          margin: 0;
          font-size: var(--text-sm);
          color: var(--color-text-muted);
        }

        .flow-arrow {
          text-align: center;
          color: var(--color-primary);
          font-size: var(--text-2xl);
          font-weight: bold;
        }

        .info-box {
          background-color: var(--color-primary-bg);
          border: 1px solid var(--color-primary);
          padding: var(--spacing-md);
          border-radius: var(--radius);
          margin-top: var(--spacing-md);
          font-size: var(--text-sm);
          line-height: 1.8;
        }

        .info-box code {
          background-color: white;
          padding: 2px 6px;
          border-radius: var(--radius);
          font-family: monospace;
          font-size: var(--text-xs);
        }

        .status-line {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin-bottom: var(--spacing-xs);
        }

        .status-line:last-child {
          margin-bottom: 0;
        }

        .status-indicator {
          display: inline-flex;
          align-items: center;
          gap: var(--spacing-xs);
          font-weight: 600;
          padding: 2px 8px;
          border-radius: var(--radius);
          font-size: var(--text-sm);
        }

        .status-success {
          color: #198754;
          background-color: rgba(25, 135, 84, 0.1);
        }

        .status-error {
          color: #dc3545;
          background-color: rgba(220, 53, 69, 0.1);
        }

        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: var(--spacing-md);
          margin-top: var(--spacing-md);
        }

        .config-item {
          background-color: var(--color-bg-secondary);
          padding: var(--spacing-md);
          border-radius: var(--radius);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
        }

        .config-item strong {
          color: var(--color-text-muted);
          font-size: var(--text-sm);
        }

        .config-item span {
          color: var(--color-text);
          font-weight: 600;
        }

        .modal-footer {
          padding: var(--spacing-lg) var(--spacing-xl);
          border-top: 2px solid var(--color-border);
          display: flex;
          justify-content: flex-end;
          position: sticky;
          bottom: 0;
          background: white;
        }
      `}</style>
    </div>
  );
}

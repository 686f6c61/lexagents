/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Landing Page Página de bienvenida que explica el sistema
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { FileText, Cpu, CheckCircle, ArrowRight, Upload, Zap } from 'lucide-react';

export default function LandingPage({ onStart }) {
  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-icon">
          <FileText size={64} />
        </div>
        <h1 className="hero-title">Sistema inteligente de extracción de referencias legales para opositores</h1>
        <p className="hero-description">
          Sube tus temarios en <strong>PDF, Word, TXT o Markdown</strong> y obtén automáticamente
          todas las referencias normativas extraídas y validadas por <strong>9 agentes de IA especializados</strong>.
        </p>
        <button onClick={onStart} className="btn btn-primary btn-lg hero-cta-button">
          <ArrowRight size={20} />
          Comenzar
        </button>
      </section>

      {/* Características principales */}
      <section className="features">
        <div className="feature-card">
          <Upload size={32} className="feature-icon" />
          <h3>Multi-formato</h3>
          <p>Sube archivos PDF, Word, TXT o Markdown</p>
        </div>

        <div className="feature-card">
          <Cpu size={32} className="feature-icon" />
          <h3>9 Agentes IA</h3>
          <p>Sistema multi-agente con convergencia iterativa</p>
        </div>

        <div className="feature-card">
          <CheckCircle size={32} className="feature-icon" />
          <h3>Validación BOE</h3>
          <p>Referencias verificadas contra el BOE oficial</p>
        </div>

        <div className="feature-card">
          <Zap size={32} className="feature-icon" />
          <h3>EUR-Lex</h3>
          <p>Integración con normativa europea</p>
        </div>
      </section>

      {/* Cómo funciona */}
      <section className="how-it-works">
        <h2>¿Cómo funciona?</h2>
        <div className="process-steps">
          <div className="process-step">
            <div className="step-number">1</div>
            <h3>Subes tu temario</h3>
            <p>Carga tu archivo en cualquier formato: PDF, Word, TXT o Markdown</p>
          </div>
          <div className="process-step">
            <div className="step-number">2</div>
            <h3>Análisis inteligente</h3>
            <p>9 agentes especializados de IA analizan el texto para extraer todas las referencias legales</p>
          </div>
          <div className="process-step">
            <div className="step-number">3</div>
            <h3>Validación oficial</h3>
            <p>Cada referencia se verifica contra las bases de datos del BOE y EUR-Lex</p>
          </div>
          <div className="process-step">
            <div className="step-number">4</div>
            <h3>Descarga resultados</h3>
            <p>Obtén un informe completo en Markdown, TXT, Word o PDF con todas las referencias validadas</p>
          </div>
        </div>
      </section>

      {/* Normativa Europea EUR-Lex */}
      <section className="eurlex-section">
        <h2>Normativa Europea a través de EUR-Lex</h2>
        <p className="eurlex-intro">
          El sistema está integrado con EUR-Lex, la base de datos oficial de legislación europea, permitiendo detectar y validar normativa comunitaria
        </p>
        <div className="eurlex-features">
          <div className="eurlex-card">
            <h4>Reglamentos UE</h4>
            <p>Legislación de aplicación directa en todos los Estados miembros</p>
            <p className="eurlex-example">Ejemplo: Reglamento (UE) 2016/679 (RGPD)</p>
          </div>
          <div className="eurlex-card">
            <h4>Directivas CE</h4>
            <p>Normas que deben ser transpuestas a la legislación nacional</p>
            <p className="eurlex-example">Ejemplo: Directiva 2008/98/CE (Residuos)</p>
          </div>
          <div className="eurlex-card">
            <h4>Decisiones UE</h4>
            <p>Actos vinculantes para destinatarios específicos</p>
            <p className="eurlex-example">Ejemplo: Decisiones de la Comisión</p>
          </div>
        </div>
      </section>

      {/* Los 9 Agentes */}
      <section className="agents-detail">
        <h2>Los 9 agentes especializados</h2>
        <p className="agents-intro">
          Cada agente tiene una función específica que garantiza la máxima precisión en la extracción de referencias legales
        </p>
        <div className="agents-list">
          <div className="agent-item">
            <span className="agent-number">1-3</span>
            <div className="agent-content">
              <h4>Extractores de referencias</h4>
              <p>Localizan todas las referencias legales en el texto con diferentes niveles de precisión para no perder ninguna</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">4</span>
            <div className="agent-content">
              <h4>Resolver de contexto</h4>
              <p>Completa referencias incompletas analizando el contexto circundante</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">5</span>
            <div className="agent-content">
              <h4>Resolver de títulos</h4>
              <p>Identifica leyes completas desde títulos abreviados (ej: "CP" → "Código Penal")</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">6</span>
            <div className="agent-content">
              <h4>Normalizador</h4>
              <p>Estandariza el formato de todas las referencias para facilitar su lectura</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">7</span>
            <div className="agent-content">
              <h4>Validador BOE</h4>
              <p>Verifica que cada referencia exista en la base de datos oficial del BOE</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">8</span>
            <div className="agent-content">
              <h4>Extractor EUR-Lex</h4>
              <p>Localiza y procesa normativa europea (Reglamentos, Directivas y Decisiones UE)</p>
            </div>
          </div>

          <div className="agent-item">
            <span className="agent-number">9</span>
            <div className="agent-content">
              <h4>Agente de inferencia (BETA)</h4>
              <p>Sugiere normativa aplicable basándose en conceptos legales detectados en el contexto pero no directamente referenciados</p>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="faq">
        <h2>Preguntas frecuentes</h2>
        <div className="faq-list">
          <div className="faq-item">
            <h3>¿Qué es un agente de IA?</h3>
            <p>Son programas especializados que realizan tareas específicas. En este sistema, cada agente tiene una función concreta: extraer referencias, validarlas, normalizarlas, etc. Trabajando juntos, garantizan la máxima precisión.</p>
          </div>

          <div className="faq-item">
            <h3>¿Qué referencias puede detectar?</h3>
            <p>Puede detectar cualquier legislación recogida en el BOE: leyes españolas (CP, LOPJ, CE, etc.), normativa autonómica, reales decretos, órdenes ministeriales, y también normativa europea (Reglamentos UE, Directivas CE). Además, puede sugerir normativa aplicable basándose en conceptos legales mencionados en tu temario.</p>
          </div>

          <div className="faq-item">
            <h3>¿Cómo se validan las referencias?</h3>
            <p>Cada referencia se comprueba contra la API oficial del BOE para normativa española y EUR-Lex para normativa europea, asegurando que existe y está vigente.</p>
          </div>

          <div className="faq-item">
            <h3>¿Qué significa "Referencias inferidas (BETA)"?</h3>
            <p>Son sugerencias de normativa aplicable que el sistema detecta basándose en conceptos legales mencionados en el texto, aunque no estén explícitamente citados. Por ejemplo, si se menciona "homicidio", sugiere artículos relevantes del Código Penal.</p>
          </div>

          <div className="faq-item">
            <h3>¿En qué formatos puedo descargar los resultados?</h3>
            <p>Los resultados se pueden descargar en cuatro formatos: Markdown (.md) con enlaces clickeables, texto plano (.txt), documento Word (.docx) y PDF (.pdf).</p>
          </div>

          <div className="faq-item">
            <h3>¿Los datos de mi temario se guardan?</h3>
            <p>No. El procesamiento es temporal y los archivos se eliminan automáticamente del servidor tras completar el análisis.</p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta">
        <button onClick={onStart} className="btn btn-primary btn-lg cta-button">
          <ArrowRight size={20} />
          Comenzar
        </button>
      </section>

      <style>{`
        .landing-page {
          max-width: 900px;
          margin: 0 auto;
          padding: var(--spacing-2xl) var(--spacing-lg);
        }

        /* Hero */
        .hero {
          text-align: center;
          margin-bottom: var(--spacing-2xl);
        }

        .hero-icon {
          display: inline-flex;
          padding: var(--spacing-lg);
          background-color: var(--color-primary-bg);
          border-radius: var(--radius-xl);
          color: var(--color-primary);
          margin-bottom: var(--spacing-lg);
        }

        .hero-title {
          font-size: var(--text-4xl);
          margin-bottom: var(--spacing-sm);
          color: var(--color-text);
        }

        .hero-subtitle {
          font-size: var(--text-xl);
          color: var(--color-text-muted);
          margin-bottom: var(--spacing-lg);
        }

        .hero-description {
          font-size: var(--text-lg);
          line-height: 1.7;
          color: var(--color-text);
          max-width: 700px;
          margin: 0 auto var(--spacing-lg) auto;
        }

        .hero-cta-button {
          margin-top: var(--spacing-md);
        }

        /* Features */
        .features {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: var(--spacing-lg);
          margin-bottom: var(--spacing-2xl);
        }

        .feature-card {
          text-align: center;
          padding: var(--spacing-lg);
          background-color: var(--color-bg);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-lg);
          transition: var(--transition);
        }

        .feature-card:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-md);
        }

        .feature-icon {
          color: var(--color-primary);
          margin-bottom: var(--spacing-sm);
        }

        .feature-card h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--spacing-xs);
        }

        .feature-card p {
          font-size: var(--text-sm);
          color: var(--color-text-muted);
        }

        /* How it works */
        .how-it-works {
          margin-bottom: var(--spacing-2xl);
        }

        .how-it-works h2 {
          text-align: center;
          color: var(--color-text);
          margin-bottom: var(--spacing-xl);
          font-size: var(--text-3xl);
        }

        .process-steps {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: var(--spacing-lg);
        }

        .process-step {
          text-align: center;
        }

        .step-number {
          width: 3rem;
          height: 3rem;
          display: flex;
          align-items: center;
          justify-content: center;
          background-color: var(--color-primary);
          color: white;
          font-size: var(--text-2xl);
          font-weight: 700;
          border-radius: var(--radius-full);
          margin: 0 auto var(--spacing-md) auto;
        }

        .process-step h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--spacing-sm);
          color: var(--color-text);
        }

        .process-step p {
          font-size: var(--text-sm);
          color: var(--color-text-muted);
          line-height: 1.6;
        }

        /* EUR-Lex Section */
        .eurlex-section {
          margin-bottom: var(--spacing-2xl);
        }

        .eurlex-section h2 {
          text-align: center;
          color: var(--color-text);
          margin-bottom: var(--spacing-md);
          font-size: var(--text-3xl);
        }

        .eurlex-intro {
          text-align: center;
          font-size: var(--text-base);
          color: var(--color-text);
          margin-bottom: var(--spacing-xl);
          line-height: 1.6;
          max-width: 700px;
          margin-left: auto;
          margin-right: auto;
        }

        .eurlex-features {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: var(--spacing-lg);
          max-width: 900px;
          margin: 0 auto;
        }

        .eurlex-card {
          background-color: var(--color-bg);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
          transition: var(--transition);
        }

        .eurlex-card:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-md);
        }

        .eurlex-card h4 {
          font-size: var(--text-lg);
          margin-bottom: var(--spacing-sm);
          color: var(--color-primary);
          font-weight: 600;
        }

        .eurlex-card p {
          font-size: var(--text-sm);
          color: var(--color-text-muted);
          line-height: 1.6;
          margin-bottom: var(--spacing-sm);
        }

        .eurlex-example {
          font-size: var(--text-xs);
          color: var(--color-text);
          font-style: italic;
          font-weight: 500;
          margin-top: var(--spacing-sm);
          margin-bottom: 0;
        }

        /* Agents Detail */
        .agents-detail {
          margin-bottom: var(--spacing-2xl);
        }

        .agents-detail h2 {
          text-align: center;
          color: var(--color-text);
          margin-bottom: var(--spacing-md);
          font-size: var(--text-3xl);
        }

        .agents-intro {
          text-align: center;
          font-size: var(--text-base);
          color: var(--color-text);
          margin-bottom: var(--spacing-xl);
          line-height: 1.6;
          max-width: 700px;
          margin-left: auto;
          margin-right: auto;
        }

        .agents-list {
          max-width: 800px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        }

        .agent-item {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-md);
          padding: var(--spacing-lg);
          background-color: var(--color-bg);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-lg);
          transition: var(--transition);
        }

        .agent-item:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-sm);
        }

        .agent-number {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 2.5rem;
          height: 2.5rem;
          background-color: var(--color-primary);
          color: white;
          font-weight: 700;
          font-size: var(--text-base);
          border-radius: var(--radius-full);
        }

        .agent-content h4 {
          font-size: var(--text-lg);
          margin: 0 0 var(--spacing-xs) 0;
          color: var(--color-text);
        }

        .agent-content p {
          font-size: var(--text-base);
          color: var(--color-text-muted);
          line-height: 1.6;
          margin: 0;
        }

        /* FAQ */
        .faq {
          margin-bottom: var(--spacing-2xl);
        }

        .faq h2 {
          text-align: center;
          color: var(--color-text);
          margin-bottom: var(--spacing-xl);
          font-size: var(--text-3xl);
        }

        .faq-list {
          max-width: 800px;
          margin: 0 auto;
        }

        .faq-item {
          background-color: var(--color-bg);
          border: 2px solid var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--spacing-lg);
          margin-bottom: var(--spacing-md);
          transition: var(--transition);
        }

        .faq-item:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-sm);
        }

        .faq-item h3 {
          font-size: var(--text-lg);
          margin-bottom: var(--spacing-sm);
          color: var(--color-primary);
        }

        .faq-item p {
          font-size: var(--text-base);
          color: var(--color-text);
          line-height: 1.7;
          margin: 0;
        }

        /* CTA */
        .cta {
          text-align: center;
        }

        .cta-button {
          font-size: var(--text-lg);
          padding: var(--spacing-md) var(--spacing-2xl);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .landing-page {
            padding: var(--spacing-xl) var(--spacing-md);
          }

          .hero-title {
            font-size: var(--text-3xl);
          }

          .hero-subtitle {
            font-size: var(--text-lg);
          }

          .hero-description {
            font-size: var(--text-base);
          }

          .features {
            grid-template-columns: 1fr;
          }

          .agent-item {
            flex-direction: column;
            text-align: center;
          }
        }
      `}</style>
    </div>
  );
}

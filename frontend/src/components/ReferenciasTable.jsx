/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Tabla de Referencias Muestra las referencias extraídas con filtros y búsqueda
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState, useMemo } from 'react';
import { Search, Filter, CheckCircle, ExternalLink, ChevronDown, ChevronRight, Loader, List, AlertTriangle, Brain } from 'lucide-react';
import React from 'react';
import apiService from '../services/api';

export default function ReferenciasTable({ referencias = [], referenciasInferidas = [] }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterTipo, setFilterTipo] = useState('todos');
  // Filtro de validación eliminado - ahora solo mostramos referencias con URLs válidas
  const [sortBy, setSortBy] = useState('confianza');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showBeta, setShowBeta] = useState(true);

  // Estados para el acordeón de artículos
  const [expandedArticles, setExpandedArticles] = useState({});
  const [articlesData, setArticlesData] = useState({});
  const [loadingArticles, setLoadingArticles] = useState({});

  // Obtener tipos únicos
  const tipos = useMemo(() => {
    const uniqueTipos = [...new Set(referencias.map(r => r.tipo))];
    return uniqueTipos.sort();
  }, [referencias]);

  // Filtrar y ordenar referencias
  const referenciasFiltradas = useMemo(() => {
    let filtered = referencias;

    // Búsqueda
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(ref =>
        ref.texto_completo?.toLowerCase().includes(term) ||
        ref.ley?.toLowerCase().includes(term) ||
        ref.articulo?.toLowerCase().includes(term)
      );
    }

    // Filtro por tipo
    if (filterTipo !== 'todos') {
      filtered = filtered.filter(ref => ref.tipo === filterTipo);
    }

    // Filtro: solo mostrar referencias que tienen BOE-ID o son EUR-Lex
    filtered = filtered.filter(ref => {
      // Tiene BOE-ID (legislación española validada)
      if (ref.boe_id) return true;

      // Es legislación europea (Reglamentos, Directivas, Decisiones UE/CE)
      const texto = ref.texto_completo || '';
      const esEurlex = ['Reglamento (UE)', 'Reglamento (CE)', 'Directiva (UE)',
                        'Directiva (CE)', 'Decisión (UE)', 'Decisión (CE)']
                       .some(p => texto.includes(p));
      if (esEurlex) return true;

      return false;
    });

    // Ordenar
    filtered = [...filtered].sort((a, b) => {
      let aVal, bVal;

      switch (sortBy) {
        case 'confianza':
          aVal = a.confianza || 0;
          bVal = b.confianza || 0;
          break;
        case 'tipo':
          aVal = a.tipo || '';
          bVal = b.tipo || '';
          break;
        case 'ley':
          aVal = a.ley || '';
          bVal = b.ley || '';
          break;
        default:
          return 0;
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  }, [referencias, searchTerm, filterTipo, sortBy, sortOrder]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const toggleArticle = async (idx, ref) => {
    const key = `${idx}`;

    // Si ya está expandido, solo colapsar
    if (expandedArticles[key]) {
      setExpandedArticles(prev => ({ ...prev, [key]: false }));
      return;
    }

    // Expandir
    setExpandedArticles(prev => ({ ...prev, [key]: true }));

    // Si ya tenemos los datos, no volver a cargar
    if (articlesData[key]) {
      return;
    }

    // Si no tiene boe_id o artículo, no podemos cargar
    if (!ref.boe_id || !ref.articulo) {
      setArticlesData(prev => ({
        ...prev,
        [key]: {
          error: true,
          mensaje: 'No hay información del BOE para este artículo'
        }
      }));
      return;
    }

    // Cargar artículo desde la API
    try {
      setLoadingArticles(prev => ({ ...prev, [key]: true }));

      const data = await apiService.getArticuloBOE(ref.boe_id, ref.articulo);

      setArticlesData(prev => ({
        ...prev,
        [key]: {
          numero: data.numero,
          titulo: data.titulo,
          texto: data.texto,
          url: data.url,
          error: false
        }
      }));
    } catch (error) {
      console.error('Error cargando artículo del BOE:', error);
      setArticlesData(prev => ({
        ...prev,
        [key]: {
          error: true,
          mensaje: error.response?.data?.detail || 'No se pudo cargar el artículo del BOE'
        }
      }));
    } finally {
      setLoadingArticles(prev => ({ ...prev, [key]: false }));
    }
  };

  if (referencias.length === 0) {
    return (
      <div className="card">
        <div className="card-body text-center text-muted">
          <p>No hay referencias para mostrar</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="flex items-center gap-2">
          <List size={24} />
          Referencias extraídas ({referenciasFiltradas.length})
        </h3>
      </div>

      <div className="card-body">
        {/* Filtros */}
        <div className="filters-container">
          {/* Búsqueda */}
          <div className="search-box">
            <Search size={18} className="search-icon" />
            <input
              type="text"
              placeholder="Buscar en referencias..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
          </div>

          {/* Filtros */}
          <div className="filters-row">
            <div className="filter-group">
              <Filter size={16} />
              <select
                value={filterTipo}
                onChange={(e) => setFilterTipo(e.target.value)}
                className="filter-select"
              >
                <option value="todos">Todos los tipos</option>
                {tipos.map(tipo => (
                  <option key={tipo} value={tipo}>
                    {tipo.charAt(0).toUpperCase() + tipo.slice(1)}
                  </option>
                ))}
              </select>
            </div>

          </div>
        </div>

        {/* Tabla */}
        <div className="table-container">
          <table className="referencias-table">
            <thead>
              <tr>
                <th className="th-sortable" onClick={() => toggleSort('tipo')}>
                  Tipo {sortBy === 'tipo' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th>Referencia</th>
                <th className="th-sortable" onClick={() => toggleSort('ley')}>
                  Ley {sortBy === 'ley' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th className="th-center">Ref. BOE</th>
                <th className="th-center">Ver BOE</th>
              </tr>
            </thead>
            <tbody>
              {referenciasFiltradas.map((ref, idx) => {
                const key = `${idx}`;
                const isExpanded = expandedArticles[key];
                const articleData = articlesData[key];
                const isLoading = loadingArticles[key];
                const hasArticle = ref.articulo && ref.boe_id;

                return (
                  <React.Fragment key={idx}>
                    <tr>
                      <td>
                        <span className="badge badge-secondary">
                          {ref.tipo}
                        </span>
                      </td>
                      <td>
                        <div className="ref-text">
                          <strong>{ref.texto_completo}</strong>

                          {/* Si tiene artículo Y boe_id, mostrar botón de acordeón */}
                          {hasArticle && (
                            <div
                              className="article-toggle"
                              onClick={() => toggleArticle(idx, ref)}
                              title="Ver texto del artículo"
                            >
                              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                              <span>Art. {ref.articulo}</span>
                            </div>
                          )}

                          {/* Si NO tiene boe_id pero SÍ tiene artículo, solo mostrar */}
                          {ref.articulo && !ref.boe_id && (
                            <div className="ref-detail">
                              Art. {ref.articulo}
                            </div>
                          )}

                          {/* Agente que lo encontró */}
                          {ref._metadata?.encontrado_por && (
                            <div className="ref-detail text-muted">
                              {ref._metadata.encontrado_por}
                            </div>
                          )}
                        </div>
                      </td>
                      <td>
                        {ref.ley || '-'}
                      </td>
                      <td className="td-center">
                        {ref.boe_id ? (
                          <code className="boe-id">{ref.boe_id}</code>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="td-center">
                        {ref.boe_url ? (
                          <a
                            href={ref.boe_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="boe-link"
                            title="Ver en BOE"
                          >
                            <ExternalLink size={18} />
                          </a>
                        ) : (
                          '-'
                        )}
                      </td>
                    </tr>

                    {/* Acordeón expandido para mostrar texto del artículo */}
                    {isExpanded && (
                      <tr className="article-row">
                        <td colSpan="5">
                          <div className="article-content">
                            {isLoading && (
                              <div className="article-loading">
                                <Loader size={20} className="spinner" />
                                Cargando artículo del BOE...
                              </div>
                            )}

                            {!isLoading && articleData && !articleData.error && (
                              <>
                                {articleData.titulo && (
                                  <h4 className="article-title">
                                    {articleData.titulo}
                                  </h4>
                                )}
                                <div
                                  className="article-text"
                                  dangerouslySetInnerHTML={{ __html: articleData.texto }}
                                />
                                <div className="article-footer">
                                  <a
                                    href={articleData.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="article-link"
                                  >
                                    <ExternalLink size={14} />
                                    Ver en BOE
                                  </a>
                                </div>
                              </>
                            )}

                            {!isLoading && articleData && articleData.error && (
                              <div className="article-error">
                                <AlertTriangle size={16} className="inline" /> {articleData.mensaje}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>

        {referenciasFiltradas.length === 0 && (
          <div className="text-center text-muted mt-3">
            No se encontraron referencias con los filtros aplicados
          </div>
        )}
      </div>

      {/* SECCIÓN BETA: Referencias Inferidas */}
      {referenciasInferidas.length > 0 && (
        <div className="beta-section">
          <div className="beta-header">
            <div className="beta-title-group">
              <h3 className="beta-title">
                <Brain size={24} />
                Posibles normas inferidas (BETA) ({referenciasInferidas.length})
              </h3>
              <button
                className="beta-toggle"
                onClick={() => setShowBeta(!showBeta)}
              >
                {showBeta ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>

            <div className="beta-warning">
              <div className="beta-warning-icon">
                <AlertTriangle size={24} />
              </div>
              <div>
                <strong>IMPORTANTE:</strong> Estas referencias han sido sugeridas por IA basándose en conceptos legales detectados en el texto.
                <br />
                <strong>No fueron mencionadas explícitamente</strong> en el material de estudio.
                <br />
                <CheckCircle size={14} className="inline" /> <strong>Recomendación:</strong> Verifica estas referencias antes de incluirlas en tu estudio.
              </div>
            </div>
          </div>

          {showBeta && (
            <div className="beta-body">
              {referenciasInferidas.map((ref, idx) => (
                <div key={idx} className="beta-card">
                  <div className="beta-card-header">
                    <span className="beta-badge">BETA-{idx + 1}</span>
                    <h4 className="beta-card-title">{ref.ley || 'Ley desconocida'}</h4>
                  </div>

                  <div className="beta-card-body">
                    <div className="beta-info-row">
                      <span className="beta-label">Concepto detectado:</span>
                      <span className="beta-value">{ref.concepto_detectado}</span>
                    </div>

                    <div className="beta-info-row">
                      <span className="beta-label">Confianza IA:</span>
                      <div className="confianza-cell">
                        <div className="confianza-bar">
                          <div
                            className="confianza-fill"
                            style={{
                              width: `${ref.confianza}%`,
                              backgroundColor: getConfianzaColor(ref.confianza)
                            }}
                          />
                        </div>
                        <span className="confianza-value">{ref.confianza}%</span>
                      </div>
                    </div>

                    <div className="beta-info-row">
                      <span className="beta-label">Artículos sugeridos:</span>
                      <span className="beta-value beta-articles">
                        {ref.articulos.slice(0, 20).join(', ')}
                        {ref.articulos.length > 20 && '...'}
                      </span>
                    </div>

                    {ref.boe_id && (
                      <>
                        <div className="beta-info-row">
                          <span className="beta-label">BOE-ID:</span>
                          <code className="boe-id">{ref.boe_id}</code>
                        </div>

                        <div className="beta-info-row">
                          <span className="beta-label">BOE URL:</span>
                          <a
                            href={`https://www.boe.es/buscar/act.php?id=${ref.boe_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="beta-link"
                          >
                            <ExternalLink size={14} />
                            Ver en BOE
                          </a>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`
        .filters-container {
          margin-bottom: var(--spacing-lg);
        }

        .search-box {
          position: relative;
          margin-bottom: var(--spacing-md);
        }

        .search-icon {
          position: absolute;
          left: var(--spacing-md);
          top: 50%;
          transform: translateY(-50%);
          color: var(--color-text-muted);
          pointer-events: none;
        }

        .search-input {
          width: 100%;
          padding-left: 2.5rem;
        }

        .filters-row {
          display: flex;
          gap: var(--spacing-md);
          flex-wrap: wrap;
        }

        .filter-group {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .filter-select {
          min-width: 150px;
        }

        .table-container {
          overflow-x: auto;
          margin-top: var(--spacing-md);
        }

        .referencias-table {
          width: 100%;
          border-collapse: collapse;
        }

        .referencias-table th {
          background-color: var(--color-primary);
          color: white;
          padding: var(--spacing-md);
          text-align: left;
          font-weight: 600;
          font-size: var(--text-sm);
          white-space: nowrap;
        }

        .th-sortable {
          cursor: pointer;
          user-select: none;
        }

        .th-sortable:hover {
          background-color: var(--color-primary-dark);
        }

        .th-center {
          text-align: center;
        }

        .referencias-table td {
          padding: var(--spacing-md);
          border-bottom: 1px solid var(--color-border);
          font-size: var(--text-sm);
        }

        .td-center {
          text-align: center;
        }

        .referencias-table tbody tr:hover {
          background-color: var(--color-bg-secondary);
        }

        .ref-text {
          max-width: 400px;
        }

        .ref-detail {
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin-top: var(--spacing-xs);
        }

        .article-toggle {
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          margin-top: var(--spacing-xs);
          padding: var(--spacing-xs) var(--spacing-sm);
          background-color: var(--color-primary-bg);
          border-radius: var(--radius);
          cursor: pointer;
          font-size: var(--text-xs);
          font-weight: 600;
          color: var(--color-primary);
          width: fit-content;
          transition: var(--transition);
        }

        .article-toggle:hover {
          background-color: var(--color-primary);
          color: white;
        }

        .article-row {
          background-color: var(--color-bg-secondary);
        }

        .article-content {
          padding: var(--spacing-lg);
          background-color: white;
          border-radius: var(--radius);
          margin: var(--spacing-sm);
        }

        .article-loading {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          color: var(--color-text-muted);
        }

        .article-title {
          margin: 0 0 var(--spacing-md) 0;
          color: var(--color-primary);
          font-size: var(--text-lg);
        }

        .article-text {
          line-height: 1.6;
          padding: var(--spacing-md);
          background-color: var(--color-bg-secondary);
          border-left: 4px solid var(--color-primary);
          border-radius: var(--radius);
        }

        /* Estilos para el HTML del BOE */
        .article-text p {
          margin: 0.5em 0;
        }

        .article-text .articulo {
          font-weight: bold;
          margin-bottom: 0.75em;
        }

        .article-text .parrafo {
          margin: 0.5em 0;
          text-align: justify;
        }

        .article-footer {
          margin-top: var(--spacing-md);
          padding-top: var(--spacing-md);
          border-top: 1px solid var(--color-border);
        }

        .article-link {
          display: inline-flex;
          align-items: center;
          gap: var(--spacing-xs);
          color: var(--color-primary);
          text-decoration: none;
          font-size: var(--text-sm);
          font-weight: 600;
        }

        .article-link:hover {
          text-decoration: underline;
        }

        .article-error {
          padding: var(--spacing-md);
          background-color: #fff3cd;
          border: 1px solid #ffc107;
          border-radius: var(--radius);
          color: #856404;
        }

        .confianza-cell {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .confianza-bar {
          flex: 1;
          height: 0.5rem;
          background-color: var(--color-gray-200);
          border-radius: var(--radius-full);
          overflow: hidden;
          min-width: 60px;
        }

        .confianza-fill {
          height: 100%;
          transition: width 0.3s ease;
        }

        .confianza-value {
          font-weight: 600;
          min-width: 40px;
          text-align: right;
        }

        .boe-id {
          font-size: var(--text-xs);
          padding: var(--spacing-xs) var(--spacing-sm);
          background-color: var(--color-bg-secondary);
          border-radius: var(--radius);
          font-family: monospace;
        }

        .boe-link {
          color: var(--color-primary);
          display: inline-flex;
          transition: var(--transition);
        }

        .boe-link:hover {
          color: var(--color-primary-dark);
          transform: scale(1.1);
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        .spinner {
          animation: spin 1s linear infinite;
        }

        /* Estilos BETA Section */
        .beta-section {
          margin-top: var(--spacing-xl);
          border-top: 3px solid #ff8c00;
        }

        .beta-header {
          background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
          padding: var(--spacing-lg);
          border-radius: var(--radius) var(--radius) 0 0;
        }

        .beta-title-group {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--spacing-md);
        }

        .beta-title {
          margin: 0;
          color: #ff8c00;
          font-size: var(--text-xl);
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .beta-toggle {
          padding: var(--spacing-sm) var(--spacing-md);
          background-color: #ff8c00;
          color: white;
          border: none;
          border-radius: var(--radius);
          cursor: pointer;
          font-weight: 600;
          transition: var(--transition);
        }

        .beta-toggle:hover {
          background-color: #e67e00;
        }

        .beta-warning {
          display: flex;
          gap: var(--spacing-md);
          padding: var(--spacing-md);
          background-color: rgba(255, 140, 0, 0.1);
          border: 2px solid #ff8c00;
          border-radius: var(--radius);
          font-size: var(--text-sm);
          line-height: 1.6;
        }

        .beta-warning-icon {
          font-size: var(--text-2xl);
        }

        .beta-body {
          padding: var(--spacing-lg);
          background-color: var(--color-bg-secondary);
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: var(--spacing-lg);
        }

        .beta-card {
          background-color: white;
          border: 2px solid #ff8c00;
          border-radius: var(--radius);
          overflow: hidden;
          transition: var(--transition);
        }

        .beta-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(255, 140, 0, 0.2);
        }

        .beta-card-header {
          padding: var(--spacing-md);
          background: linear-gradient(135deg, #ff8c00 0%, #ff9d1f 100%);
          color: white;
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        }

        .beta-badge {
          padding: var(--spacing-xs) var(--spacing-sm);
          background-color: rgba(255, 255, 255, 0.3);
          border-radius: var(--radius);
          font-weight: 700;
          font-size: var(--text-xs);
        }

        .beta-card-title {
          margin: 0;
          font-size: var(--text-base);
          font-weight: 600;
        }

        .beta-card-body {
          padding: var(--spacing-md);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        }

        .beta-info-row {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
        }

        .beta-label {
          font-weight: 600;
          color: var(--color-text-muted);
          font-size: var(--text-sm);
        }

        .beta-value {
          font-size: var(--text-sm);
        }

        .beta-articles {
          font-family: monospace;
          font-size: var(--text-xs);
          padding: var(--spacing-sm);
          background-color: var(--color-bg-secondary);
          border-radius: var(--radius);
          word-break: break-word;
        }

        .beta-link {
          display: inline-flex;
          align-items: center;
          gap: var(--spacing-xs);
          color: #ff8c00;
          text-decoration: none;
          font-weight: 600;
          font-size: var(--text-sm);
          transition: var(--transition);
        }

        .beta-link:hover {
          color: #e67e00;
          text-decoration: underline;
        }

        @media (max-width: 768px) {
          .beta-body {
            grid-template-columns: 1fr;
          }

          .beta-title-group {
            flex-direction: column;
            align-items: flex-start;
            gap: var(--spacing-sm);
          }
        }
      `}</style>
    </div>
  );
}

function getConfianzaColor(confianza) {
  if (confianza >= 90) return '#198754';
  if (confianza >= 70) return '#20c997';
  if (confianza >= 50) return '#ffc107';
  return '#dc3545';
}
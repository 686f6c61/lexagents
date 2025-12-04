/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Panel de Descarga de Archivos Permite descargar los archivos exportados
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState } from 'react';
import { Download, FileText, File, FileCode, FilePlus } from 'lucide-react';
import apiService from '../services/api';

export default function DownloadPanel({ jobId, archivosExportados }) {
  const [downloading, setDownloading] = useState({});

  const handleDownload = async (formato) => {
    setDownloading(prev => ({ ...prev, [formato]: true }));

    try {
      const blob = await apiService.downloadFile(jobId, formato);

      // Crear URL temporal para el blob
      const url = window.URL.createObjectURL(blob);

      // Crear link temporal y hacer click
      const a = document.createElement('a');
      a.href = url;
      a.download = `referencias_${jobId.substring(0, 8)}.${formato}`;
      document.body.appendChild(a);
      a.click();

      // Limpiar
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error(`Error descargando ${formato}:`, err);
      alert(`Error al descargar archivo ${formato}`);
    } finally {
      setDownloading(prev => ({ ...prev, [formato]: false }));
    }
  };

  const formatos = [
    {
      key: 'md',
      name: 'Markdown',
      extension: '.md',
      icon: FileCode,
      description: 'Formato Markdown con enlaces clickeables',
      color: 'var(--color-info)'
    },
    {
      key: 'txt',
      name: 'Texto Plano',
      extension: '.txt',
      icon: FileText,
      description: 'Texto simple para impresión',
      color: 'var(--color-text-muted)'
    },
    {
      key: 'docx',
      name: 'Microsoft Word',
      extension: '.docx',
      icon: File,
      description: 'Documento profesional con tablas',
      color: 'var(--color-primary)'
    },
    {
      key: 'pdf',
      name: 'PDF',
      extension: '.pdf',
      icon: FilePlus,
      description: 'Documento PDF portátil',
      color: 'var(--color-danger)'
    }
  ];

  if (!jobId || !archivosExportados) {
    return null;
  }

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="flex items-center gap-2">
          <Download size={24} />
          Descargar resultados
        </h3>
      </div>

      <div className="card-body">
        <div className="download-row">
          {formatos.map(formato => {
            const Icon = formato.icon;
            const isAvailable = archivosExportados[
              formato.key === 'md' ? 'markdown' :
              formato.key === 'txt' ? 'texto' :
              formato.key === 'pdf' ? 'pdf' :
              'word'
            ];

            return (
              <div key={formato.key} className="download-item">
                <div className="download-icon-small" style={{ color: formato.color }}>
                  <Icon size={24} />
                </div>

                <div className="download-info-compact">
                  <h4 className="download-title-small">{formato.name}</h4>
                  <p className="download-extension-small">{formato.extension}</p>
                </div>

                <button
                  onClick={() => handleDownload(formato.key)}
                  disabled={!isAvailable || downloading[formato.key]}
                  className="btn btn-primary btn-sm"
                >
                  {downloading[formato.key] ? (
                    <>
                      <div className="spinner" />
                    </>
                  ) : (
                    <>
                      <Download size={16} />
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="download-all-section">
          <button
            onClick={async () => {
              for (const formato of formatos) {
                await handleDownload(formato.key);
              }
            }}
            disabled={Object.values(downloading).some(Boolean)}
            className="btn btn-outline"
          >
            <Download size={18} />
            Descargar todos
          </button>
        </div>
      </div>

      <style>{`
        .download-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--spacing-md);
          margin-bottom: var(--spacing-lg);
        }

        .download-item {
          border: 2px solid var(--color-border);
          border-radius: var(--radius);
          padding: var(--spacing-md);
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          transition: var(--transition);
        }

        .download-item:hover {
          border-color: var(--color-primary);
          box-shadow: var(--shadow-sm);
        }

        .download-icon-small {
          flex-shrink: 0;
        }

        .download-info-compact {
          flex: 1;
        }

        .download-title-small {
          font-size: var(--text-base);
          font-weight: 600;
          margin: 0 0 2px 0;
        }

        .download-extension-small {
          font-family: var(--font-mono);
          font-size: var(--text-xs);
          color: var(--color-text-muted);
          margin: 0;
        }

        .download-all-section {
          border-top: 1px solid var(--color-border);
          padding-top: var(--spacing-lg);
          display: flex;
          justify-content: center;
        }

        .download-all-section .btn {
          min-width: 180px;
        }

        @media (max-width: 1024px) {
          .download-row {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 640px) {
          .download-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}

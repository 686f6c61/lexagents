/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Componente de Upload de Archivos Características:
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import { useState, useRef } from 'react';
import { Upload, File, X, Check } from 'lucide-react';
import apiService from '../services/api';

export default function FileUpload({ onUploadSuccess }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    validateAndSetFile(droppedFile);
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    validateAndSetFile(selectedFile);
  };

  const validateAndSetFile = (selectedFile) => {
    setError(null);
    setUploaded(false);

    // Validar tipo - Formatos permitidos
    const allowedExtensions = ['.json', '.pdf', '.docx', '.txt', '.md'];
    const fileName = selectedFile.name.toLowerCase();
    const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));

    if (!isValid) {
      setError('Formato no soportado. Use: JSON, PDF, Word (.docx), TXT o Markdown (.md)');
      return;
    }

    // Validar tamaño (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setError('El archivo es demasiado grande (máximo 10MB)');
      return;
    }

    setFile(selectedFile);
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const result = await apiService.uploadFile(file);
      setUploaded(true);
      setUploading(false);

      // Notificar al componente padre
      if (onUploadSuccess) {
        onUploadSuccess({
          archivoId: result.archivo_id,
          nombreOriginal: result.nombre_original,
          tamaño: result.tamaño_bytes
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al subir el archivo');
      setUploading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setUploaded(false);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="flex items-center gap-2">
          <Upload size={24} />
          Subir tema
        </h3>
        <p className="text-sm text-muted mt-1">
          Formatos soportados: JSON, PDF, Word, TXT, Markdown
        </p>
      </div>

      <div className="card-body">
        {/* Drop zone */}
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !file && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.pdf,.docx,.txt,.md"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />

          {!file ? (
            <div className="upload-zone-content">
              <Upload size={48} className="text-muted" />
              <p className="font-bold">
                Arrastra tu documento aquí
              </p>
              <p className="text-muted text-sm">
                o haz clic para seleccionar
              </p>
              <p className="text-muted text-xs mt-2">
                JSON, PDF, Word (.docx), TXT o Markdown (.md) • Máximo 10MB
              </p>
            </div>
          ) : (
            <div className="upload-file-preview">
              <div className="flex items-center gap-2">
                <File size={24} className="text-primary" />
                <div className="flex-1">
                  <p className="font-bold">{file.name}</p>
                  <p className="text-sm text-muted">{formatBytes(file.size)}</p>
                </div>
                {uploaded && (
                  <Check size={24} className="text-success" />
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleClear();
                  }}
                  className="btn btn-sm btn-secondary"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert-error mt-2">
            {error}
          </div>
        )}

        {/* Botón de upload */}
        {file && !uploaded && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn btn-primary btn-lg w-full mt-3"
          >
            {uploading ? (
              <>
                <div className="spinner" />
                Subiendo...
              </>
            ) : (
              <>
                <Upload size={20} />
                Subir archivo
              </>
            )}
          </button>
        )}

        {uploaded && (
          <div className="alert alert-success mt-3">
            <Check size={20} className="inline" /> Archivo subido exitosamente
          </div>
        )}
      </div>

      <style>{`
        .upload-zone {
          border: 2px dashed var(--color-border);
          border-radius: var(--radius-lg);
          padding: var(--spacing-2xl);
          text-align: center;
          cursor: pointer;
          transition: var(--transition);
        }

        .upload-zone:hover {
          border-color: var(--color-primary);
          background-color: var(--color-primary-bg);
        }

        .upload-zone.dragging {
          border-color: var(--color-primary);
          background-color: var(--color-primary-bg);
        }

        .upload-zone.has-file {
          cursor: default;
          border-style: solid;
        }

        .upload-zone.has-file:hover {
          background-color: white;
        }

        .upload-zone-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .upload-file-preview {
          padding: var(--spacing-md);
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

        .alert-success {
          background-color: #d1f4e0;
          border-color: #badbcc;
          color: #0f5132;
        }
      `}</style>
    </div>
  );
}

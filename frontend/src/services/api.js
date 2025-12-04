/**
 * LexAgents - Sistema Multi-Agente de Extracción Legal
 * https://github.com/686f6c61/lexagents
 * 
 * Servicio de API Cliente para comunicarse con el backend FastAPI
 * 
 * @author 686f6c61
 * @version 0.2.0
 * @license MIT
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Crear instancia de axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor para manejo de errores
api.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * API Service
 */
const apiService = {
  /**
   * Health check
   */
  async healthCheck() {
    const response = await api.get('/api/v1/health');
    return response.data;
  },

  /**
   * Obtiene información completa del sistema
   */
  async getSystemInfo() {
    const response = await api.get('/api/v1/system/info');
    return response.data;
  },

  /**
   * Sube un archivo JSON
   * @param {File} file - Archivo a subir
   * @returns {Promise<Object>} - Respuesta con archivo_id
   */
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/api/v1/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    return response.data;
  },

  /**
   * Procesa un tema (asíncrono)
   * @param {Object} config - Configuración del procesamiento
   * @returns {Promise<Object>} - Respuesta con job_id
   */
  async processTema(config) {
    const response = await api.post('/api/v1/process', config);
    return response.data;
  },

  /**
   * Procesa un tema (síncrono)
   * @param {Object} config - Configuración del procesamiento
   * @returns {Promise<Object>} - Resultado completo
   */
  async processTemaSync(config) {
    const response = await api.post('/api/v1/process/sync', config);
    return response.data;
  },

  /**
   * Obtiene el estado de un job
   * @param {string} jobId - ID del job
   * @returns {Promise<Object>} - Estado del job
   */
  async getJobStatus(jobId) {
    const response = await api.get(`/api/v1/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Lista todos los jobs
   * @returns {Promise<Object>} - Lista de jobs
   */
  async listJobs() {
    const response = await api.get('/api/v1/jobs');
    return response.data;
  },

  /**
   * Cancela un job
   * @param {string} jobId - ID del job
   * @returns {Promise<Object>} - Confirmación
   */
  async cancelJob(jobId) {
    const response = await api.delete(`/api/v1/jobs/${jobId}`);
    return response.data;
  },

  /**
   * Descarga un archivo exportado
   * @param {string} jobId - ID del job
   * @param {string} formato - Formato (md, txt, docx)
   * @returns {Promise<Blob>} - Archivo descargado
   */
  async downloadFile(jobId, formato) {
    const response = await api.get(`/api/v1/download/${jobId}/${formato}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  /**
   * Obtiene estadísticas del sistema
   * @returns {Promise<Object>} - Estadísticas
   */
  async getStats() {
    const response = await api.get('/api/v1/stats');
    return response.data;
  },

  /**
   * Limpia jobs antiguos
   * @param {number} maxAgeHours - Edad máxima en horas
   * @returns {Promise<Object>} - Confirmación
   */
  async cleanupJobs(maxAgeHours = 24) {
    const response = await api.post(`/api/v1/admin/cleanup?max_age_hours=${maxAgeHours}`);
    return response.data;
  },

  /**
   * Polling de job hasta que complete
   * @param {string} jobId - ID del job
   * @param {Function} onProgress - Callback de progreso
   * @param {number} interval - Intervalo de polling (ms)
   * @returns {Promise<Object>} - Resultado final
   */
  async pollJob(jobId, onProgress = null, interval = 2000) {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getJobStatus(jobId);

          // Callback de progreso
          if (onProgress) {
            onProgress(status);
          }

          // Verificar si terminó
          if (status.status === 'completed') {
            resolve(status);
          } else if (status.status === 'failed') {
            reject(new Error(status.error || 'Procesamiento fallido'));
          } else if (status.status === 'cancelled') {
            reject(new Error('Procesamiento cancelado'));
          } else {
            // Continuar polling
            setTimeout(poll, interval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  },

  /**
   * Obtiene el texto completo de un artículo del BOE
   * @param {string} boeId - ID del BOE (ej: "BOE-A-1985-12666")
   * @param {string} numeroArticulo - Número del artículo (ej: "456")
   * @returns {Promise<Object>} - Datos del artículo
   */
  async getArticuloBOE(boeId, numeroArticulo) {
    const response = await api.get(`/api/v1/boe/articulo/${boeId}/${numeroArticulo}`);
    return response.data;
  }
};

export default apiService;

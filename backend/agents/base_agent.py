# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Clase base para todos los agentes de IA del sistema

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from google import genai

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Clase base abstracta para todos los agentes del sistema

    Proporciona funcionalidad común:
    - Configuración de Gemini
    - Logging
    - Manejo de errores
    - Métricas de uso
    """

    def __init__(
        self,
        nombre: str,
        modelo: str = "gemini-2.5-pro",
        temperatura: float = 0.1,
        api_key: Optional[str] = None
    ):
        """
        Inicializa el agente base

        Args:
            nombre: Nombre identificador del agente
            modelo: Modelo de Gemini a usar
            temperatura: Temperatura para generación (0.0-1.0)
            api_key: API key de Gemini (si no se proporciona, usa .env)
        """
        self.nombre = nombre
        self.modelo = modelo
        self.temperatura = temperatura

        # Configurar cliente de Gemini
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY no encontrada")

        self.client = genai.Client(api_key=self.api_key)

        # Métricas
        self.metricas = {
            'total_llamadas': 0,
            'total_tokens_prompt': 0,
            'total_tokens_respuesta': 0,
            'total_errores': 0,
            'tiempo_total_ms': 0
        }

        logger.info(f"✅ Agente '{self.nombre}' inicializado (modelo: {self.modelo}, temp: {self.temperatura})")

    @abstractmethod
    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método abstracto que debe implementar cada agente

        Args:
            entrada: Dict con los datos de entrada del agente

        Returns:
            Dict con los resultados del procesamiento
        """
        pass

    def generar_contenido(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Genera contenido usando Gemini

        Args:
            prompt: Prompt para el modelo
            system_instruction: Instrucción de sistema (opcional)

        Returns:
            Texto generado por el modelo
        """
        inicio = datetime.now()

        try:
            self.metricas['total_llamadas'] += 1

            # Configurar la llamada
            config = {
                'temperature': self.temperatura,
                'max_output_tokens': 65000
            }

            # Agregar system instruction si se proporciona
            if system_instruction:
                # En la nueva API, el system instruction se pasa como parte del prompt
                prompt_completo = f"{system_instruction}\n\n{prompt}"
            else:
                prompt_completo = prompt

            # Llamar a Gemini
            response = self.client.models.generate_content(
                model=self.modelo,
                contents=prompt_completo,
                config=config
            )

            # Extraer texto
            texto_respuesta = response.text

            # Actualizar métricas
            tiempo_ms = (datetime.now() - inicio).total_seconds() * 1000
            self.metricas['tiempo_total_ms'] += tiempo_ms

            # Estimación de tokens (aproximada)
            # 1 token ≈ 4 caracteres en español
            tokens_prompt = len(prompt_completo) // 4
            tokens_respuesta = len(texto_respuesta) // 4

            self.metricas['total_tokens_prompt'] += tokens_prompt
            self.metricas['total_tokens_respuesta'] += tokens_respuesta

            logger.debug(
                f"[{self.nombre}] Llamada exitosa: "
                f"{tokens_prompt} tokens prompt, "
                f"{tokens_respuesta} tokens respuesta, "
                f"{tiempo_ms:.0f}ms"
            )

            return texto_respuesta

        except Exception as e:
            self.metricas['total_errores'] += 1
            logger.error(f"[{self.nombre}] Error en generación: {e}")
            raise

    def obtener_metricas(self) -> Dict[str, Any]:
        """
        Obtiene las métricas del agente

        Returns:
            Dict con métricas de uso
        """
        return {
            'nombre': self.nombre,
            'modelo': self.modelo,
            'temperatura': self.temperatura,
            **self.metricas,
            'tiempo_promedio_ms': (
                self.metricas['tiempo_total_ms'] / self.metricas['total_llamadas']
                if self.metricas['total_llamadas'] > 0 else 0
            )
        }

    def resetear_metricas(self):
        """Resetea las métricas del agente"""
        self.metricas = {
            'total_llamadas': 0,
            'total_tokens_prompt': 0,
            'total_tokens_respuesta': 0,
            'total_errores': 0,
            'tiempo_total_ms': 0
        }
        logger.info(f"[{self.nombre}] Métricas reseteadas")

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"nombre='{self.nombre}' "
            f"modelo='{self.modelo}' "
            f"temp={self.temperatura}>"
        )

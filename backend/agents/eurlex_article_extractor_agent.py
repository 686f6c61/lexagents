# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 4: Extractor de Artículos EUR-Lex
Extrae el texto completo de artículos específicos de legislación europea:
- Scraping HTML de EUR-Lex
- Soporte multi-idioma (ES, EN, FR)
- Limpieza y formateo con IA

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from pathlib import Path
from functools import lru_cache
import re
import sys

# Permitir imports relativos cuando se ejecuta como script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_agent import BaseAgent
else:
    from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EurlexArticleExtractorAgent(BaseAgent):
    """
    Agente extractor de artículos de EUR-Lex

    Características:
    - Extracción de artículos por CELEX + número de artículo
    - Scraping HTML optimizado
    - Soporte multi-idioma (ES, EN, FR)
    - Limpieza de texto con IA
    - Caché LRU para artículos frecuentes
    """

    def __init__(
        self,
        api_key: str = None,
        cache_size: int = 200
    ):
        """
        Inicializa el Agente Extractor EUR-Lex

        Args:
            api_key: API key de Gemini (opcional)
            cache_size: Tamaño del caché LRU
        """
        super().__init__(
            nombre="Agente4-EurlexExtractor",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.1,  # Muy conservador para extracción
            api_key=api_key
        )

        self.cache_size = cache_size
        self.idiomas_soportados = ['ES', 'EN', 'FR', 'DE', 'IT']

        logger.info(f"✅ Agente EUR-Lex Extractor inicializado (caché: {cache_size})")

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae artículos de EUR-Lex

        Args:
            entrada: Dict con:
                - 'celex': str - Identificador CELEX
                - 'articulo': str o int - Número de artículo
                - 'idioma': str - Código idioma (ES, EN, FR...) [opcional]
                - 'limpiar_con_ia': bool - Usar IA para limpiar [opcional]

        Returns:
            Dict con:
                - 'articulo': str
                - 'celex': str
                - 'texto_completo': str
                - 'titulo_articulo': str
                - 'url_fuente': str
                - 'idioma': str
                - 'apartados': List[str]
                - 'exito': bool
                - 'agente': str
        """
        celex = entrada.get('celex', '').strip()
        articulo = str(entrada.get('articulo', '')).strip()
        idioma = entrada.get('idioma', 'ES').upper()
        limpiar_con_ia = entrada.get('limpiar_con_ia', False)

        logger.info(f"[{self.nombre}] Extrayendo Artículo {articulo} de CELEX {celex} ({idioma})")

        if not celex or not articulo:
            logger.error("CELEX o artículo vacío")
            return self._respuesta_error("CELEX o artículo requerido")

        # Validar idioma
        if idioma not in self.idiomas_soportados:
            logger.warning(f"Idioma {idioma} no soportado, usando ES")
            idioma = 'ES'

        # Extraer artículo (con caché)
        resultado = self._extraer_articulo_cached(celex, articulo, idioma)

        if not resultado['exito']:
            return resultado

        # Opcional: limpiar con IA
        if limpiar_con_ia and resultado.get('texto_completo'):
            texto_limpio = self._limpiar_texto_con_ia(resultado['texto_completo'], articulo)
            if texto_limpio:
                resultado['texto_completo'] = texto_limpio
                resultado['_limpiado_ia'] = True

        resultado['agente'] = self.nombre
        logger.info(f"[{self.nombre}] ✅ Artículo {articulo} extraído ({len(resultado.get('texto_completo', ''))} chars)")

        return resultado

    @lru_cache(maxsize=200)
    def _extraer_articulo_cached(
        self,
        celex: str,
        articulo: str,
        idioma: str
    ) -> Dict[str, Any]:
        """
        Extrae artículo con caché LRU

        Args:
            celex: CELEX
            articulo: Número de artículo
            idioma: Código idioma

        Returns:
            Dict con información del artículo
        """
        logger.debug(f"Extrayendo artículo (caché habilitado): {celex} art. {articulo} ({idioma})")
        return self._extraer_articulo_eurlex(celex, articulo, idioma)

    def _extraer_articulo_eurlex(
        self,
        celex: str,
        articulo: str,
        idioma: str
    ) -> Dict[str, Any]:
        """
        Extrae artículo de EUR-Lex mediante scraping HTML

        Args:
            celex: CELEX
            articulo: Número de artículo
            idioma: Código idioma

        Returns:
            Dict con datos del artículo
        """
        # Construir URL
        url = f"https://eur-lex.europa.eu/legal-content/{idioma}/TXT/HTML/?uri=CELEX:{celex}"

        try:
            # Petición HTTP
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            # Parsear HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Normalizar número de artículo (puede venir como "17" o "art_17")
            art_id = articulo.replace('art_', '').replace('Art_', '').strip()
            art_id_full = f"art_{art_id}"

            # Buscar div del artículo
            div_articulo = soup.find('div', id=art_id_full)

            if not div_articulo:
                logger.warning(f"Artículo {art_id} no encontrado en {url}")
                return self._respuesta_error(f"Artículo {art_id} no encontrado", celex, articulo, url)

            # Extraer componentes del artículo
            texto_completo = div_articulo.get_text(separator='\n', strip=True)

            # Extraer título del artículo (si existe)
            titulo_div = div_articulo.find('div', class_='eli-title')
            titulo_articulo = titulo_div.get_text(strip=True) if titulo_div else ''

            # Extraer apartados (divs internos sin clase específica)
            apartados = []
            for div in div_articulo.find_all('div', recursive=False):
                if div.get('id') and not div.get('class'):
                    texto_apartado = div.get_text(separator=' ', strip=True)
                    if texto_apartado:
                        apartados.append(texto_apartado)

            logger.debug(f"✅ Artículo extraído: {len(texto_completo)} chars, {len(apartados)} apartados")

            return {
                'exito': True,
                'celex': celex,
                'articulo': art_id,
                'texto_completo': texto_completo,
                'titulo_articulo': titulo_articulo,
                'apartados': apartados,
                'idioma': idioma,
                'url_fuente': url,
                'longitud_caracteres': len(texto_completo),
                'num_apartados': len(apartados)
            }

        except requests.RequestException as e:
            logger.error(f"Error HTTP al extraer artículo: {e}")
            return self._respuesta_error(f"Error HTTP: {e}", celex, articulo, url)

        except Exception as e:
            logger.error(f"Error inesperado al extraer artículo: {e}")
            import traceback
            traceback.print_exc()
            return self._respuesta_error(f"Error: {e}", celex, articulo, url)

    def _limpiar_texto_con_ia(
        self,
        texto: str,
        num_articulo: str
    ) -> Optional[str]:
        """
        Limpia y formatea texto de artículo usando IA

        Args:
            texto: Texto crudo extraído
            num_articulo: Número de artículo

        Returns:
            Texto limpio o None si falla
        """
        # Limitar longitud del texto para IA
        texto_para_ia = texto[:8000] if len(texto) > 8000 else texto

        prompt = f"""Limpia y formatea el siguiente texto de un artículo de legislación europea.

ARTÍCULO: {num_articulo}

TEXTO CRUDO:
{texto_para_ia}

INSTRUCCIONES:
1. Mantén el contenido exacto, NO cambies el significado
2. Mejora el formato y legibilidad
3. Separa claramente apartados y subapartados
4. Elimina saltos de línea innecesarios
5. Mantén la numeración de apartados (1., 2., a), b), etc.)
6. Asegúrate de que el título del artículo esté claro

Devuelve SOLO el texto limpio y formateado, sin explicaciones."""

        try:
            respuesta = self.generar_contenido(
                prompt,
                system_instruction="Eres un experto en formateo de textos legales europeos. Limpia y formatea preservando exactitud."
            )

            texto_limpio = respuesta.strip()

            # Validar que el texto limpio tenga sentido
            if len(texto_limpio) > 100 and 'Artículo' in texto_limpio:
                logger.debug(f"✅ Texto limpiado con IA: {len(texto_limpio)} chars")
                return texto_limpio
            else:
                logger.warning(f"IA devolvió texto inválido: {texto_limpio[:200]}")
                return None

        except Exception as e:
            logger.error(f"Error limpiando texto con IA: {e}")
            return None

    def _respuesta_error(
        self,
        mensaje: str,
        celex: str = '',
        articulo: str = '',
        url: str = ''
    ) -> Dict[str, Any]:
        """
        Genera respuesta de error estándar

        Args:
            mensaje: Mensaje de error
            celex: CELEX (opcional)
            articulo: Artículo (opcional)
            url: URL (opcional)

        Returns:
            Dict con error
        """
        return {
            'exito': False,
            'error': mensaje,
            'celex': celex,
            'articulo': articulo,
            'url_fuente': url,
            'texto_completo': '',
            'titulo_articulo': '',
            'apartados': []
        }

    def extraer_multiples_articulos(
        self,
        celex: str,
        articulos: List[str],
        idioma: str = 'ES'
    ) -> Dict[str, Any]:
        """
        Extrae múltiples artículos del mismo documento

        Args:
            celex: CELEX
            articulos: Lista de números de artículo
            idioma: Código idioma

        Returns:
            Dict con lista de artículos extraídos
        """
        logger.info(f"[{self.nombre}] Extrayendo {len(articulos)} artículos de {celex}")

        resultados = []
        exitosos = 0

        for num_art in articulos:
            resultado = self.procesar({
                'celex': celex,
                'articulo': num_art,
                'idioma': idioma
            })

            resultados.append(resultado)

            if resultado.get('exito'):
                exitosos += 1

        logger.info(f"[{self.nombre}] ✅ {exitosos}/{len(articulos)} artículos extraídos")

        return {
            'articulos': resultados,
            'total': len(articulos),
            'exitosos': exitosos,
            'fallidos': len(articulos) - exitosos,
            'celex': celex,
            'idioma': idioma,
            'agente': self.nombre
        }

    def limpiar_cache(self):
        """Limpia el caché de artículos"""
        self._extraer_articulo_cached.cache_clear()
        logger.info(f"[{self.nombre}] Caché limpiado")

    def obtener_info_cache(self) -> Dict[str, Any]:
        """
        Obtiene información del caché

        Returns:
            Dict con estadísticas del caché
        """
        cache_info = self._extraer_articulo_cached.cache_info()

        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize,
            'hit_rate': cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
        }


# Función helper
def extraer_articulo_eurlex(
    celex: str,
    articulo: str,
    idioma: str = 'ES',
    limpiar: bool = False
) -> Dict[str, Any]:
    """
    Función helper para extraer artículo EUR-Lex

    Args:
        celex: CELEX
        articulo: Número de artículo
        idioma: Código idioma
        limpiar: Limpiar con IA

    Returns:
        Dict con datos del artículo
    """
    agente = EurlexArticleExtractorAgent()

    return agente.procesar({
        'celex': celex,
        'articulo': articulo,
        'idioma': idioma,
        'limpiar_con_ia': limpiar
    })


# Ejemplo de uso
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    # Cargar .env
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 80)
    print("🧪 TEST DEL AGENTE EUR-LEX ARTICLE EXTRACTOR")
    print("=" * 80)

    # Test 1: Artículo 17 del RGPD (Derecho al olvido)
    print("\n1. Extrayendo Artículo 17 del RGPD (Derecho al olvido)")
    print("-" * 80)

    agente = EurlexArticleExtractorAgent()

    resultado = agente.procesar({
        'celex': '32016R0679',
        'articulo': '17',
        'idioma': 'ES'
    })

    if resultado['exito']:
        print(f"\n✅ Artículo extraído exitosamente")
        print(f"   Título: {resultado['titulo_articulo']}")
        print(f"   Longitud: {resultado['longitud_caracteres']} caracteres")
        print(f"   Apartados: {resultado['num_apartados']}")
        print(f"   URL: {resultado['url_fuente']}")
        print(f"\n   Primeros 500 caracteres:")
        print(f"   {'-' * 76}")
        print(f"   {resultado['texto_completo'][:500]}...")
    else:
        print(f"\n❌ Error: {resultado['error']}")

    # Test 2: Múltiples artículos
    print("\n\n2. Extrayendo múltiples artículos (15, 16, 17)")
    print("-" * 80)

    resultado_multiple = agente.extraer_multiples_articulos(
        celex='32016R0679',
        articulos=['15', '16', '17'],
        idioma='ES'
    )

    print(f"\n✅ Extraídos: {resultado_multiple['exitosos']}/{resultado_multiple['total']}")

    for art in resultado_multiple['articulos']:
        if art['exito']:
            print(f"   ✅ Artículo {art['articulo']}: {art['titulo_articulo']}")
        else:
            print(f"   ❌ Artículo {art['articulo']}: {art['error']}")

    # Test 3: Info del caché
    print("\n\n3. Información del caché")
    print("-" * 80)

    info_cache = agente.obtener_info_cache()
    print(f"\n   Hits: {info_cache['hits']}")
    print(f"   Misses: {info_cache['misses']}")
    print(f"   Tamaño actual: {info_cache['currsize']}/{info_cache['maxsize']}")
    print(f"   Hit rate: {info_cache['hit_rate']:.2%}")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETADO")
    print("=" * 80)

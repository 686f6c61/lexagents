# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo: BOE Downloader
Descarga el contenido oficial HTML consolidado de las leyes desde el BOE.
Parsea los artículos y los almacena en caché para verificación posterior.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import requests
import logging
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
import json
import hashlib
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BOEDownloader:
    """Descargador de contenido consolidado del BOE"""

    def __init__(self, cache_dir: str = "../../data/cache/boe_html"):
        """
        Inicializa el downloader

        Args:
            cache_dir: Directorio para caché de leyes descargadas
        """
        self.base_url = "https://www.boe.es/buscar/act.php"

        # Caché local
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Configuración
        self.cache_days = 30  # Leyes consolidadas no cambian frecuentemente
        self.timeout = 30

        # Rate limiting
        self.min_request_interval = 1.0  # segundos entre peticiones

    def descargar_ley(self, boe_id: str, force_refresh: bool = False) -> Optional[Dict]:
        """
        Descarga una ley consolidada del BOE

        Args:
            boe_id: Identificador BOE (ej: BOE-A-2015-10565)
            force_refresh: Forzar descarga incluso si existe en caché

        Returns:
            Dict con:
                - boe_id: ID de la ley
                - html_content: HTML completo
                - articulos: Dict de artículos parseados
                - metadata: Metadatos extraídos
                - fecha_descarga: Fecha de descarga
                - cached: Si vino de caché
        """
        # Verificar caché
        if not force_refresh:
            cached = self._get_from_cache(boe_id)
            if cached:
                logger.info(f"Ley {boe_id} obtenida de caché")
                return cached

        # Descargar desde BOE
        logger.info(f"Descargando ley {boe_id} desde BOE...")

        url = f"{self.base_url}?id={boe_id}"

        try:
            response = requests.get(url, timeout=self.timeout)

            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code} al descargar {boe_id}")
                return None

            html_content = response.text

            # Parsear contenido
            articulos, metadata = self._parsear_html(html_content, boe_id)

            # Construir resultado
            result = {
                'boe_id': boe_id,
                'html_content': html_content,
                'articulos': articulos,
                'metadata': metadata,
                'fecha_descarga': datetime.now().isoformat(),
                'cached': False,
                'url': url
            }

            # Guardar en caché
            self._save_to_cache(boe_id, result)

            logger.info(f"Ley {boe_id} descargada: {len(articulos)} artículos encontrados")

            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red descargando {boe_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado descargando {boe_id}: {e}")
            return None

    def _parsear_html(self, html_content: str, boe_id: str) -> tuple:
        """
        Parsea el HTML consolidado para extraer artículos

        Args:
            html_content: HTML completo de la ley
            boe_id: ID para referencia

        Returns:
            Tupla (articulos_dict, metadata_dict)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extraer metadata
            metadata = self._extraer_metadata(soup, boe_id)

            # Extraer artículos
            articulos = self._extraer_articulos(soup)

            return articulos, metadata

        except Exception as e:
            logger.error(f"Error parseando HTML de {boe_id}: {e}")
            return {}, {}

    def _extraer_metadata(self, soup: BeautifulSoup, boe_id: str) -> Dict:
        """
        Extrae metadatos de la ley del HTML

        Args:
            soup: BeautifulSoup object
            boe_id: ID del BOE

        Returns:
            Dict con metadatos
        """
        metadata = {
            'boe_id': boe_id,
            'titulo': None,
            'fecha_publicacion': None,
            'fecha_vigencia': None,
        }

        try:
            # Buscar título (generalmente en <h2> o <h1>)
            titulo_tag = soup.find('h2', class_='titulo_parrafo') or soup.find('h1')
            if titulo_tag:
                metadata['titulo'] = titulo_tag.get_text(strip=True)

            # Buscar fechas en la página
            # El formato puede variar, intentamos varios selectores
            fecha_tags = soup.find_all('p', class_='fecha')
            for tag in fecha_tags:
                texto = tag.get_text()
                if 'publicaci' in texto.lower():
                    metadata['fecha_publicacion'] = texto.strip()
                if 'vigencia' in texto.lower():
                    metadata['fecha_vigencia'] = texto.strip()

        except Exception as e:
            logger.warning(f"Error extrayendo metadata: {e}")

        return metadata

    def _extraer_articulos(self, soup: BeautifulSoup) -> Dict[str, Dict]:
        """
        Extrae todos los artículos de la ley

        Args:
            soup: BeautifulSoup object

        Returns:
            Dict {numero_articulo: {texto, titulo, apartados}}
        """
        articulos = {}

        try:
            # Los artículos en BOE consolidado suelen estar en divs con clase 'articulo'
            # o en elementos con id que empieza con 'art'

            # Estrategia 1: Buscar por clase 'articulo'
            articulos_tags = soup.find_all('div', class_='articulo')

            # Estrategia 2: Si no hay, buscar por estructura de encabezados
            if not articulos_tags:
                articulos_tags = soup.find_all(['div', 'section'], attrs={'id': lambda x: x and x.startswith('art')})

            # Estrategia 3: Buscar por patrones de texto "Artículo N"
            if not articulos_tags:
                articulos_tags = []
                for tag in soup.find_all(['h3', 'h4', 'h5', 'p']):
                    texto = tag.get_text().strip()
                    if texto.startswith('Artículo') or texto.startswith('Art.') or texto.startswith('Art '):
                        # Encontramos un encabezado de artículo
                        # Intentar capturar todo el contenido hasta el siguiente artículo
                        articulo_div = tag.find_parent(['div', 'section']) or tag
                        articulos_tags.append(articulo_div)

            logger.debug(f"   Encontrados {len(articulos_tags)} artículos potenciales")

            for art_tag in articulos_tags:
                articulo_data = self._parsear_articulo(art_tag)
                if articulo_data:
                    num = articulo_data.get('numero')
                    if num:
                        articulos[num] = articulo_data

        except Exception as e:
            logger.error(f"Error extrayendo artículos: {e}")

        return articulos

    def _parsear_articulo(self, tag) -> Optional[Dict]:
        """
        Parsea un artículo individual

        Args:
            tag: Tag de BeautifulSoup con el artículo

        Returns:
            Dict con datos del artículo o None
        """
        try:
            texto_completo = tag.get_text(separator='\n', strip=True)

            # Intentar extraer número de artículo
            # Formato típico: "Artículo 12." o "Art. 5"
            numero = None
            titulo = None

            # Buscar encabezado del artículo
            encabezado_tags = tag.find_all(['h3', 'h4', 'h5', 'span', 'strong'], limit=3)
            for enc_tag in encabezado_tags:
                texto_enc = enc_tag.get_text(strip=True)

                # Extraer número
                import re
                match = re.match(r'Art(?:ículo|\.)\s+(\d+(?:\.\d+)?)', texto_enc)
                if match:
                    numero = match.group(1)
                    # El título puede estar después del número
                    titulo = texto_enc[match.end():].strip('. ')
                    break

            if not numero:
                # Intentar extraer del texto completo
                match = re.search(r'Art(?:ículo|\.)\s+(\d+(?:\.\d+)?)', texto_completo)
                if match:
                    numero = match.group(1)

            if not numero:
                return None  # No pudimos identificar el número de artículo

            # Extraer texto del contenido (sin el encabezado)
            contenido = texto_completo
            if titulo:
                # Remover encabezado del contenido
                contenido = texto_completo.split(titulo, 1)[-1].strip()

            return {
                'numero': numero,
                'titulo': titulo or '',
                'texto_completo': texto_completo,
                'contenido': contenido,
                'html': str(tag)
            }

        except Exception as e:
            logger.warning(f"Error parseando artículo: {e}")
            return None

    def verificar_articulo_existe(self, boe_id: str, numero_articulo: str) -> bool:
        """
        Verifica si un artículo específico existe en una ley

        Args:
            boe_id: ID de la ley
            numero_articulo: Número del artículo (ej: "39", "12.2")

        Returns:
            True si el artículo existe, False si no
        """
        # Descargar la ley (usa caché si está disponible)
        ley_data = self.descargar_ley(boe_id)

        if not ley_data:
            logger.warning(f"No se pudo descargar la ley {boe_id}")
            return False

        articulos = ley_data.get('articulos', {})

        # Normalizar número de artículo
        numero_norm = numero_articulo.strip().lstrip('0')

        # Buscar el artículo
        existe = numero_norm in articulos

        if existe:
            logger.info(f"Artículo {numero_articulo} existe en {boe_id}")
        else:
            logger.warning(f"Artículo {numero_articulo} NO existe en {boe_id}")
            logger.debug(f"   Artículos disponibles: {list(articulos.keys())[:10]}...")

        return existe

    def obtener_texto_articulo(self, boe_id: str, numero_articulo: str) -> Optional[str]:
        """
        Obtiene el texto oficial de un artículo específico

        Args:
            boe_id: ID de la ley
            numero_articulo: Número del artículo

        Returns:
            Texto del artículo o None si no existe
        """
        ley_data = self.descargar_ley(boe_id)

        if not ley_data:
            return None

        articulos = ley_data.get('articulos', {})
        numero_norm = numero_articulo.strip().lstrip('0')

        articulo_data = articulos.get(numero_norm)

        if articulo_data:
            return articulo_data.get('texto_completo')
        else:
            return None

    def _get_cache_path(self, boe_id: str) -> Path:
        """Genera path del archivo de caché para una ley"""
        return self.cache_dir / f"{boe_id}.json"

    def _get_from_cache(self, boe_id: str) -> Optional[Dict]:
        """
        Obtiene una ley del caché si existe y no está expirada

        Args:
            boe_id: ID de la ley

        Returns:
            Dict con datos de la ley o None
        """
        cache_path = self._get_cache_path(boe_id)

        if not cache_path.exists():
            return None

        # Verificar edad del caché
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - file_time > timedelta(days=self.cache_days):
            logger.debug(f"   Caché expirado para {boe_id}")
            return None

        # Leer del caché
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['cached'] = True
            return data

        except Exception as e:
            logger.warning(f"Error leyendo caché de {boe_id}: {e}")
            return None

    def _save_to_cache(self, boe_id: str, data: Dict):
        """
        Guarda una ley en el caché

        Args:
            boe_id: ID de la ley
            data: Datos a guardar
        """
        cache_path = self._get_cache_path(boe_id)

        try:
            # No guardar el HTML en caché (muy grande)
            # Solo guardar artículos y metadata
            cache_data = {
                'boe_id': data['boe_id'],
                'articulos': data['articulos'],
                'metadata': data['metadata'],
                'fecha_descarga': data['fecha_descarga'],
                'url': data['url']
            }

            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"   Caché guardado para {boe_id}")

        except Exception as e:
            logger.error(f"Error guardando caché de {boe_id}: {e}")


# Helper function
def verificar_articulo(boe_id: str, numero_articulo: str) -> bool:
    """
    Función helper para verificar si un artículo existe

    Args:
        boe_id: ID del BOE
        numero_articulo: Número de artículo

    Returns:
        True si existe, False si no
    """
    downloader = BOEDownloader()
    return downloader.verificar_articulo_existe(boe_id, numero_articulo)

# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

BOE Article Fetcher
Obtiene el texto completo de artículos específicos desde la API del BOE
Usa el endpoint /texto/indice para encontrar el ID correcto del bloque,
solucionando el problema de diferentes estructuras entre leyes.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import requests
import xml.etree.ElementTree as ET
import re
import logging
from typing import Optional, Dict, List
from functools import lru_cache

logger = logging.getLogger(__name__)


class BOEArticleFetcher:
    """
    Obtiene artículos específicos del BOE usando la API oficial

    Estrategia:
    1. Intentar método directo (a{numero})
    2. Si falla (404), obtener índice completo y buscar bloque correcto
    3. Caché inteligente para minimizar llamadas a la API
    """

    BOE_API_BASE = "https://www.boe.es/datosabiertos/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Agente-Oposiciones/1.0)',
            'Accept': 'application/xml'
        })

    @lru_cache(maxsize=200)
    def obtener_articulo(
        self,
        boe_id: str,
        numero_articulo: str
    ) -> Optional[Dict[str, str]]:
        """
        Obtiene el texto completo de un artículo específico

        Args:
            boe_id: ID del BOE (ej: "BOE-A-1985-12666" para LOPJ)
            numero_articulo: Número del artículo (ej: "456", "14", "1.2", "117.3")

        Returns:
            Dict con:
            - numero: Número del artículo
            - titulo: Título del artículo
            - texto: Texto completo del artículo en HTML
            - boe_id: ID del BOE
            - url: URL directa al artículo
            - None si no se encuentra
        """
        try:
            logger.info(f"Obteniendo artículo {numero_articulo} de {boe_id}")

            # ESTRATEGIA 1: Intentar método directo (rápido)
            num_norm = self._normalizar_numero_articulo(numero_articulo)
            id_bloque_directo = f"a{num_norm}"

            articulo = self._intentar_descarga_directa(boe_id, id_bloque_directo, numero_articulo)
            if articulo:
                logger.info(f"✅ Artículo {numero_articulo} encontrado (método directo)")
                return articulo

            # ESTRATEGIA 2: Obtener índice y buscar el bloque correcto (fallback inteligente)
            logger.info(f"Método directo falló, buscando en índice completo...")
            articulo = self._buscar_en_indice(boe_id, numero_articulo)

            if articulo:
                logger.info(f"✅ Artículo {numero_articulo} encontrado (vía índice)")
                return articulo

            # ESTRATEGIA 3: Si es subapartado (ej: "517.2.5.º", "22.e)"), intentar artículo base
            if '.' in numero_articulo or ')' in numero_articulo:
                # Extraer artículo base (antes del primer punto)
                articulo_base = numero_articulo.split('.')[0].split(')')[0]
                if articulo_base != numero_articulo:
                    logger.info(f"Subapartado detectado, intentando artículo base: {articulo_base}")
                    articulo = self.obtener_articulo(boe_id, articulo_base)
                    if articulo:
                        # Marcar que es un subapartado del artículo base
                        articulo['es_subapartado'] = True
                        articulo['numero_subapartado'] = numero_articulo
                        logger.info(f"✅ Artículo base {articulo_base} encontrado para subapartado {numero_articulo}")
                        return articulo

            logger.warning(f"❌ Artículo {numero_articulo} no disponible en {boe_id}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo artículo {numero_articulo} de {boe_id}: {e}")
            return None

    def _intentar_descarga_directa(
        self,
        boe_id: str,
        id_bloque: str,
        numero_articulo: str
    ) -> Optional[Dict[str, str]]:
        """
        Intenta descargar el artículo usando múltiples patrones de ID de bloque

        Args:
            boe_id: ID del BOE
            id_bloque: ID estimado del bloque (ej: "a456")
            numero_articulo: Número original del artículo

        Returns:
            Dict con datos del artículo, o None si falla
        """
        # Normalizar número de artículo
        num_norm = self._normalizar_numero_articulo(numero_articulo)
        num_base = num_norm.split('.')[0]  # Número base sin subapartados

        # Lista de patrones a probar en orden de probabilidad
        # Basado en el análisis exhaustivo de la API del BOE
        patrones_id = [
            f"a{num_base}",      # Patrón estándar (Constitución, etc.)
            f"art{num_base}",    # Patrón Código Civil (BOE-A-1889-4763)
            f"a{num_base}bis",   # Artículos bis
            f"art{num_base}bis", # Artículos bis en Código Civil
            id_bloque,           # Patrón original pasado como parámetro
        ]

        # Patrón LOPJ (números en español) - solo si el número es válido
        try:
            num_int = int(num_base)
            patron_lopj = self._numero_a_palabras_lopj(num_int)
            patrones_id.insert(1, patron_lopj)  # Insertar después del patrón estándar
        except (ValueError, TypeError):
            pass  # Si no es un número válido, ignorar patrón LOPJ

        # Intentar cada patrón en secuencia
        for id_test in patrones_id:
            xml_content = self._descargar_bloque_articulo(boe_id, id_test)
            if xml_content:
                articulo = self._extraer_articulo_bloque(xml_content, numero_articulo, boe_id)
                if articulo:
                    logger.info(f"✅ Artículo {numero_articulo} encontrado con patrón ID: {id_test}")
                    return articulo

        # Si ningún patrón funcionó
        logger.debug(f"Ningún patrón directo funcionó para artículo {numero_articulo}")
        return None

    @lru_cache(maxsize=50)
    def _obtener_indice(self, boe_id: str) -> List[Dict[str, str]]:
        """
        Obtiene el índice completo de la norma (todos los bloques disponibles)

        Args:
            boe_id: ID del BOE

        Returns:
            Lista de diccionarios con:
            - id: ID del bloque
            - titulo: Título del bloque
            - fecha_actualizacion: Fecha de última actualización
        """
        try:
            url = f"{self.BOE_API_BASE}/legislacion-consolidada/id/{boe_id}/texto/indice"
            logger.debug(f"Descargando índice desde: {url}")

            response = self.session.get(url, timeout=20)

            if response.status_code != 200:
                logger.error(f"Error HTTP {response.status_code} al obtener índice de {boe_id}")
                return []

            # Parsear XML del índice
            root = ET.fromstring(response.text)

            # Extraer todos los bloques
            bloques = []
            for bloque_elem in root.findall('.//bloque'):
                id_bloque = bloque_elem.find('id')
                titulo = bloque_elem.find('titulo')
                fecha_act = bloque_elem.find('fecha_actualizacion')

                # Solo incluir bloques que tengan ambos: ID y título con texto
                if (id_bloque is not None and id_bloque.text and
                    titulo is not None and titulo.text):
                    bloques.append({
                        'id': id_bloque.text.strip(),
                        'titulo': titulo.text.strip(),
                        'fecha_actualizacion': fecha_act.text.strip() if (fecha_act is not None and fecha_act.text) else ''
                    })

            logger.info(f"Índice obtenido: {len(bloques)} bloques encontrados")
            return bloques

        except Exception as e:
            logger.error(f"Error obteniendo índice de {boe_id}: {e}")
            return []

    def _buscar_en_indice(
        self,
        boe_id: str,
        numero_articulo: str
    ) -> Optional[Dict[str, str]]:
        """
        Busca el artículo en el índice completo de la norma

        Args:
            boe_id: ID del BOE
            numero_articulo: Número del artículo a buscar

        Returns:
            Dict con datos del artículo, o None si no se encuentra
        """
        # Obtener índice completo
        indice = self._obtener_indice(boe_id)
        if not indice:
            logger.error(f"No se pudo obtener el índice de {boe_id}")
            return None

        # Normalizar número de artículo para búsqueda
        num_normalizado = self._normalizar_numero_articulo(numero_articulo)

        # Extraer número base (sin subapartado) para fallback
        # Por ejemplo: "117.3" -> "117"
        num_base = num_normalizado.split('.')[0]

        # Patrones de búsqueda (de más específico a más general)
        patrones = []

        # 1. Intentar con número completo (ej: "117.3")
        if '.' in num_normalizado:
            patrones.extend([
                rf'^Art[ií]culo\s+{re.escape(num_normalizado)}\.?$',
                rf'^Art[ií]culo\s+{re.escape(num_normalizado)}\b',
            ])

        # 2. Intentar con número base (ej: "117") - FALLBACK para subapartados
        patrones.extend([
            rf'^Art[ií]culo\s+{re.escape(num_base)}\.?$',
            rf'^Art[ií]culo\s+{re.escape(num_base)}\b',
            # Variaciones
            rf'\bArt\.\s*{re.escape(num_base)}\b',
            rf'\b{re.escape(num_base)}\b.*Art[ií]culo',
        ])

        # Buscar en el índice
        for bloque in indice:
            titulo = bloque.get('titulo', '')
            id_bloque = bloque.get('id', '')

            # Skip si no tiene título o id
            if not titulo or not id_bloque:
                continue

            # Intentar cada patrón
            for patron in patrones:
                if re.search(patron, titulo, re.IGNORECASE):
                    logger.info(f"Encontrado en índice: '{titulo}' -> {id_bloque}")

                    # Descargar el bloque encontrado
                    xml_content = self._descargar_bloque_articulo(boe_id, id_bloque)
                    if xml_content:
                        return self._extraer_articulo_bloque(xml_content, numero_articulo, boe_id)

        # No encontrado
        logger.warning(f"Artículo {numero_articulo} no encontrado en el índice de {boe_id}")
        return None

    def _descargar_bloque_articulo(self, boe_id: str, id_bloque: str) -> Optional[str]:
        """
        Descarga un bloque específico (artículo) del BOE

        Args:
            boe_id: ID del BOE (ej: "BOE-A-1985-12666")
            id_bloque: ID del bloque (ej: "a456" para artículo 456)

        Returns:
            Contenido XML del bloque como string, o None si falla
        """
        try:
            # URL de la API para obtener un bloque específico
            url = f"{self.BOE_API_BASE}/legislacion-consolidada/id/{boe_id}/texto/bloque/{id_bloque}"

            logger.debug(f"Descargando bloque desde: {url}")
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                return response.text
            else:
                logger.debug(f"HTTP {response.status_code} para bloque {id_bloque} de {boe_id}")
                return None

        except requests.RequestException as e:
            logger.error(f"Error de red al descargar bloque {id_bloque} de {boe_id}: {e}")
            return None

    def _extraer_articulo_bloque(
        self,
        xml_content: str,
        numero_articulo: str,
        boe_id: str
    ) -> Optional[Dict[str, str]]:
        """
        Extrae el artículo del XML de respuesta del endpoint /texto/bloque

        Args:
            xml_content: Contenido XML de la respuesta
            numero_articulo: Número del artículo original
            boe_id: ID del BOE

        Returns:
            Dict con datos del artículo, o None si no se encuentra
        """
        try:
            root = ET.fromstring(xml_content)

            # Verificar que la respuesta sea correcta
            status_code = root.find('.//code')
            if status_code is None or status_code.text != '200':
                logger.debug(f"Respuesta no exitosa del BOE")
                return None

            # Extraer el bloque
            bloque = root.find('.//bloque')
            if bloque is None:
                logger.error(f"No se encontró el bloque en la respuesta")
                return None

            # Extraer título del bloque
            titulo = bloque.get('titulo', '')

            # Extraer la versión más reciente (la primera)
            version = bloque.find('version')
            if version is None:
                logger.error(f"No se encontró ninguna versión del artículo")
                return None

            # Extraer todo el HTML dentro de <version>
            # Combinar todos los elementos <p>, <table>, etc.
            html_parts = []
            for elem in version:
                # Convertir cada elemento a string HTML
                html_str = ET.tostring(elem, encoding='unicode', method='html')
                html_parts.append(html_str)

            texto_html = '\n'.join(html_parts)

            # Extraer número base del artículo
            num_base = self._normalizar_numero_articulo(numero_articulo)

            return {
                'numero': num_base,
                'titulo': titulo,
                'texto': texto_html,
                'boe_id': boe_id,
                'url': f"https://www.boe.es/buscar/act.php?id={boe_id}#a{num_base}"
            }

        except ET.ParseError as e:
            logger.error(f"Error parseando XML: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extrayendo artículo del bloque: {e}")
            return None

    def _normalizar_numero_articulo(self, numero: str) -> str:
        """
        Normaliza el número de artículo para comparación

        Args:
            numero: Número original (ej: "Art. 456", "artículo 14", "1.2", "117.3")

        Returns:
            Número normalizado (ej: "456", "14", "1.2", "117.3")

        Nota: Ahora conserva los subapartados (ej: "117.3") para búsqueda más precisa
        """
        # Quitar prefijos comunes
        numero = re.sub(r'^(art\.?|artículo|art)\s*', '', numero.lower(), flags=re.IGNORECASE)
        # Quitar espacios
        numero = numero.strip()

        # Extraer el número (puede incluir puntos para subapartados)
        match = re.match(r'^(\d+(?:\.\d+)?)', numero)
        if match:
            return match.group(1)

        return numero

    def _numero_a_palabras_lopj(self, numero: int) -> str:
        """
        Convierte un número a palabras en español para el patrón de LOPJ

        Args:
            numero: Número de artículo (ej: 456, 117, 25)

        Returns:
            ID en formato LOPJ (ej: "acuatrocientoscincuentayseis", "acientodiecisiete", "aveinticinco")

        Nota: LOPJ usa nombres completos en español precedidos por "a"
        """
        # Unidades (0-9)
        unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']

        # Decenas especiales (10-19)
        especiales = ['diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciséis',
                      'diecisiete', 'dieciocho', 'diecinueve']

        # Decenas (20-90)
        decenas = ['', '', 'veint', 'treinta', 'cuarenta', 'cincuenta',
                   'sesenta', 'setenta', 'ochenta', 'noventa']

        # Centenas
        centenas = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos', 'quinientos',
                    'seiscientos', 'setecientos', 'ochocientos', 'novecientos']

        if numero == 0:
            return 'acero'

        if numero < 10:
            # Primeros artículos usan nombres especiales en LOPJ
            if numero == 1:
                return 'aprimero'
            elif numero == 2:
                return 'asegundo'
            elif numero == 3:
                return 'atercero'
            elif numero == 4:
                return 'acuarto'
            elif numero == 5:
                return 'aquinto'
            elif numero == 6:
                return 'asexto'
            elif numero == 7:
                return 'aseptimo'
            elif numero == 8:
                return 'aoctavo'
            elif numero == 9:
                return 'anoveno'

        resultado = ''

        # Centenas
        c = numero // 100
        if c > 0:
            if numero == 100:
                resultado = 'cien'
            else:
                resultado = centenas[c]

        # Decenas y unidades
        resto = numero % 100
        if resto >= 10 and resto < 20:
            # Casos especiales 10-19
            resultado += especiales[resto - 10]
        elif resto >= 20:
            # 20-99
            d = resto // 10
            u = resto % 10
            if resto >= 20 and resto <= 29:
                # Veinti- casos
                if u == 0:
                    resultado += 'veinte'
                else:
                    resultado += decenas[d] + 'i' + unidades[u]
            else:
                # 30-99
                resultado += decenas[d]
                if u > 0:
                    resultado += 'y' + unidades[u]
        else:
            # 1-9 (en decenas)
            if resto > 0:
                resultado += unidades[resto]

        return 'a' + resultado

    @lru_cache(maxsize=100)
    def obtener_titulo_ley(self, boe_id: str) -> Optional[str]:
        """
        Obtiene el título completo de una ley desde su BOE-ID

        Args:
            boe_id: ID del BOE (ej: "BOE-A-2015-10565")

        Returns:
            Título completo de la ley, o None si no se encuentra
        """
        try:
            url = f"{self.BOE_API_BASE}/legislacion-consolidada/id/{boe_id}"
            logger.debug(f"Obteniendo título de {boe_id}")

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Error HTTP {response.status_code} al obtener título de {boe_id}")
                return None

            # Parsear XML
            root = ET.fromstring(response.text)

            # El título está en <titulo>
            titulo_elem = root.find('.//titulo')
            if titulo_elem is not None and titulo_elem.text:
                titulo = titulo_elem.text.strip()
                logger.debug(f"Título encontrado: {titulo[:80]}...")
                return titulo

            logger.warning(f"No se encontró título en la respuesta para {boe_id}")
            return None

        except Exception as e:
            logger.error(f"Error obteniendo título de {boe_id}: {e}")
            return None



# Singleton global
_boe_fetcher = None


def get_boe_article_fetcher() -> BOEArticleFetcher:
    """
    Obtiene la instancia singleton del fetcher
    """
    global _boe_fetcher
    if _boe_fetcher is None:
        _boe_fetcher = BOEArticleFetcher()
    return _boe_fetcher

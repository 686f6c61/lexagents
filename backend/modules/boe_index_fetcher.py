# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

BOE Index Fetcher
Obtiene el índice completo (estructura) de una ley desde la API del BOE
Este módulo descarga la estructura completa de una ley (títulos, capítulos,
secciones, artículos) desde el endpoint /texto/indice del BOE.
NO usa IA - Todo viene directamente del BOE API oficial.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import requests
import xml.etree.ElementTree as ET
import logging
from typing import Optional, Dict, List
from functools import lru_cache
import re

logger = logging.getLogger(__name__)


class BOEIndexFetcher:
    """
    Obtiene el índice completo de leyes desde el BOE

    Propósito:
    - Descargar estructura completa de una ley (títulos, capítulos, artículos)
    - Fuente 100% real (no alucinación)
    - Cache para evitar múltiples descargas
    """

    BOE_API_BASE = "https://www.boe.es/datosabiertos/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Agente-Oposiciones/1.0)',
            'Accept': 'application/xml'
        })

    @lru_cache(maxsize=50)
    def obtener_indice(self, boe_id: str) -> Optional[Dict]:
        """
        Obtiene el índice completo de una ley

        Args:
            boe_id: ID del BOE (ej: "BOE-A-1995-25444" para Código Penal)

        Returns:
            Dict con estructura completa:
            {
                'boe_id': 'BOE-A-1995-25444',
                'ley': 'Código Penal',
                'titulos': [
                    {
                        'id': 'tit1',
                        'nombre': 'TÍTULO I. Del homicidio y sus formas',
                        'articulos': [
                            {'numero': '138', 'nombre': 'Artículo 138', 'id': 'a138'},
                            {'numero': '139', 'nombre': 'Artículo 139. Asesinato', 'id': 'a139'},
                            ...
                        ]
                    },
                    ...
                ],
                'articulos': [  # Lista plana de todos los artículos
                    {'numero': '138', 'nombre': 'Artículo 138', 'titulo': 'TÍTULO I...'},
                    ...
                ],
                'total_articulos': 639
            }

            None si no se puede obtener
        """
        try:
            logger.info(f"📥 Obteniendo índice del BOE: {boe_id}")

            # Endpoint del índice
            url = f"{self.BOE_API_BASE}/legislacion-consolidada/id/{boe_id}/texto/indice"

            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                logger.warning(f"⚠️  BOE API retornó {response.status_code} para {boe_id}")
                return None

            # Parsear XML
            root = ET.fromstring(response.content)

            # Extraer nombre de la ley
            nombre_ley = self._extraer_nombre_ley(root, boe_id)

            # Parsear estructura
            titulos = self._parsear_estructura(root)

            # Crear lista plana de artículos
            articulos_planos = self._crear_lista_plana(titulos)

            indice = {
                'boe_id': boe_id,
                'ley': nombre_ley,
                'titulos': titulos,
                'articulos': articulos_planos,
                'total_articulos': len(articulos_planos)
            }

            logger.info(f"✅ Índice obtenido: {nombre_ley}")
            logger.info(f"   Títulos: {len(titulos)}")
            logger.info(f"   Artículos: {len(articulos_planos)}")

            return indice

        except Exception as e:
            logger.error(f"❌ Error obteniendo índice de {boe_id}: {e}")
            return None

    def _extraer_nombre_ley(self, root: ET.Element, boe_id: str) -> str:
        """Extrae el nombre de la ley del XML"""
        # Intentar extraer del título del documento
        titulo_elem = root.find('.//titulo')
        if titulo_elem is not None and titulo_elem.text:
            return titulo_elem.text.strip()

        # Fallback: usar BOE-ID
        return f"Ley {boe_id}"

    def _parsear_estructura(self, root: ET.Element) -> List[Dict]:
        """
        Parsea la estructura XML del índice

        Estructura REAL del BOE (flat list of bloques):
        <indice>
          <bloque><id>tpreliminar</id><titulo>TÍTULO PRELIMINAR</titulo></bloque>
          <bloque><id>a1</id><titulo>Artículo 1</titulo></bloque>
          <bloque><id>a2</id><titulo>Artículo 2</titulo></bloque>
          <bloque><id>li</id><titulo>LIBRO I</titulo></bloque>
          <bloque><id>ti</id><titulo>TÍTULO I. Del homicidio</titulo></bloque>
          <bloque><id>a138</id><titulo>Artículo 138</titulo></bloque>
          <bloque><id>a139</id><titulo>Artículo 139. Asesinato</titulo></bloque>
        </indice>

        Necesitamos reconstruir la jerarquía desde la lista plana.
        """

        titulos = []

        # Buscar todos los bloques
        bloques = root.findall('.//bloque')

        if not bloques:
            logger.warning("⚠️  No se encontraron <bloque> en el XML")
            return titulos

        # Variables para tracking de contexto
        titulo_actual = None
        articulos_actuales = []

        for bloque in bloques:
            # Extraer ID y título del bloque
            id_elem = bloque.find('id')
            titulo_elem = bloque.find('titulo')

            if id_elem is None or titulo_elem is None:
                continue

            bloque_id = id_elem.text.strip() if id_elem.text else ''
            bloque_titulo = titulo_elem.text.strip() if titulo_elem.text else ''

            # Determinar tipo de bloque por ID
            tipo = self._determinar_tipo_bloque(bloque_id)

            if tipo == 'titulo':
                # Nuevo título: guardar el anterior si existe
                if titulo_actual and articulos_actuales:
                    titulos.append({
                        'id': titulo_actual['id'],
                        'nombre': titulo_actual['nombre'],
                        'articulos': articulos_actuales
                    })

                # Iniciar nuevo título
                titulo_actual = {
                    'id': bloque_id,
                    'nombre': bloque_titulo
                }
                articulos_actuales = []

            elif tipo == 'articulo':
                # Artículo: extraer info
                art_info = self._extraer_info_articulo_desde_bloque(
                    bloque_id,
                    bloque_titulo,
                    titulo_actual['nombre'] if titulo_actual else ''
                )

                if art_info:
                    articulos_actuales.append(art_info)

            # Ignorar otros tipos (libro, capítulo, sección, etc.)

        # No olvidar el último título
        if titulo_actual and articulos_actuales:
            titulos.append({
                'id': titulo_actual['id'],
                'nombre': titulo_actual['nombre'],
                'articulos': articulos_actuales
            })

        # Si no hay títulos pero hay artículos, agrupar todos
        if not titulos and articulos_actuales:
            titulos.append({
                'id': 'raiz',
                'nombre': 'Artículos',
                'articulos': articulos_actuales
            })

        return titulos

    def _determinar_tipo_bloque(self, bloque_id: str) -> str:
        """
        Determina el tipo de bloque según su ID

        Patrones comunes del BOE:
        - Libros: "li", "lii", "liii", "liv", "lv"
        - Títulos: "tpreliminar", "ti", "tii", "tiii", etc.
        - Capítulos: "ci", "cii", "ciii", etc.
        - Secciones: "si", "sii", "siii", etc.
        - Artículos: "a1", "a2", "a138", etc.
        - Disposiciones: "daprimera", "dtprimera", etc.
        """
        bloque_id_lower = bloque_id.lower()

        # Artículos (más común)
        if re.match(r'^a\d+', bloque_id_lower):
            return 'articulo'

        # Títulos
        if bloque_id_lower.startswith('t') and (
            bloque_id_lower == 'tpreliminar' or
            re.match(r'^t[ivxlcdm]+$', bloque_id_lower)
        ):
            return 'titulo'

        # Libros
        if bloque_id_lower.startswith('l') and re.match(r'^l[ivxlcdm]+$', bloque_id_lower):
            return 'libro'

        # Capítulos
        if bloque_id_lower.startswith('c') and re.match(r'^c[ivxlcdm]+$', bloque_id_lower):
            return 'capitulo'

        # Secciones
        if bloque_id_lower.startswith('s') and re.match(r'^s[ivxlcdm]+$', bloque_id_lower):
            return 'seccion'

        return 'otro'

    def _extraer_info_articulo_desde_bloque(
        self,
        bloque_id: str,
        bloque_titulo: str,
        titulo_padre: str
    ) -> Optional[Dict]:
        """
        Extrae información de artículo desde un bloque

        Returns:
            {
                'numero': '138',
                'nombre': 'Artículo 138',
                'id': 'a138',
                'titulo_padre': 'TÍTULO I. ...'
            }
        """
        # Extraer número del artículo
        numero = self._extraer_numero_articulo(bloque_titulo, bloque_id)

        if not numero:
            return None

        return {
            'numero': numero,
            'nombre': bloque_titulo,
            'id': bloque_id,
            'titulo_padre': titulo_padre
        }

    def _extraer_numero_articulo(self, nombre: str, art_id: str) -> Optional[str]:
        """
        Extrae el número del artículo desde el nombre o ID

        Ejemplos:
        - "Artículo 138" → "138"
        - "Artículo 139. Asesinato" → "139"
        - "Art. 14.2" → "14.2"
        - ID: "a138" → "138"
        """
        # Intentar extraer del nombre
        match = re.search(r'[Aa]rt[íi]culo\s+(\d+(?:\.\d+)?)', nombre)
        if match:
            return match.group(1)

        # Intentar extraer del ID (ej: "a138" → "138")
        match = re.search(r'a(\d+)', art_id)
        if match:
            return match.group(1)

        return None

    def _crear_lista_plana(self, titulos: List[Dict]) -> List[Dict]:
        """
        Crea una lista plana de todos los artículos
        (útil para búsquedas rápidas)
        """
        plana = []

        for titulo in titulos:
            for articulo in titulo.get('articulos', []):
                plana.append({
                    'numero': articulo['numero'],
                    'nombre': articulo['nombre'],
                    'titulo': titulo['nombre'],
                    'id': articulo['id']
                })

        return plana

    def buscar_articulos_por_concepto(
        self,
        boe_id: str,
        concepto: str
    ) -> Optional[Dict]:
        """
        Busca artículos relacionados con un concepto en el índice real

        Args:
            boe_id: ID del BOE
            concepto: Concepto a buscar (ej: "homicidio", "aborto")

        Returns:
            {
                'concepto': 'homicidio',
                'titulo_encontrado': 'TÍTULO I. Del homicidio y sus formas',
                'articulos': ['138', '139', '140', '141', '142', '143'],
                'match_tipo': 'titulo',  # 'titulo', 'articulo', 'ninguno'
                'confianza': 90
            }

            None si no se encuentra
        """
        indice = self.obtener_indice(boe_id)

        if not indice:
            return None

        concepto_norm = concepto.lower().strip()

        logger.info(f"🔍 Buscando '{concepto}' en el índice de {boe_id}")

        # ESTRATEGIA 1: Buscar en TÍTULOS (más fiable)
        for titulo in indice['titulos']:
            nombre_titulo = titulo['nombre'].lower()

            if concepto_norm in nombre_titulo:
                # Match en título
                articulos_nums = [art['numero'] for art in titulo['articulos']]

                logger.info(f"✅ Encontrado en título: {titulo['nombre']}")
                logger.info(f"   Artículos: {', '.join(articulos_nums)}")

                return {
                    'concepto': concepto,
                    'titulo_encontrado': titulo['nombre'],
                    'articulos': articulos_nums,
                    'match_tipo': 'titulo',
                    'confianza': 90
                }

        # ESTRATEGIA 2: Buscar en NOMBRES de artículos (menos fiable)
        articulos_match = []
        for articulo in indice['articulos']:
            if concepto_norm in articulo['nombre'].lower():
                articulos_match.append(articulo)

        if articulos_match:
            logger.info(f"✅ Encontrado en {len(articulos_match)} artículos")

            return {
                'concepto': concepto,
                'titulo_encontrado': f'Artículos relacionados con "{concepto}"',
                'articulos': [art['numero'] for art in articulos_match],
                'match_tipo': 'articulo',
                'confianza': 70
            }

        # No encontrado
        logger.warning(f"⚠️  No se encontró '{concepto}' en el índice")
        return None

    def obtener_estadisticas(self, boe_id: str) -> Optional[Dict]:
        """
        Obtiene estadísticas del índice de una ley

        Returns:
            {
                'total_titulos': 10,
                'total_articulos': 639,
                'primer_articulo': '1',
                'ultimo_articulo': '639'
            }
        """
        indice = self.obtener_indice(boe_id)

        if not indice:
            return None

        articulos = indice['articulos']

        return {
            'total_titulos': len(indice['titulos']),
            'total_articulos': len(articulos),
            'primer_articulo': articulos[0]['numero'] if articulos else None,
            'ultimo_articulo': articulos[-1]['numero'] if articulos else None
        }


# Singleton
_fetcher_instance = None

def get_boe_index_fetcher() -> BOEIndexFetcher:
    """Obtiene instancia singleton del BOEIndexFetcher"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = BOEIndexFetcher()
    return _fetcher_instance


# =============================================================================
# TESTING (solo si se ejecuta directamente)
# =============================================================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Test con Código Penal
    fetcher = BOEIndexFetcher()

    print("\n" + "="*80)
    print("TEST: Obtener índice del Código Penal")
    print("="*80)

    indice = fetcher.obtener_indice("BOE-A-1995-25444")

    if indice:
        print(f"\n✅ Índice obtenido correctamente")
        print(f"   Ley: {indice['ley']}")
        print(f"   Títulos: {len(indice['titulos'])}")
        print(f"   Artículos: {indice['total_articulos']}")

        print("\n📋 Primeros 3 títulos:")
        for i, titulo in enumerate(indice['titulos'][:3]):
            print(f"\n{i+1}. {titulo['nombre']}")
            print(f"   Artículos: {len(titulo['articulos'])}")
            if titulo['articulos']:
                arts = [art['numero'] for art in titulo['articulos'][:5]]
                print(f"   Primeros: {', '.join(arts)}")

        print("\n" + "="*80)
        print("TEST: Buscar conceptos")
        print("="*80)

        conceptos = ['homicidio', 'aborto', 'lesiones']

        for concepto in conceptos:
            print(f"\n🔍 Buscando: {concepto}")
            resultado = fetcher.buscar_articulos_por_concepto("BOE-A-1995-25444", concepto)

            if resultado:
                print(f"✅ Encontrado en: {resultado['titulo_encontrado']}")
                print(f"   Artículos: {', '.join(resultado['articulos'])}")
                print(f"   Confianza: {resultado['confianza']}%")
            else:
                print(f"❌ No encontrado")
    else:
        print("❌ No se pudo obtener el índice")

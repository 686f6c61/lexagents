# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo 4: Extractor de Artículos
Extrae artículos específicos de leyes del BOE.
Parsea el HTML consolidado y extrae artículos con su contenido completo.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Articulo:
    """Representa un artículo de una ley"""
    numero: str  # "23", "23.2", "23.2.b"
    titulo: Optional[str]  # Título del artículo (si existe)
    contenido: str  # Texto completo del artículo
    apartados: List[str]  # Lista de apartados (si tiene)
    html_original: str  # HTML original del artículo
    ley_referencia: str  # Ley a la que pertenece (ej: "Ley 39/2015")


class ArticleExtractor:
    """Extractor de artículos de legislación del BOE"""

    def __init__(self):
        self.soup = None
        self.articulos = []

        # Patrones para identificar artículos
        self.patrones_articulo = [
            r'Artículo\s+(\d+(?:\.\d+)?(?:\.[a-z])?)',
            r'Art\.\s+(\d+(?:\.\d+)?(?:\.[a-z])?)',
            r'Art\s+(\d+(?:\.\d+)?(?:\.[a-z])?)',
        ]

    def extraer_de_html(self, html_content: str, ley_referencia: str = "") -> List[Dict]:
        """
        Extrae todos los artículos de un HTML del BOE

        Args:
            html_content: HTML de la ley consolidada
            ley_referencia: Referencia de la ley (ej: "Ley 39/2015")

        Returns:
            Lista de artículos como diccionarios
        """
        logger.info(f"📄 Extrayendo artículos de: {ley_referencia or 'ley sin especificar'}")

        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.articulos = []

        # Buscar todos los artículos en el HTML
        articulos_encontrados = self._buscar_articulos()

        # Parsear cada artículo
        for num, html_elem in articulos_encontrados:
            try:
                articulo = self._parsear_articulo(num, html_elem, ley_referencia)
                if articulo:
                    self.articulos.append(articulo)
            except Exception as e:
                logger.warning(f"Error parseando artículo {num}: {e}")

        logger.info(f"✅ Extraídos {len(self.articulos)} artículos")

        # Convertir a diccionarios para serialización
        return [asdict(art) for art in self.articulos]

    def extraer_articulo_especifico(
        self,
        html_content: str,
        numero_articulo: str,
        ley_referencia: str = ""
    ) -> Optional[Dict]:
        """
        Extrae un artículo específico por su número

        Args:
            html_content: HTML de la ley consolidada
            numero_articulo: Número del artículo (ej: "23", "23.2", "23.2.b")
            ley_referencia: Referencia de la ley

        Returns:
            Dict con el artículo o None si no se encuentra
        """
        logger.info(f"🔍 Buscando artículo {numero_articulo} en {ley_referencia}")

        # Extraer todos primero
        todos_articulos = self.extraer_de_html(html_content, ley_referencia)

        # Buscar el artículo específico
        for art in todos_articulos:
            if art['numero'] == numero_articulo:
                logger.info(f"✅ Artículo {numero_articulo} encontrado")
                return art

            # También buscar por coincidencia parcial (art. 23 incluye 23.1, 23.2, etc.)
            if art['numero'].startswith(f"{numero_articulo}."):
                logger.info(f"✅ Encontrado apartado: {art['numero']}")
                return art

        logger.warning(f"❌ Artículo {numero_articulo} no encontrado")
        return None

    def _buscar_articulos(self) -> List[Tuple[str, any]]:
        """
        Busca todos los elementos que representan artículos en el HTML

        Returns:
            Lista de tuplas (numero_articulo, elemento_html)
        """
        articulos = []

        # Estrategia 1: Buscar por estructura del BOE
        # El BOE suele usar <div class="articulo"> o <p class="articulo">
        for elem in self.soup.find_all(['div', 'p', 'h3', 'h4'], class_=re.compile(r'articulo|art\b', re.I)):
            numero = self._extraer_numero_articulo(elem.get_text())
            if numero:
                articulos.append((numero, elem))

        # Estrategia 2: Buscar por texto que contenga "Artículo X"
        if not articulos:
            for elem in self.soup.find_all(['p', 'div', 'h3', 'h4']):
                texto = elem.get_text(strip=True)
                numero = self._extraer_numero_articulo(texto)
                if numero:
                    articulos.append((numero, elem))

        # Eliminar duplicados
        articulos_unicos = {}
        for num, elem in articulos:
            if num not in articulos_unicos:
                articulos_unicos[num] = elem

        logger.debug(f"Encontrados {len(articulos_unicos)} artículos únicos")
        return list(articulos_unicos.items())

    def _extraer_numero_articulo(self, texto: str) -> Optional[str]:
        """
        Extrae el número de artículo de un texto

        Args:
            texto: Texto que puede contener "Artículo 123"

        Returns:
            Número del artículo (ej: "123", "123.2") o None
        """
        for patron in self.patrones_articulo:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parsear_articulo(
        self,
        numero: str,
        elemento: any,
        ley_referencia: str
    ) -> Optional[Articulo]:
        """
        Parsea un elemento HTML como artículo

        Args:
            numero: Número del artículo
            elemento: Elemento BeautifulSoup
            ley_referencia: Referencia de la ley

        Returns:
            Objeto Articulo o None
        """
        # Extraer título (si existe)
        titulo = self._extraer_titulo_articulo(elemento)

        # Extraer contenido completo
        contenido = self._extraer_contenido_articulo(elemento)

        # Extraer apartados (numeración interna)
        apartados = self._extraer_apartados(elemento)

        # HTML original
        html_original = str(elemento)

        if not contenido.strip():
            logger.warning(f"Artículo {numero} sin contenido")
            return None

        return Articulo(
            numero=numero,
            titulo=titulo,
            contenido=contenido,
            apartados=apartados,
            html_original=html_original,
            ley_referencia=ley_referencia
        )

    def _extraer_titulo_articulo(self, elemento: any) -> Optional[str]:
        """
        Extrae el título del artículo (si existe)

        Ejemplo: "Artículo 23. Derecho a ser informado."
                 Devuelve: "Derecho a ser informado"
        """
        texto = elemento.get_text(strip=True)

        # Buscar patrón: Artículo X. Título
        match = re.search(
            r'(?:Artículo|Art\.?)\s+\d+(?:\.\d+)?(?:\.[a-z])?\s*\.\s*(.+?)(?:\.|$)',
            texto,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return None

    def _extraer_contenido_articulo(self, elemento: any) -> str:
        """
        Extrae el contenido completo del artículo

        Args:
            elemento: Elemento BeautifulSoup

        Returns:
            Texto del artículo limpio
        """
        # Obtener todo el texto del elemento y sus hermanos siguientes
        # hasta el próximo artículo

        contenido_partes = []

        # Texto del elemento actual
        texto = elemento.get_text(strip=True)
        contenido_partes.append(texto)

        # Buscar elementos siguientes hasta el próximo artículo
        siguiente = elemento.find_next_sibling()
        while siguiente:
            # Si encontramos otro artículo, detenerse
            siguiente_texto = siguiente.get_text(strip=True)
            if self._extraer_numero_articulo(siguiente_texto):
                break

            # Si es un elemento de contenido, agregarlo
            if siguiente.name in ['p', 'div', 'ul', 'ol', 'li']:
                contenido_partes.append(siguiente_texto)

            siguiente = siguiente.find_next_sibling()

        # Unir todo el contenido
        contenido_completo = '\n'.join(contenido_partes)

        # Limpiar exceso de espacios en blanco
        contenido_completo = re.sub(r'\s+', ' ', contenido_completo)

        return contenido_completo.strip()

    def _extraer_apartados(self, elemento: any) -> List[str]:
        """
        Extrae los apartados de un artículo (numeración interna)

        Ejemplo:
        1. Primer apartado
        2. Segundo apartado
        a) Subapartado a
        b) Subapartado b
        """
        apartados = []

        # Buscar listas numeradas o con letras
        for lista in elemento.find_all(['ol', 'ul']):
            for item in lista.find_all('li'):
                texto = item.get_text(strip=True)
                if texto:
                    apartados.append(texto)

        # Buscar apartados en el texto plano
        texto = elemento.get_text()

        # Patrón: 1. texto, 2. texto, etc.
        matches = re.findall(r'^\s*(\d+)\.\s+(.+?)(?=\n\s*\d+\.|$)', texto, re.MULTILINE)
        for num, contenido in matches:
            apartados.append(f"{num}. {contenido.strip()}")

        # Patrón: a) texto, b) texto, etc.
        matches = re.findall(r'^\s*([a-z])\)\s+(.+?)(?=\n\s*[a-z]\)|$)', texto, re.MULTILINE)
        for letra, contenido in matches:
            apartados.append(f"{letra}) {contenido.strip()}")

        return apartados

    def buscar_articulos_por_patron(
        self,
        html_content: str,
        patron: str,
        ley_referencia: str = ""
    ) -> List[Dict]:
        """
        Busca artículos que contengan un patrón específico en su contenido

        Args:
            html_content: HTML de la ley
            patron: Expresión regular a buscar
            ley_referencia: Referencia de la ley

        Returns:
            Lista de artículos que coinciden
        """
        logger.info(f"🔍 Buscando artículos con patrón: {patron}")

        todos_articulos = self.extraer_de_html(html_content, ley_referencia)

        coincidencias = []
        for art in todos_articulos:
            if re.search(patron, art['contenido'], re.IGNORECASE):
                coincidencias.append(art)

        logger.info(f"✅ Encontrados {len(coincidencias)} artículos con el patrón")
        return coincidencias

    def estadisticas(self) -> Dict:
        """
        Devuelve estadísticas sobre los artículos extraídos

        Returns:
            Dict con estadísticas
        """
        if not self.articulos:
            return {
                'total_articulos': 0,
                'articulos_con_titulo': 0,
                'articulos_con_apartados': 0,
                'promedio_longitud': 0
            }

        return {
            'total_articulos': len(self.articulos),
            'articulos_con_titulo': sum(1 for a in self.articulos if a.titulo),
            'articulos_con_apartados': sum(1 for a in self.articulos if a.apartados),
            'promedio_longitud': sum(len(a.contenido) for a in self.articulos) / len(self.articulos)
        }


def extraer_articulo(
    html_content: str,
    numero_articulo: str,
    ley_referencia: str = ""
) -> Optional[Dict]:
    """
    Función helper para extraer un artículo específico

    Args:
        html_content: HTML de la ley consolidada
        numero_articulo: Número del artículo a extraer
        ley_referencia: Referencia de la ley

    Returns:
        Dict con el artículo o None
    """
    extractor = ArticleExtractor()
    return extractor.extraer_articulo_especifico(
        html_content,
        numero_articulo,
        ley_referencia
    )


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    print("=" * 60)
    print("📄 TEST DE EXTRACCIÓN DE ARTÍCULOS")
    print("=" * 60)

    # Intentar cargar una ley desde el caché
    cache_dir = Path("../../data/cache/boe_leyes")
    cache_files = list(cache_dir.glob("*.json"))

    if not cache_files:
        print("❌ No hay leyes en caché. Ejecuta primero boe_downloader.py")
        sys.exit(1)

    # Cargar la primera ley del caché
    import json
    cache_file = cache_files[0]

    print(f"\n📂 Cargando: {cache_file.name}")

    with open(cache_file, 'r', encoding='utf-8') as f:
        ley_data = json.load(f)

    html_content = ley_data.get('contenido', '')
    ley_referencia = ley_data['metadata'].get('numero_oficial', 'Ley sin identificar')

    print(f"📄 Ley: {ley_data['metadata'].get('titulo', 'N/A')}")
    print("-" * 60)

    # Test 1: Extraer artículo específico (artículo 23)
    extractor = ArticleExtractor()

    print("\n🔍 Test 1: Extraer artículo 23")
    articulo_23 = extractor.extraer_articulo_especifico(
        html_content,
        "23",
        ley_referencia
    )

    if articulo_23:
        print(f"✅ Artículo encontrado:")
        print(f"   Número: {articulo_23['numero']}")
        print(f"   Título: {articulo_23['titulo'] or 'N/A'}")
        print(f"   Contenido (primeros 200 chars): {articulo_23['contenido'][:200]}...")
        print(f"   Apartados: {len(articulo_23['apartados'])}")
    else:
        print("❌ Artículo 23 no encontrado")

    # Test 2: Extraer todos los artículos
    print("\n🔍 Test 2: Extraer todos los artículos")
    todos = extractor.extraer_de_html(html_content, ley_referencia)
    print(f"✅ Total de artículos extraídos: {len(todos)}")

    if todos:
        print(f"\n📋 Primeros 5 artículos:")
        for art in todos[:5]:
            print(f"   - Artículo {art['numero']}: {art['titulo'] or '(sin título)'}")

    # Test 3: Estadísticas
    print(f"\n📊 Estadísticas:")
    stats = extractor.estadisticas()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)

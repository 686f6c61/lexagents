# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo 1: Extractor de HTML de temas de oposiciones
Extrae y limpia el contenido HTML de los archivos JSON de temas,
manteniendo la estructura y trazabilidad.

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import json
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class HTMLExtractor:
    """Extractor de HTML de temas JSON"""

    def __init__(self):
        self.soup = None
        self.texto_limpio = ""
        self.lineas = []

    def extraer_de_json(self, json_path: str) -> Dict:
        """
        Extrae HTML de un archivo JSON de tema

        Args:
            json_path: Ruta al archivo JSON

        Returns:
            Dict con texto limpio, líneas y metadata
        """
        logger.info(f"Extrayendo HTML de: {json_path}")

        try:
            # Leer el archivo
            with open(json_path, 'r', encoding='utf-8') as f:
                contenido_raw = f.read()

            # Intentar parsear como JSON normal
            try:
                data = json.loads(contenido_raw)
                html_content = data['document']['documentVersion']['contenido']

            except json.JSONDecodeError as e:
                logger.warning(f"JSON mal formado, intentando reparación: {e}")
                # Reparar JSON con comillas mal escapadas
                html_content = self._extraer_html_fallback(contenido_raw)

            # Limpiar HTML
            resultado = self.limpiar_html(html_content)

            logger.info(f"✅ Extraído: {len(resultado['texto_limpio'])} caracteres")
            return resultado

        except FileNotFoundError:
            logger.error(f"❌ Archivo no encontrado: {json_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Error extrayendo HTML: {e}")
            raise

    def _extraer_html_fallback(self, contenido_raw: str) -> str:
        """
        Extrae HTML cuando el JSON está mal formado

        Busca el patrón "contenido": "..." y extrae el HTML
        """
        # Buscar el campo contenido
        match = re.search(r'"contenido"\s*:\s*"(.+)"', contenido_raw, re.DOTALL)

        if match:
            html_content = match.group(1)
            # Esto todavía tiene escapes, pero BeautifulSoup lo manejará
            return html_content
        else:
            # Último intento: buscar cualquier cosa que parezca HTML
            match = re.search(r'(<h1[^>]*>.*</h1>)', contenido_raw, re.DOTALL)
            if match:
                return match.group(1)

        raise ValueError("No se pudo extraer HTML del JSON")

    def limpiar_html(self, html_content: str) -> Dict:
        """
        Limpia HTML manteniendo estructura

        Args:
            html_content: HTML crudo

        Returns:
            Dict con:
            - texto_limpio: str
            - lineas: List[str]
            - metadata: Dict
        """
        # Parsear HTML con BeautifulSoup
        self.soup = BeautifulSoup(html_content, 'html.parser')

        # Extraer texto preservando estructura
        texto_limpio = self._extraer_texto_estructurado()

        # Dividir en líneas
        lineas = [linea.strip() for linea in texto_limpio.split('\n') if linea.strip()]

        # Metadata
        metadata = {
            'total_caracteres': len(texto_limpio),
            'total_lineas': len(lineas),
            'tiene_h1': bool(self.soup.find('h1')),
            'tiene_h2': bool(self.soup.find('h2')),
            'num_parrafos': len(self.soup.find_all('p')),
        }

        return {
            'texto_limpio': texto_limpio,
            'lineas': lineas,
            'metadata': metadata
        }

    def _extraer_texto_estructurado(self) -> str:
        """
        Extrae texto manteniendo estructura jerárquica

        - h1, h2, h3 → Con saltos de línea dobles
        - p → Con saltos de línea simples
        - Preserva numeración
        """
        resultado = []

        for element in self.soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
            texto = element.get_text(strip=True)

            if not texto:
                continue

            # Limpiar saltos de línea múltiples dentro del texto
            texto = re.sub(r'\s+', ' ', texto)

            # Agregar según el tipo de elemento
            if element.name in ['h1', 'h2']:
                # Títulos con separación
                resultado.append(f"\n\n{texto}\n")
            elif element.name == 'h3':
                resultado.append(f"\n{texto}\n")
            elif element.name == 'p':
                resultado.append(f"{texto}\n")
            elif element.name == 'li':
                resultado.append(f"- {texto}\n")

        texto_final = ''.join(resultado)

        # Limpiar exceso de saltos de línea
        texto_final = re.sub(r'\n{4,}', '\n\n\n', texto_final)

        return texto_final.strip()

    def extraer_estructura(self, html_content: str) -> Dict:
        """
        Extrae la estructura del documento (títulos, secciones)

        Returns:
            Dict con estructura jerárquica
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        estructura = {
            'titulo_principal': None,
            'secciones': []
        }

        # Título principal (h1)
        h1 = soup.find('h1')
        if h1:
            estructura['titulo_principal'] = h1.get_text(strip=True)

        # Secciones (h2)
        for i, h2 in enumerate(soup.find_all('h2')):
            seccion = {
                'numero': i + 1,
                'titulo': h2.get_text(strip=True),
                'subsecciones': []
            }

            # Buscar h3 después de este h2
            siguiente = h2.find_next_sibling()
            while siguiente and siguiente.name != 'h2':
                if siguiente.name == 'h3':
                    seccion['subsecciones'].append(siguiente.get_text(strip=True))
                siguiente = siguiente.find_next_sibling()

            estructura['secciones'].append(seccion)

        return estructura


def extraer_texto_de_tema(json_path: str) -> Dict:
    """
    Función helper para extraer texto de un tema

    Args:
        json_path: Ruta al JSON del tema

    Returns:
        Dict con texto limpio y metadata
    """
    extractor = HTMLExtractor()
    return extractor.extraer_de_json(json_path)


# Ejemplo de uso
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        tema_path = sys.argv[1]
    else:
        # Test con tema de ejemplo
        tema_path = "../../data/json/TramitaciónProcesalAdministrativa-Tema17.json"

    try:
        resultado = extraer_texto_de_tema(tema_path)

        print("=" * 60)
        print("📄 EXTRACCIÓN DE TEMA")
        print("=" * 60)
        print(f"\n📊 Metadata:")
        print(f"  - Caracteres: {resultado['metadata']['total_caracteres']}")
        print(f"  - Líneas: {resultado['metadata']['total_lineas']}")
        print(f"  - Párrafos: {resultado['metadata']['num_parrafos']}")

        print(f"\n📝 Primeras 500 caracteres:")
        print("-" * 60)
        print(resultado['texto_limpio'][:500])
        print("-" * 60)

        print(f"\n✅ Extracción exitosa")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

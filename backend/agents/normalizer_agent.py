# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Agente 2: Normalizador de Referencias Legales
Normaliza y enriquece referencias legales extraídas:
- Expande siglas usando CSV de siglas legales
- Normaliza formatos
- Resuelve ambigüedades

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
import csv
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

# Permitir imports relativos cuando se ejecuta como script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.base_agent import BaseAgent
else:
    from .base_agent import BaseAgent

# Importar funciones EUR-Lex
from modules.legal_abbreviations import (
    es_legislacion_europea,
    es_sigla_europea,
    expandir_sigla_europea,
    obtener_celex_por_sigla,
    procesar_nombre_ley_completo,
    SIGLAS_EUROPEAS
)

logger = logging.getLogger(__name__)


class NormalizerAgent(BaseAgent):
    """
    Agente normalizador de referencias legales

    Características:
    - Carga y usa diccionario de siglas legales
    - Expande abreviaturas
    - Normaliza formatos inconsistentes
    - Resuelve referencias ambiguas usando IA
    - Enriquece metadata
    """

    def __init__(
        self,
        siglas_csv_path: str = None,
        api_key: str = None
    ):
        """
        Inicializa el Agente Normalizador

        Args:
            siglas_csv_path: Ruta al CSV de siglas legales
            api_key: API key de Gemini (opcional)
        """
        super().__init__(
            nombre="Agente2-Normalizador",
            modelo="gemini-2.0-flash-exp",
            temperatura=0.2,  # Conservador pero flexible
            api_key=api_key
        )

        # Cargar diccionario de siglas
        if not siglas_csv_path:
            # Ruta por defecto
            base_path = Path(__file__).parent.parent.parent
            siglas_csv_path = base_path / "data" / "siglas" / "siglas_legales.csv"

        self.siglas_dict = self._cargar_siglas(siglas_csv_path)
        logger.info(f"✅ Diccionario de siglas cargado: {len(self.siglas_dict)} entradas")

    def _cargar_siglas(self, csv_path: str) -> Dict[str, List[str]]:
        """
        Carga el diccionario de siglas desde CSV

        Args:
            csv_path: Ruta al CSV

        Returns:
            Dict {sigla: [significado1, significado2, ...]}
        """
        siglas_dict = {}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    sigla = row.get('SIGLAS', '').strip()
                    significado = row.get('SIGNIFICADO', '').strip()

                    if sigla and significado:
                        # Normalizar sigla
                        sigla_norm = sigla.upper().replace('.', '')

                        # Puede haber múltiples significados (ej: CE)
                        if sigla_norm not in siglas_dict:
                            siglas_dict[sigla_norm] = []

                        siglas_dict[sigla_norm].append(significado)

            logger.debug(f"Cargadas {len(siglas_dict)} siglas desde {csv_path}")

            return siglas_dict

        except FileNotFoundError:
            logger.error(f"❌ Archivo CSV no encontrado: {csv_path}")
            return {}
        except Exception as e:
            logger.error(f"❌ Error cargando siglas: {e}")
            return {}

    def procesar(self, entrada: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa y normaliza una lista de referencias

        Args:
            entrada: Dict con:
                - 'referencias': List[Dict] - Referencias a normalizar
                - 'contexto': str - Contexto del tema (opcional)

        Returns:
            Dict con:
                - 'referencias_normalizadas': List[Dict]
                - 'total': int
                - 'cambios': int
                - 'agente': str
        """
        referencias = entrada.get('referencias', [])
        contexto = entrada.get('contexto', '')

        logger.info(f"[{self.nombre}] Normalizando {len(referencias)} referencias")

        referencias_normalizadas = []
        cambios = 0

        for ref in referencias:
            ref_normalizada, hubo_cambios = self._normalizar_referencia(ref, contexto)
            referencias_normalizadas.append(ref_normalizada)

            if hubo_cambios:
                cambios += 1

        logger.info(f"[{self.nombre}] Normalizadas {len(referencias_normalizadas)} referencias ({cambios} modificadas)")

        return {
            'referencias_normalizadas': referencias_normalizadas,
            'total': len(referencias_normalizadas),
            'cambios': cambios,
            'agente': self.nombre
        }

    def _normalizar_referencia(
        self,
        referencia: Dict,
        contexto: str
    ) -> tuple[Dict, bool]:
        """
        Normaliza una referencia individual

        Args:
            referencia: Referencia a normalizar
            contexto: Contexto del tema

        Returns:
            Tupla (referencia_normalizada, hubo_cambios)
        """
        ref_normalizada = referencia.copy()
        hubo_cambios = False

        # 0. NUEVO: Detectar y normalizar legislación europea
        texto_completo = referencia.get('texto_completo', '')
        ley_nombre = referencia.get('ley_nombre', '')

        if es_legislacion_europea(texto_completo) or es_legislacion_europea(ley_nombre):
            logger.debug(f"Detectada legislación europea: {texto_completo}")
            normalizada_eu, cambio_eu = self._normalizar_referencia_europea(ref_normalizada, contexto)
            if cambio_eu:
                ref_normalizada = normalizada_eu
                hubo_cambios = True
                # Marcar y retornar temprano si es europea
                ref_normalizada['_normalizada'] = True
                ref_normalizada['_europea'] = True
                return ref_normalizada, hubo_cambios

        # 1. Expandir siglas (españolas)
        if self._es_sigla(referencia):
            expandida, cambio = self._expandir_sigla(ref_normalizada, contexto)
            if cambio:
                ref_normalizada = expandida
                hubo_cambios = True

        # 2. Normalizar formato de ley (española)
        normalizada, cambio = self._normalizar_formato_ley(ref_normalizada)
        if cambio:
            ref_normalizada = normalizada
            hubo_cambios = True

        # 3. Enriquecer metadata
        enriquecida = self._enriquecer_metadata(ref_normalizada)
        ref_normalizada = enriquecida

        # 4. Marcar si fue normalizada
        if hubo_cambios:
            ref_normalizada['_normalizada'] = True

        return ref_normalizada, hubo_cambios

    def _es_sigla(self, referencia: Dict) -> bool:
        """
        Determina si una referencia es una sigla

        Args:
            referencia: Referencia a verificar

        Returns:
            True si es sigla, False si no
        """
        tipo = referencia.get('tipo', '').lower()
        texto = referencia.get('texto_completo', '')

        # Es sigla si el tipo es 'sigla' o si el texto es muy corto (< 10 chars) y todo mayúsculas
        if tipo == 'sigla':
            return True

        if len(texto) < 10 and texto.isupper():
            return True

        return False

    def _expandir_sigla(
        self,
        referencia: Dict,
        contexto: str
    ) -> tuple[Dict, bool]:
        """
        Expande una sigla a su significado completo

        Args:
            referencia: Referencia con sigla
            contexto: Contexto para resolver ambigüedades

        Returns:
            Tupla (referencia_expandida, hubo_cambio)
        """
        texto = referencia.get('texto_completo', '').strip().upper().replace('.', '')

        # Buscar en diccionario
        if texto in self.siglas_dict:
            significados = self.siglas_dict[texto]

            if len(significados) == 1:
                # Un solo significado - fácil
                significado = significados[0]
                logger.debug(f"Expandiendo sigla: {texto} → {significado}")

                referencia['significado_completo'] = significado
                referencia['sigla_original'] = texto
                referencia['_expandida'] = True

                # Intentar extraer número de ley del significado
                import re
                match = re.search(r'Ley\s+(\d+/\d{4})', significado)
                if match:
                    referencia['ley'] = match.group(1)

                return referencia, True

            else:
                # Múltiples significados - usar IA para resolver
                logger.debug(f"Sigla ambigua: {texto} tiene {len(significados)} significados")

                significado = self._resolver_ambiguedad_con_ia(
                    texto,
                    significados,
                    contexto
                )

                if significado:
                    referencia['significado_completo'] = significado
                    referencia['sigla_original'] = texto
                    referencia['_expandida'] = True
                    referencia['_ambigua_resuelta'] = True

                    return referencia, True

        return referencia, False

    def _resolver_ambiguedad_con_ia(
        self,
        sigla: str,
        significados: List[str],
        contexto: str
    ) -> Optional[str]:
        """
        Usa IA para resolver siglas ambiguas basándose en contexto

        Args:
            sigla: Sigla a resolver
            significados: Lista de posibles significados
            contexto: Contexto del tema

        Returns:
            Significado más probable o None
        """
        # Limitar contexto
        contexto_corto = contexto[:2000] if contexto else "(sin contexto)"

        prompt = f"""Dada la sigla "{sigla}" y el contexto de un tema de oposiciones, determina cuál es el significado más probable.

SIGLA: {sigla}

POSIBLES SIGNIFICADOS:
{chr(10).join(f"{i+1}. {sig}" for i, sig in enumerate(significados))}

CONTEXTO DEL TEMA:
{contexto_corto}

Responde SOLO con el número (1, 2, 3, etc.) del significado más probable según el contexto.
Si no hay suficiente contexto, responde con el significado más común en oposiciones de derecho administrativo."""

        try:
            respuesta = self.generar_contenido(
                prompt,
                system_instruction="Eres un experto en derecho administrativo español."
            )

            # Extraer número
            import re
            match = re.search(r'\b([1-9]\d?)\b', respuesta)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(significados):
                    logger.debug(f"IA resolvió {sigla} → {significados[idx]}")
                    return significados[idx]

        except Exception as e:
            logger.error(f"Error resolviendo ambigüedad con IA: {e}")

        # Fallback: primer significado
        return significados[0] if significados else None

    def _normalizar_formato_ley(self, referencia: Dict) -> tuple[Dict, bool]:
        """
        Normaliza el formato de una referencia de ley

        Args:
            referencia: Referencia a normalizar

        Returns:
            Tupla (referencia_normalizada, hubo_cambio)
        """
        ley = referencia.get('ley', '')

        if not ley:
            return referencia, False

        # Normalizar formato "Ley X/YYYY"
        import re

        # Caso: "Ley Orgánica 1/1996" → normalizar
        match = re.match(r'Ley\s+Orgánica\s+(\d+/\d{4})', ley, re.IGNORECASE)
        if match:
            referencia['ley_normalizada'] = f"Ley Orgánica {match.group(1)}"
            referencia['tipo_ley'] = 'organica'
            return referencia, True

        # Caso: "Ley 39/2015" → OK pero agregar metadata
        match = re.match(r'Ley\s+(\d+/\d{4})', ley, re.IGNORECASE)
        if match:
            referencia['ley_normalizada'] = f"Ley {match.group(1)}"
            referencia['tipo_ley'] = 'ordinaria'
            return referencia, True

        # Caso: "Real Decreto 203/2021"
        match = re.match(r'Real\s+Decreto\s+(?:Ley\s+)?(\d+/\d{4})', ley, re.IGNORECASE)
        if match:
            referencia['ley_normalizada'] = f"Real Decreto {match.group(1)}"
            referencia['tipo_ley'] = 'real_decreto'
            return referencia, True

        return referencia, False

    def _normalizar_referencia_europea(
        self,
        referencia: Dict,
        contexto: str
    ) -> tuple[Dict, bool]:
        """
        Normaliza referencias a legislación europea

        Casos a resolver:
        - "RGPD" → "Reglamento (UE) 2016/679"
        - "Art. 17 RGPD" → "Artículo 17 del Reglamento (UE) 2016/679"
        - "Reg. UE 2016/679" → "Reglamento (UE) 2016/679"
        - "Roma I" → "Reglamento (CE) No 593/2008"

        Args:
            referencia: Referencia europea a normalizar
            contexto: Contexto del tema

        Returns:
            Tupla (referencia_normalizada, hubo_cambio)
        """
        texto_original = referencia.get('texto_completo', '')
        ley_nombre = referencia.get('ley_nombre', '')

        # Extraer información de artículo si existe
        import re
        articulo_match = re.search(r'art(?:ículo|iculo)?\.?\s*(\d+)', texto_original, re.IGNORECASE)
        articulo = articulo_match.group(1) if articulo_match else None

        # Caso 1: Es una sigla europea conocida (RGPD, Roma I, etc.)
        texto_limpio = texto_original.strip()
        # Limpiar "Artículo X del" para detectar sigla
        texto_sin_articulo = re.sub(r'art(?:ículo|iculo)?\.?\s*\d+\s+del?\s+', '', texto_limpio, flags=re.IGNORECASE)

        if es_sigla_europea(texto_sin_articulo.strip()):
            sigla = texto_sin_articulo.strip()
            nombre_completo = expandir_sigla_europea(sigla)
            celex = obtener_celex_por_sigla(sigla)

            logger.debug(f"Expandiendo sigla europea: {sigla} → {nombre_completo}")

            referencia['nombre_completo'] = nombre_completo
            referencia['sigla_original'] = sigla
            referencia['_expandida'] = True

            if celex:
                referencia['celex'] = celex
                logger.debug(f"CELEX añadido: {celex}")

            if articulo:
                referencia['articulo'] = articulo
                referencia['texto_normalizado'] = f"Artículo {articulo} del {nombre_completo}"
            else:
                referencia['texto_normalizado'] = nombre_completo

            return referencia, True

        # Caso 2: Formato informal que necesita normalización con IA
        # "Reg. UE 2016/679", "Regl. (UE) 2016/679", etc.
        if any(palabra in texto_original.lower() for palabra in ['reg.', 'regl.', 'dir.', 'directiva', 'reglamento']):
            logger.debug(f"Normalizando formato europeo con IA: {texto_original}")

            normalizado = self._normalizar_formato_europeo_con_ia(texto_original, contexto)

            if normalizado:
                referencia['texto_normalizado'] = normalizado
                referencia['_normalizado_ia'] = True

                # Intentar extraer CELEX del formato normalizado
                from modules.eurlex_fetcher import extraer_celex_de_texto
                try:
                    celex = extraer_celex_de_texto(normalizado)
                    if celex:
                        referencia['celex'] = celex
                        logger.debug(f"CELEX extraído del texto normalizado: {celex}")
                except Exception as e:
                    logger.debug(f"No se pudo extraer CELEX: {e}")

                return referencia, True

        # Caso 3: Ya está en formato correcto (Reglamento (UE) YYYY/NNN)
        # Solo añadir CELEX si es posible
        from modules.eurlex_fetcher import extraer_celex_de_texto
        try:
            celex = extraer_celex_de_texto(texto_original)
            if celex:
                referencia['celex'] = celex
                referencia['texto_normalizado'] = texto_original
                logger.debug(f"CELEX extraído: {celex}")
                return referencia, True
        except Exception as e:
            logger.debug(f"No se pudo extraer CELEX del formato estándar: {e}")

        return referencia, False

    def _normalizar_formato_europeo_con_ia(
        self,
        texto: str,
        contexto: str
    ) -> Optional[str]:
        """
        Usa IA para normalizar formatos informales de legislación europea

        Args:
            texto: Texto a normalizar
            contexto: Contexto del tema

        Returns:
            Texto normalizado o None
        """
        # Contexto limitado
        contexto_corto = contexto[:1500] if contexto else "(sin contexto)"

        # Crear lista de ejemplos de siglas conocidas
        ejemplos_siglas = "\n".join([
            f"- {sigla} = {nombre}"
            for sigla, nombre in list(SIGLAS_EUROPEAS.items())[:10]
        ])

        prompt = f"""Normaliza la siguiente referencia a legislación europea al formato estándar oficial.

REFERENCIA A NORMALIZAR:
{texto}

CONTEXTO DEL TEMA:
{contexto_corto}

FORMATO ESTÁNDAR ESPERADO:
- Reglamento (UE) YYYY/NNN
- Reglamento (CE) No NNN/YYYY
- Directiva (UE) YYYY/NNN
- Directiva (CE) YYYY/NNN

SIGLAS EUROPEAS CONOCIDAS (ejemplos):
{ejemplos_siglas}

INSTRUCCIONES:
1. Si es una sigla conocida (RGPD, Roma I, etc.), expándela al nombre completo
2. Si tiene formato abreviado (Reg., Dir., etc.), expande a formato completo
3. Asegúrate de usar (UE) o (CE) según corresponda
4. Mantén el número y año exactos
5. Si hay mención de artículo, inclúyelo: "Artículo X del Reglamento..."

Responde SOLO con el texto normalizado, sin explicaciones adicionales."""

        try:
            respuesta = self.generar_contenido(
                prompt,
                system_instruction="Eres un experto en derecho europeo. Tu tarea es normalizar referencias a legislación de la UE al formato oficial estándar."
            )

            # Limpiar respuesta
            normalizado = respuesta.strip()

            # Validar que tenga sentido (debe contener palabras clave)
            if any(palabra in normalizado.lower() for palabra in ['reglamento', 'directiva', 'decisión']):
                logger.debug(f"IA normalizó: {texto} → {normalizado}")
                return normalizado
            else:
                logger.warning(f"IA devolvió respuesta inválida: {normalizado}")
                return None

        except Exception as e:
            logger.error(f"Error normalizando con IA: {e}")
            return None

    def _enriquecer_metadata(self, referencia: Dict) -> Dict:
        """
        Enriquece la metadata de una referencia

        Args:
            referencia: Referencia a enriquecer

        Returns:
            Referencia enriquecida
        """
        # Agregar metadata de normalización
        if '_metadata_normalizacion' not in referencia:
            referencia['_metadata_normalizacion'] = {}

        metadata = referencia['_metadata_normalizacion']

        # Marcar si tiene BOE-ID (para validación posterior)
        metadata['tiene_boe_id'] = 'boe_id' in referencia

        # Marcar si tiene artículo específico
        metadata['tiene_articulo'] = bool(referencia.get('articulo'))

        # Clasificar tipo de referencia
        if referencia.get('tipo') in ['ley', 'real_decreto']:
            metadata['categoria'] = 'normativa'
        elif referencia.get('tipo') in ['articulo', 'apartado']:
            metadata['categoria'] = 'disposicion'
        else:
            metadata['categoria'] = 'otra'

        return referencia

    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del agente normalizador

        Returns:
            Dict con estadísticas
        """
        return {
            'total_siglas_diccionario': len(self.siglas_dict),
            **self.obtener_metricas()
        }


# Función helper
def normalizar_referencias(
    referencias: List[Dict],
    contexto: str = "",
    siglas_csv_path: str = None
) -> List[Dict]:
    """
    Función helper para normalizar referencias

    Args:
        referencias: Lista de referencias a normalizar
        contexto: Contexto del tema (opcional)
        siglas_csv_path: Ruta al CSV de siglas (opcional)

    Returns:
        Lista de referencias normalizadas
    """
    agente = NormalizerAgent(siglas_csv_path=siglas_csv_path)

    resultado = agente.procesar({
        'referencias': referencias,
        'contexto': contexto
    })

    return resultado['referencias_normalizadas']


# Ejemplo de uso
if __name__ == "__main__":
    import sys
    from pathlib import Path
    from dotenv import load_dotenv

    # Cargar .env
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 60)
    print("🧪 TEST DEL AGENTE NORMALIZADOR")
    print("=" * 60)

    # Referencias de prueba
    referencias_prueba = [
        {
            'texto_completo': 'LPAC',
            'tipo': 'sigla',
            'contexto': 'El procedimiento administrativo...'
        },
        {
            'texto_completo': 'LEC',
            'tipo': 'sigla',
            'contexto': 'El proceso civil...'
        },
        {
            'texto_completo': 'CE',
            'tipo': 'sigla',
            'contexto': 'El artículo 24 reconoce el derecho a la tutela judicial efectiva...'
        },
        {
            'texto_completo': 'Ley 39/2015',
            'tipo': 'ley',
            'ley': 'Ley 39/2015',
        }
    ]

    # Normalizar
    agente = NormalizerAgent()
    resultado = agente.procesar({
        'referencias': referencias_prueba,
        'contexto': 'Tema sobre procedimiento administrativo común'
    })

    print(f"\n✅ Normalizadas: {resultado['total']}")
    print(f"✅ Cambios: {resultado['cambios']}")

    print(f"\n📋 Referencias Normalizadas:")
    print("-" * 60)

    for i, ref in enumerate(resultado['referencias_normalizadas'], 1):
        print(f"\n{i}. {ref.get('texto_completo')}")

        if ref.get('significado_completo'):
            print(f"   └─ Expandida a: {ref['significado_completo']}")

        if ref.get('ley_normalizada'):
            print(f"   └─ Ley normalizada: {ref['ley_normalizada']}")

        if ref.get('_expandida'):
            print(f"   └─ ✅ Expandida")

        if ref.get('_ambigua_resuelta'):
            print(f"   └─ ⚠️ Ambigüedad resuelta con IA")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)

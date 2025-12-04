# -*- coding: utf-8 -*-
"""
LexAgents - Sistema Multi-Agente de Extracción Legal
https://github.com/686f6c61/lexagents

Módulo Auditor
Analiza la calidad y confianza de las referencias extraídas:
- Calcula métricas de confianza
- Identifica referencias problemáticas
- Genera informes de cobertura

Author: 686f6c61
Version: 0.2.0
License: MIT
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class Auditor:
    """
    Auditor de calidad de referencias legales

    Analiza:
    - Confianza global del conjunto
    - Referencias de alta/baja confianza
    - Cobertura de validación
    - Problemas detectados
    - Sugerencias de mejora
    """

    def __init__(self):
        """Inicializa el auditor"""
        self.umbrales = {
            'confianza_alta': 90,
            'confianza_media': 70,
            'confianza_baja': 50,
            'tasa_validacion_buena': 0.70,
            'tasa_validacion_aceptable': 0.50
        }

    def auditar(self, referencias: List[Dict], metricas_pipeline: Dict = None) -> Dict[str, Any]:
        """
        Audita un conjunto de referencias

        Args:
            referencias: Lista de referencias a auditar
            metricas_pipeline: Métricas del pipeline (opcional)

        Returns:
            Dict con informe de auditoría completo
        """
        logger.info("🔍 Iniciando auditoría de referencias")

        # Análisis de confianza
        analisis_confianza = self._analizar_confianza(referencias)

        # Análisis de validación
        analisis_validacion = self._analizar_validacion(referencias)

        # Detección de problemas
        problemas = self._detectar_problemas(referencias, metricas_pipeline)

        # Análisis de cobertura
        cobertura = self._analizar_cobertura(referencias)

        # Sugerencias
        sugerencias = self._generar_sugerencias(
            analisis_confianza,
            analisis_validacion,
            problemas,
            cobertura
        )

        # Calificación global
        calificacion = self._calcular_calificacion_global(
            analisis_confianza,
            analisis_validacion,
            cobertura
        )

        informe = {
            'timestamp': datetime.now().isoformat(),
            'total_referencias': len(referencias),
            'calificacion_global': calificacion,
            'analisis_confianza': analisis_confianza,
            'analisis_validacion': analisis_validacion,
            'cobertura': cobertura,
            'problemas_detectados': problemas,
            'sugerencias': sugerencias
        }

        logger.info(f"✅ Auditoría completada - Calificación: {calificacion['nota']}/10")

        return informe

    def _analizar_confianza(self, referencias: List[Dict]) -> Dict[str, Any]:
        """
        Analiza la distribución de confianza

        Returns:
            Dict con análisis de confianza
        """
        if not referencias:
            return {
                'promedio': 0,
                'minima': 0,
                'maxima': 0,
                'distribucion': {'alta': 0, 'media': 0, 'baja': 0},
                'porcentajes': {'alta': 0, 'media': 0, 'baja': 0},
                'referencias_baja_confianza': []
            }

        confianzas = [ref.get('confianza', 0) for ref in referencias]
        promedio = sum(confianzas) / len(confianzas)

        # Clasificar por nivel
        alta = sum(1 for c in confianzas if c >= self.umbrales['confianza_alta'])
        media = sum(1 for c in confianzas if self.umbrales['confianza_media'] <= c < self.umbrales['confianza_alta'])
        baja = sum(1 for c in confianzas if c < self.umbrales['confianza_media'])

        # Referencias de baja confianza (requieren revisión)
        refs_baja_confianza = [
            {
                'texto': ref.get('texto_completo', 'N/A'),
                'confianza': ref.get('confianza', 0),
                'agente': ref.get('_metadata', {}).get('encontrado_por', 'N/A')
            }
            for ref in referencias
            if ref.get('confianza', 0) < self.umbrales['confianza_media']
        ]

        return {
            'promedio': promedio,
            'minima': min(confianzas),
            'maxima': max(confianzas),
            'distribucion': {
                'alta': alta,
                'media': media,
                'baja': baja
            },
            'porcentajes': {
                'alta': alta / len(referencias) * 100,
                'media': media / len(referencias) * 100,
                'baja': baja / len(referencias) * 100
            },
            'referencias_baja_confianza': refs_baja_confianza
        }

    def _analizar_validacion(self, referencias: List[Dict]) -> Dict[str, Any]:
        """
        Analiza el estado de validación

        Returns:
            Dict con análisis de validación
        """
        total = len(referencias)
        if total == 0:
            return {'tasa': 0, 'validadas': 0, 'no_validadas': 0}

        validadas = sum(1 for ref in referencias if ref.get('_validada'))
        no_validadas = total - validadas

        # Referencias no validadas
        refs_no_validadas = [
            {
                'texto': ref.get('texto_completo', 'N/A'),
                'tipo': ref.get('tipo', 'N/A'),
                'motivo': ref.get('_metadata_validacion', {}).get('motivo', 'Desconocido')
            }
            for ref in referencias
            if not ref.get('_validada')
        ]

        # BOE-IDs encontrados
        boe_ids = [
            ref.get('boe_id')
            for ref in referencias
            if ref.get('boe_id')
        ]

        return {
            'validadas': validadas,
            'no_validadas': no_validadas,
            'tasa': validadas / total,
            'porcentaje_validadas': validadas / total * 100,
            'boe_ids_encontrados': len(boe_ids),
            'referencias_no_validadas': refs_no_validadas
        }

    def _analizar_cobertura(self, referencias: List[Dict]) -> Dict[str, Any]:
        """
        Analiza la cobertura de tipos de referencias

        Returns:
            Dict con análisis de cobertura
        """
        # Contar por tipo
        tipos = Counter(ref.get('tipo', 'desconocido') for ref in referencias)

        # Contar por agente
        agentes = Counter(
            ref.get('_metadata', {}).get('encontrado_por', 'desconocido')
            for ref in referencias
        )

        # Contar leyes vs artículos
        leyes = sum(1 for ref in referencias if ref.get('tipo') in ['ley', 'real_decreto', 'sigla'])
        articulos = sum(1 for ref in referencias if ref.get('tipo') == 'articulo')

        return {
            'por_tipo': dict(tipos),
            'por_agente': dict(agentes),
            'leyes': leyes,
            'articulos': articulos,
            'ratio_ley_articulo': leyes / articulos if articulos > 0 else float('inf')
        }

    def _detectar_problemas(
        self,
        referencias: List[Dict],
        metricas_pipeline: Optional[Dict]
    ) -> List[Dict[str, str]]:
        """
        Detecta problemas en el conjunto de referencias

        Returns:
            Lista de problemas detectados
        """
        problemas = []

        # Problema 1: Tasa de validación muy baja
        validadas = sum(1 for ref in referencias if ref.get('_validada'))
        tasa_validacion = validadas / len(referencias) if referencias else 0

        if tasa_validacion < self.umbrales['tasa_validacion_aceptable']:
            problemas.append({
                'severidad': 'alta',
                'tipo': 'validacion_baja',
                'descripcion': f'Tasa de validación muy baja: {tasa_validacion*100:.1f}% (esperado >50%)',
                'accion': 'Revisar manualmente las referencias no validadas o expandir el mapeo de leyes'
            })

        # Problema 2: Muchas referencias de baja confianza
        baja_confianza = sum(
            1 for ref in referencias
            if ref.get('confianza', 0) < self.umbrales['confianza_media']
        )

        if baja_confianza > len(referencias) * 0.3:  # >30%
            problemas.append({
                'severidad': 'media',
                'tipo': 'confianza_baja',
                'descripcion': f'{baja_confianza} referencias con confianza <70% ({baja_confianza/len(referencias)*100:.1f}%)',
                'accion': 'Revisar manualmente las referencias de baja confianza'
            })

        # Problema 3: No se alcanzó convergencia
        if metricas_pipeline and not metricas_pipeline.get('convergencia_alcanzada'):
            problemas.append({
                'severidad': 'media',
                'tipo': 'sin_convergencia',
                'descripcion': 'No se alcanzó convergencia en las rondas permitidas',
                'accion': 'Considerar aumentar el número máximo de rondas o revisar el texto'
            })

        # Problema 4: Pocas referencias encontradas
        if len(referencias) < 5:
            problemas.append({
                'severidad': 'alta',
                'tipo': 'pocas_referencias',
                'descripcion': f'Solo se encontraron {len(referencias)} referencias',
                'accion': 'El tema puede tener pocas referencias legales o los agentes necesitan ajuste'
            })

        # Problema 5: Referencias duplicadas (mismo texto exacto)
        textos = [ref.get('texto_completo', '') for ref in referencias]
        duplicados = len(textos) - len(set(textos))

        if duplicados > 0:
            problemas.append({
                'severidad': 'baja',
                'tipo': 'duplicados',
                'descripcion': f'{duplicados} referencias duplicadas detectadas',
                'accion': 'Revisar el filtrado de duplicados en el sistema de convergencia'
            })

        return problemas

    def _generar_sugerencias(
        self,
        confianza: Dict,
        validacion: Dict,
        problemas: List[Dict],
        cobertura: Dict
    ) -> List[str]:
        """
        Genera sugerencias de mejora

        Returns:
            Lista de sugerencias
        """
        sugerencias = []

        # Basadas en confianza
        if confianza['promedio'] < self.umbrales['confianza_media']:
            sugerencias.append(
                "⚠️ Confianza promedio baja - Considerar revisar manualmente todas las referencias"
            )

        if confianza['distribucion']['baja'] > 0:
            sugerencias.append(
                f"🔍 {confianza['distribucion']['baja']} referencias requieren revisión manual"
            )

        # Basadas en validación
        if validacion['tasa'] < self.umbrales['tasa_validacion_buena']:
            sugerencias.append(
                "📝 Expandir el mapeo de leyes comunes en el BOESearcher para mejorar validación"
            )

        if validacion['no_validadas'] > 0:
            sugerencias.append(
                f"✅ Validar manualmente {validacion['no_validadas']} referencias contra el BOE"
            )

        # Basadas en cobertura
        if cobertura['articulos'] == 0 and cobertura['leyes'] > 0:
            sugerencias.append(
                "🎯 Solo se encontraron leyes, sin artículos específicos - Tema puede ser muy general"
            )

        # Basadas en problemas
        if any(p['severidad'] == 'alta' for p in problemas):
            sugerencias.append(
                "⚠️ Se detectaron problemas de severidad ALTA - Revisión urgente recomendada"
            )

        # Sugerencia general
        if not sugerencias:
            sugerencias.append(
                "✅ La extracción parece correcta - Revisión manual opcional"
            )

        return sugerencias

    def _calcular_calificacion_global(
        self,
        confianza: Dict,
        validacion: Dict,
        cobertura: Dict
    ) -> Dict[str, Any]:
        """
        Calcula una calificación global del 0-10

        Returns:
            Dict con nota y nivel
        """
        # Factores (0-10 cada uno)
        factor_confianza = confianza['promedio'] / 10
        factor_validacion = validacion['tasa'] * 10
        factor_cobertura = min(len(cobertura['por_tipo']), 5) * 2  # Max 5 tipos diferentes

        # Pesos
        peso_confianza = 0.4
        peso_validacion = 0.4
        peso_cobertura = 0.2

        nota = (
            factor_confianza * peso_confianza +
            factor_validacion * peso_validacion +
            factor_cobertura * peso_cobertura
        )

        # Clasificar
        if nota >= 8:
            nivel = "Excelente"
            emoji = "🌟"
        elif nota >= 6:
            nivel = "Bueno"
            emoji = "✅"
        elif nota >= 4:
            nivel = "Aceptable"
            emoji = "⚠️"
        else:
            nivel = "Requiere Revisión"
            emoji = "❌"

        return {
            'nota': round(nota, 1),
            'nivel': nivel,
            'emoji': emoji,
            'factores': {
                'confianza': round(factor_confianza, 1),
                'validacion': round(factor_validacion, 1),
                'cobertura': round(factor_cobertura, 1)
            }
        }

    def generar_informe_texto(self, informe: Dict[str, Any]) -> str:
        """
        Genera un informe en texto formateado

        Args:
            informe: Informe de auditoría

        Returns:
            String con informe formateado
        """
        lineas = []

        lineas.append("=" * 80)
        lineas.append("📊 INFORME DE AUDITORÍA DE REFERENCIAS LEGALES")
        lineas.append("=" * 80)

        # Calificación global
        cal = informe['calificacion_global']
        lineas.append(f"\n{cal['emoji']} CALIFICACIÓN GLOBAL: {cal['nota']}/10 - {cal['nivel']}")

        lineas.append(f"\n📊 Factores:")
        lineas.append(f"   - Confianza: {cal['factores']['confianza']}/10")
        lineas.append(f"   - Validación: {cal['factores']['validacion']}/10")
        lineas.append(f"   - Cobertura: {cal['factores']['cobertura']}/10")

        # Resumen
        lineas.append(f"\n📋 Resumen:")
        lineas.append(f"   - Total referencias: {informe['total_referencias']}")

        # Confianza
        conf = informe['analisis_confianza']
        lineas.append(f"\n🎯 Confianza:")
        lineas.append(f"   - Promedio: {conf['promedio']:.1f}%")
        lineas.append(f"   - Alta (≥90%): {conf['distribucion']['alta']} ({conf['porcentajes']['alta']:.1f}%)")
        lineas.append(f"   - Media (70-89%): {conf['distribucion']['media']} ({conf['porcentajes']['media']:.1f}%)")
        lineas.append(f"   - Baja (<70%): {conf['distribucion']['baja']} ({conf['porcentajes']['baja']:.1f}%)")

        # Validación
        val = informe['analisis_validacion']
        lineas.append(f"\n✅ Validación:")
        lineas.append(f"   - Validadas: {val['validadas']}/{informe['total_referencias']} ({val['porcentaje_validadas']:.1f}%)")
        lineas.append(f"   - BOE-IDs encontrados: {val['boe_ids_encontrados']}")

        # Cobertura
        cob = informe['cobertura']
        lineas.append(f"\n📈 Cobertura:")
        lineas.append(f"   - Tipos encontrados: {list(cob['por_tipo'].keys())}")
        lineas.append(f"   - Leyes: {cob['leyes']}")
        lineas.append(f"   - Artículos: {cob['articulos']}")

        # Problemas
        if informe['problemas_detectados']:
            lineas.append(f"\n⚠️  Problemas Detectados: {len(informe['problemas_detectados'])}")
            for i, prob in enumerate(informe['problemas_detectados'], 1):
                lineas.append(f"\n   {i}. [{prob['severidad'].upper()}] {prob['tipo']}")
                lineas.append(f"      {prob['descripcion']}")
                lineas.append(f"      → {prob['accion']}")

        # Sugerencias
        if informe['sugerencias']:
            lineas.append(f"\n💡 Sugerencias:")
            for sug in informe['sugerencias']:
                lineas.append(f"   {sug}")

        # Referencias que requieren revisión
        if conf['referencias_baja_confianza']:
            lineas.append(f"\n🔍 Referencias que Requieren Revisión Manual:")
            for i, ref in enumerate(conf['referencias_baja_confianza'][:10], 1):
                lineas.append(f"\n   {i}. {ref['texto']} (confianza: {ref['confianza']}%)")
                lineas.append(f"      Encontrado por: {ref['agente']}")

        lineas.append("\n" + "=" * 80)

        return "\n".join(lineas)


# Función helper
def auditar_referencias(
    referencias: List[Dict],
    metricas_pipeline: Dict = None
) -> Dict[str, Any]:
    """
    Función helper para auditar referencias

    Args:
        referencias: Referencias a auditar
        metricas_pipeline: Métricas del pipeline (opcional)

    Returns:
        Informe de auditoría
    """
    auditor = Auditor()
    return auditor.auditar(referencias, metricas_pipeline)


# Ejemplo de uso
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    print("=" * 80)
    print("🧪 TEST DEL AUDITOR")
    print("=" * 80)

    # Referencias de prueba
    referencias_prueba = [
        {
            'texto_completo': 'Ley 39/2015',
            'tipo': 'ley',
            'confianza': 100,
            '_validada': True,
            'boe_id': 'BOE-A-2015-10565',
            '_metadata': {'encontrado_por': 'Agente1A-Conservador'}
        },
        {
            'texto_completo': 'Ley 40/2015',
            'tipo': 'ley',
            'confianza': 100,
            '_validada': True,
            'boe_id': 'BOE-A-2015-10566',
            '_metadata': {'encontrado_por': 'Agente1A-Conservador'}
        },
        {
            'texto_completo': 'Artículo 24 CE',
            'tipo': 'articulo',
            'confianza': 90,
            '_validada': False,
            '_metadata': {'encontrado_por': 'Agente1A-Conservador'},
            '_metadata_validacion': {'motivo': 'No se encontró BOE-ID'}
        },
        {
            'texto_completo': 'legislación notarial',
            'tipo': 'ley',
            'confianza': 60,
            '_validada': False,
            '_metadata': {'encontrado_por': 'Agente1B-Agresivo'},
            '_metadata_validacion': {'motivo': 'Referencia genérica'}
        }
    ]

    metricas = {
        'convergencia_alcanzada': True,
        'total_rondas': 2
    }

    # Auditar
    auditor = Auditor()
    informe = auditor.auditar(referencias_prueba, metricas)

    # Mostrar informe
    texto_informe = auditor.generar_informe_texto(informe)
    print(texto_informe)

    print("\n✅ TEST COMPLETADO")

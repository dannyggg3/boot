"""
AI Response Schemas - Validación de respuestas de IA con Pydantic
==================================================================
Define los esquemas de datos esperados de las respuestas de la IA,
permitiendo validación robusta y reintentos automáticos si falla.

Autor: Trading Bot System
Versión: 1.0
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


class TradingDecision(BaseModel):
    """
    Schema para la decisión de trading de la IA.
    """
    decision: Literal["COMPRA", "VENTA", "ESPERA"] = Field(
        description="Decisión de trading"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Nivel de confianza (0-1)"
    )
    razonamiento: str = Field(
        min_length=5,
        description="Explicación de la decisión"
    )
    stop_loss_sugerido: Optional[float] = Field(
        default=None,
        description="Precio de stop loss sugerido"
    )
    take_profit_sugerido: Optional[float] = Field(
        default=None,
        description="Precio de take profit sugerido"
    )
    tamaño_posicion_sugerido: Optional[float] = Field(
        default=None,
        ge=0.0, le=10,
        description="Tamaño de posición sugerido (% capital)"
    )
    alertas: List[str] = Field(
        default_factory=list,
        description="Lista de alertas o riesgos identificados"
    )

    @field_validator('decision', mode='before')
    @classmethod
    def normalize_decision(cls, v):
        """Normaliza la decisión a mayúsculas."""
        if isinstance(v, str):
            v = v.upper().strip()
            # Mapear variantes comunes
            mapping = {
                'BUY': 'COMPRA',
                'SELL': 'VENTA',
                'HOLD': 'ESPERA',
                'WAIT': 'ESPERA',
                'LONG': 'COMPRA',
                'SHORT': 'VENTA'
            }
            return mapping.get(v, v)
        return v

    @field_validator('stop_loss_sugerido', 'take_profit_sugerido', mode='before')
    @classmethod
    def parse_price(cls, v):
        """Convierte strings a float para precios."""
        if v is None or v == 'N/A' or v == '':
            return None
        if isinstance(v, str):
            try:
                # Remover caracteres no numéricos excepto punto
                cleaned = ''.join(c for c in v if c.isdigit() or c == '.')
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return v

    @field_validator('tamaño_posicion_sugerido', mode='before')
    @classmethod
    def parse_position_size(cls, v):
        """Convierte strings a float para tamaño de posición."""
        if v is None or v == 'N/A' or v == '':
            return None
        if isinstance(v, str):
            try:
                cleaned = ''.join(c for c in v if c.isdigit() or c == '.')
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return v


class QuickFilterDecision(BaseModel):
    """
    Schema para el filtro rápido de oportunidades.
    """
    is_interesting: bool = Field(
        description="Si hay oportunidad técnica interesante"
    )
    signal: Literal["COMPRA", "VENTA", "ESPERA"] = Field(
        description="Señal detectada"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Nivel de confianza"
    )
    reason: str = Field(
        min_length=3,
        description="Razón breve"
    )

    @field_validator('signal', mode='before')
    @classmethod
    def normalize_signal(cls, v):
        """Normaliza la señal."""
        if isinstance(v, str):
            v = v.upper().strip()
            mapping = {
                'BUY': 'COMPRA',
                'SELL': 'VENTA',
                'HOLD': 'ESPERA',
                'WAIT': 'ESPERA'
            }
            return mapping.get(v, v)
        return v


class TrendAgentDecision(TradingDecision):
    """
    Schema para el agente de tendencia.
    """
    tipo_entrada: Optional[str] = Field(
        default=None,
        description="Tipo de entrada detectada"
    )


class ReversalAgentDecision(TradingDecision):
    """
    Schema para el agente de reversión.
    """
    tipo_entrada: Optional[str] = Field(
        default=None,
        description="Tipo de entrada detectada"
    )
    divergencia_detectada: Optional[bool] = Field(
        default=None,
        description="Si se detectó divergencia"
    )


def parse_ai_response_safe(
    response_text: str,
    schema_class: type = TradingDecision,
    fallback_decision: str = "ESPERA"
) -> dict:
    """
    Parsea una respuesta de IA de forma segura usando Pydantic.

    Args:
        response_text: Texto de respuesta de la IA
        schema_class: Clase Pydantic para validación
        fallback_decision: Decisión por defecto si falla el parseo

    Returns:
        Diccionario con la decisión validada
    """
    import json
    import re

    # 1. Intentar extraer JSON de bloques de código markdown
    json_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
    json_blocks = re.findall(json_block_pattern, response_text)

    json_str = None

    # Buscar en bloques de código
    for block in json_blocks:
        block = block.strip()
        if block.startswith('{') and block.endswith('}'):
            try:
                json.loads(block)
                json_str = block
                break
            except json.JSONDecodeError:
                continue

    # 2. Si no se encontró en bloques, buscar JSON raw
    if not json_str:
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.findall(json_pattern, response_text)

        for match in reversed(json_matches):
            try:
                json.loads(match)
                json_str = match
                break
            except json.JSONDecodeError:
                continue

    # 3. Fallback: método simple
    if not json_str:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]

    # 4. Si no se encontró JSON válido
    if not json_str:
        logger.warning("No se encontró JSON en la respuesta de IA")
        return {
            "decision": fallback_decision,
            "confidence": 0.0,
            "razonamiento": "Error: No se pudo extraer JSON de la respuesta",
            "alertas": ["Formato de respuesta inválido"]
        }

    # 5. Validar con Pydantic
    try:
        raw_data = json.loads(json_str)
        validated = schema_class.model_validate(raw_data)
        result = validated.model_dump()
        logger.debug(f"Respuesta IA validada correctamente: {result['decision']}")
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"Error decodificando JSON: {e}")
        return {
            "decision": fallback_decision,
            "confidence": 0.0,
            "razonamiento": f"Error JSON: {str(e)}",
            "alertas": ["JSONDecodeError"]
        }

    except Exception as e:
        logger.warning(f"Error validando respuesta con Pydantic: {e}")
        # Intentar usar los datos raw sin validación estricta
        try:
            raw_data = json.loads(json_str)
            # Normalizar campos básicos
            decision = str(raw_data.get('decision', fallback_decision)).upper()
            if decision not in ['COMPRA', 'VENTA', 'ESPERA']:
                decision = fallback_decision

            return {
                "decision": decision,
                "confidence": float(raw_data.get('confidence', 0.0)),
                "razonamiento": str(raw_data.get('razonamiento', 'N/A')),
                "stop_loss_sugerido": raw_data.get('stop_loss_sugerido'),
                "take_profit_sugerido": raw_data.get('take_profit_sugerido'),
                "alertas": raw_data.get('alertas', [f"Validación parcial: {str(e)}"])
            }
        except:
            return {
                "decision": fallback_decision,
                "confidence": 0.0,
                "razonamiento": f"Error validación: {str(e)}",
                "alertas": ["ValidationError"]
            }


if __name__ == "__main__":
    # Pruebas del módulo
    logging.basicConfig(level=logging.INFO)

    # Test 1: Respuesta válida
    test_response = '''
    ```json
    {
        "decision": "COMPRA",
        "confidence": 0.85,
        "razonamiento": "RSI sobrevendido con divergencia alcista",
        "stop_loss_sugerido": 95000,
        "take_profit_sugerido": 102000,
        "alertas": ["Volumen bajo"]
    }
    ```
    '''

    result = parse_ai_response_safe(test_response)
    print("Test 1 (válido):", result)

    # Test 2: Respuesta con errores
    test_response_2 = '''
    {
        "decision": "buy",
        "confidence": "0.7",
        "razonamiento": "Tendencia alcista"
    }
    '''

    result_2 = parse_ai_response_safe(test_response_2)
    print("Test 2 (normalizado):", result_2)

    # Test 3: Respuesta inválida
    test_response_3 = "No puedo analizar esto porque..."

    result_3 = parse_ai_response_safe(test_response_3)
    print("Test 3 (fallback):", result_3)

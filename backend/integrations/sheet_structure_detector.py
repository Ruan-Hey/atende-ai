"""
Detector automático de estrutura de planilhas
Mapeia colunas dinamicamente baseado nos cabeçalhos
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import gspread

logger = logging.getLogger(__name__)

class SheetStructureDetector:
    """Detecta automaticamente a estrutura de uma planilha"""
    
    def __init__(self):
        # Mapeamento de palavras-chave para tipos de coluna
        # ORDEM É IMPORTANTE: colunas específicas primeiro, genéricas depois
        self.column_keywords = {
            'horario': ['horario', 'hora', 'time', 'hour'],
            'pessoas': ['pessoas', 'people', 'convidados', 'guests', 'quantidade', 'qtd', 'qty'],
            'observacoes': ['observacoes', 'obs', 'observations', 'notes', 'comentarios', 'comments'],
            'ultima_alteracao': ['ultima alteracao', 'last change', 'modificado', 'modified', 'atualizado', 'updated'],
            'waid': ['telefone', 'whatsapp', 'waid', 'phone', 'celular', 'mobile', 'id', 'identificador'],
            'data': ['data', 'date', 'dia', 'day'],
            'nome': ['nome', 'cliente', 'customer', 'client', 'person']  # Removido 'pessoa' para evitar conflito
        }
    
    def detect_structure(self, worksheet: gspread.Worksheet) -> Dict[str, Any]:
        """Detecta automaticamente a estrutura da planilha"""
        try:
            # Obter cabeçalhos da primeira linha
            headers = worksheet.row_values(1)
            logger.info(f"Cabeçalhos detectados: {headers}")
            
            # Mapear colunas baseado nos cabeçalhos
            column_mapping = {}
            required_columns = []
            
            for col_index, header in enumerate(headers):
                if not header:  # Pular colunas vazias
                    continue
                    
                header_lower = header.lower().strip()
                column_letter = self._get_column_letter(col_index)
                
                # Mapear coluna baseado em palavras-chave
                column_type = self._identify_column_type(header_lower)
                
                if column_type:
                    column_mapping[column_type] = {
                        'index': col_index,
                        'letter': column_letter,
                        'header': header,
                        'original_name': header
                    }
                    
                    # Marcar WaId como obrigatório
                    if column_type == 'waid':
                        required_columns.append('waid')
                        logger.info(f"✅ Coluna WaId detectada: {header} ({column_letter})")
                    else:
                        logger.info(f"📋 Coluna {column_type} detectada: {header} ({column_letter})")
            
            # Verificar se WaId está presente (obrigatório)
            if 'waid' not in column_mapping:
                logger.error("❌ Coluna WaId não encontrada! Esta coluna é obrigatória.")
                raise ValueError("Coluna WaId (telefone/whatsapp) é obrigatória na planilha")
            
            # Verificar colunas essenciais
            essential_columns = ['nome', 'data', 'horario']
            missing_essential = [col for col in essential_columns if col not in column_mapping]
            
            if missing_essential:
                logger.warning(f"⚠️ Colunas essenciais não encontradas: {missing_essential}")
            
            structure = {
                'column_mapping': column_mapping,
                'required_columns': required_columns,
                'total_columns': len(headers),
                'detection_success': True
            }
            
            logger.info(f"✅ Estrutura da planilha detectada com sucesso: {len(column_mapping)} colunas mapeadas")
            return structure
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar estrutura da planilha: {e}")
            return {
                'column_mapping': {},
                'required_columns': [],
                'total_columns': 0,
                'detection_success': False,
                'error': str(e)
            }
    
    def _identify_column_type(self, header: str) -> Optional[str]:
        """Identifica o tipo de coluna baseado no cabeçalho"""
        header_lower = header.lower().strip()
        
        # Buscar correspondências exatas primeiro
        for column_type, keywords in self.column_keywords.items():
            for keyword in keywords:
                if keyword == header_lower:  # Correspondência exata
                    return column_type
        
        # Se não encontrar correspondência exata, buscar parcial
        for column_type, keywords in self.column_keywords.items():
            for keyword in keywords:
                if keyword in header_lower:  # Correspondência parcial
                    return column_type
        
        return None
    
    def _get_column_letter(self, col_index: int) -> str:
        """Converte índice da coluna para letra (A, B, C, etc.)"""
        result = ""
        while col_index >= 0:
            col_index, remainder = divmod(col_index, 26)
            result = chr(65 + remainder) + result
            col_index -= 1
        return result
    
    def validate_structure(self, structure: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Valida se a estrutura detectada é válida"""
        errors = []
        
        if not structure.get('detection_success'):
            errors.append("Falha na detecção da estrutura")
            return False, errors
        
        # WaId é obrigatório
        if 'waid' not in structure['column_mapping']:
            errors.append("Coluna WaId (telefone/whatsapp) é obrigatória")
        
        # Nome é altamente recomendado
        if 'nome' not in structure['column_mapping']:
            errors.append("Coluna Nome é altamente recomendada")
        
        # Data e horário são essenciais para reservas
        if 'data' not in structure['column_mapping']:
            errors.append("Coluna Data é essencial para reservas")
        
        if 'horario' not in structure['column_mapping']:
            errors.append("Coluna Horário é essencial para reservas")
        
        return len(errors) == 0, errors
    
    def get_column_info(self, structure: Dict[str, Any], column_type: str) -> Optional[Dict[str, Any]]:
        """Obtém informações de uma coluna específica"""
        return structure.get('column_mapping', {}).get(column_type)
    
    def get_required_columns(self, structure: Dict[str, Any]) -> List[str]:
        """Retorna lista de colunas obrigatórias"""
        return structure.get('required_columns', [])
    
    def is_column_present(self, structure: Dict[str, Any], column_type: str) -> bool:
        """Verifica se uma coluna está presente"""
        return column_type in structure.get('column_mapping', {})

# Instância global do detector
sheet_structure_detector = SheetStructureDetector() 
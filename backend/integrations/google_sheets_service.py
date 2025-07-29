import gspread
from google.oauth2.service_account import Credentials
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Serviço para integração com Google Sheets"""
    
    def __init__(self, credentials_path: str):
        # Configurar escopo para Google Sheets
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Carregar credenciais
        self.creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
        self.client = gspread.authorize(self.creds)
    
    def get_spreadsheet(self, spreadsheet_id: str):
        """Abre uma planilha específica"""
        try:
            return self.client.open_by_key(spreadsheet_id)
        except Exception as e:
            logger.error(f"Erro ao abrir planilha {spreadsheet_id}: {e}")
            raise
    
    def add_reserva(self, spreadsheet_id: str, reserva_data: Dict[str, Any]) -> bool:
        """Adiciona uma nova reserva à planilha"""
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1  # Primeira aba
            
            # Preparar dados da reserva
            row_data = [
                reserva_data.get('nome', ''),
                reserva_data.get('telefone', ''),
                reserva_data.get('data', ''),
                reserva_data.get('horario', ''),
                reserva_data.get('pessoas', ''),
                reserva_data.get('observacoes', ''),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Data de criação
            ]
            
            # Adicionar linha
            worksheet.append_row(row_data)
            
            logger.info(f"Reserva adicionada: {reserva_data.get('nome')}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar reserva: {e}")
            return False
    
    def update_reserva(self, spreadsheet_id: str, nome: str, reserva_data: Dict[str, Any]) -> bool:
        """Atualiza uma reserva existente"""
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Encontrar linha com o nome
            try:
                cell = worksheet.find(nome)
                row_number = cell.row
                
                # Atualizar dados
                worksheet.update(f'A{row_number}', reserva_data.get('nome', ''))
                worksheet.update(f'B{row_number}', reserva_data.get('telefone', ''))
                worksheet.update(f'C{row_number}', reserva_data.get('data', ''))
                worksheet.update(f'D{row_number}', reserva_data.get('horario', ''))
                worksheet.update(f'E{row_number}', reserva_data.get('pessoas', ''))
                worksheet.update(f'F{row_number}', reserva_data.get('observacoes', ''))
                worksheet.update(f'G{row_number}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                logger.info(f"Reserva atualizada: {nome}")
                return True
                
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada: {nome}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao atualizar reserva: {e}")
            return False
    
    def cancel_reserva(self, spreadsheet_id: str, nome: str) -> bool:
        """Cancela uma reserva (marca como cancelada)"""
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Encontrar linha com o nome
            try:
                cell = worksheet.find(nome)
                row_number = cell.row
                
                # Marcar como cancelada
                worksheet.update(f'C{row_number}', 'Cancelado')
                worksheet.update(f'D{row_number}', 'Cancelado')
                worksheet.update(f'E{row_number}', 'Cancelado')
                worksheet.update(f'F{row_number}', 'Cancelado')
                worksheet.update(f'G{row_number}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                
                logger.info(f"Reserva cancelada: {nome}")
                return True
                
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada para cancelar: {nome}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return False
    
    def get_reservas(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Retorna todas as reservas da planilha"""
        try:
            spreadsheet = self.get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Pegar todos os dados
            all_values = worksheet.get_all_values()
            
            if len(all_values) < 2:  # Só cabeçalho ou vazio
                return []
            
            # Pular cabeçalho
            reservas = []
            for row in all_values[1:]:
                if len(row) >= 7:  # Verificar se tem dados suficientes
                    reserva = {
                        'nome': row[0],
                        'telefone': row[1],
                        'data': row[2],
                        'horario': row[3],
                        'pessoas': row[4],
                        'observacoes': row[5],
                        'ultima_alteracao': row[6]
                    }
                    reservas.append(reserva)
            
            return reservas
            
        except Exception as e:
            logger.error(f"Erro ao buscar reservas: {e}")
            return [] 
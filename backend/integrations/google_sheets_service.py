import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Serviço para integração com Google Sheets
    
    Aceita um dicionário de configuração e autentica via:
    - Service Account (arquivo ou dict)
    - OAuth2 (client_id, client_secret, refresh_token)
    
    Se não houver credenciais válidas, permanece inativo (sem lançar exceção).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.client: Optional[gspread.Client] = None
        self.spreadsheet_id: Optional[str] = self.config.get("google_sheets_id")
        
        # Escopos necessários para Sheets/Drive
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        
        try:
            # 1) Service Account via caminho de arquivo, se fornecido
            credentials_path = self.config.get("google_sheets_credentials_path")
            if credentials_path:
                creds = ServiceAccountCredentials.from_service_account_file(
                    credentials_path, scopes=self.scopes
                )
                self.client = gspread.authorize(creds)
                logger.info("Google Sheets autenticado via Service Account (arquivo)")
                return
            
            # 2) Service Account via dict JSON, se fornecido
            service_account_info = self.config.get("google_sheets_service_account")
            if isinstance(service_account_info, dict) and service_account_info:
                creds = ServiceAccountCredentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
                self.client = gspread.authorize(creds)
                logger.info("Google Sheets autenticado via Service Account (dict)")
                return
            
            # 3) OAuth2 usando refresh token
            # Primeiro tenta credenciais específicas do Google Sheets
            sheets_client_id = self.config.get("google_sheets_client_id")
            sheets_client_secret = self.config.get("google_sheets_client_secret")
            sheets_refresh_token = self.config.get("google_sheets_refresh_token")
            
            # Mantém compatibilidade usando credenciais do Calendar se existirem
            calendar_client_id = self.config.get("google_calendar_client_id")
            calendar_client_secret = self.config.get("google_calendar_client_secret")
            calendar_refresh_token = self.config.get("google_calendar_refresh_token")
            
            client_id = sheets_client_id or calendar_client_id
            client_secret = sheets_client_secret or calendar_client_secret
            refresh_token = sheets_refresh_token or calendar_refresh_token
            
            if client_id and client_secret and refresh_token:
                creds = UserCredentials(
                    None,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=self.scopes,
                )
                creds.refresh(Request())
                self.client = gspread.authorize(creds)
                source = "Sheets" if sheets_refresh_token else "Calendar"
                logger.info(f"Google Sheets autenticado via OAuth2 (refresh token, origem: {source})")
                return
            
            logger.warning(
                "Google Sheets não configurado: faltam credenciais (Service Account ou OAuth2)"
            )
        except Exception as e:
            logger.warning(f"Falha ao autenticar Google Sheets: {e}")
            self.client = None

    # ------------------------
    # Métodos utilitários base
    # ------------------------
    def _get_spreadsheet(self, spreadsheet_id: Optional[str] = None):
        if not self.client:
            raise RuntimeError("Google Sheets não autenticado")
        key = spreadsheet_id or self.spreadsheet_id
        if not key:
            raise RuntimeError("google_sheets_id não configurado")
        return self.client.open_by_key(key)

    # ---------------------------------
    # API de alto nível usada pelo bot
    # ---------------------------------
    def add_reservation(self, data: str, hora: str, cliente: str, empresa: str) -> bool:
        """Adiciona uma reserva simples usando `google_sheets_id` da config.
        Compatível com chamada em `calendar_tools`.
        """
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.sheet1
            row_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                empresa,
                cliente,
                data,
                hora,
                "",
                "Criado via bot",
            ]
            worksheet.append_row(row_data, value_input_option="RAW")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar reserva no Google Sheets: {e}")
            return False

    # ---------------------------------
    # Métodos legados (compatibilidade)
    # ---------------------------------
    def get_spreadsheet(self, spreadsheet_id: str):
        """Mantido para compatibilidade com código legado."""
        try:
            return self._get_spreadsheet(spreadsheet_id)
        except Exception as e:
            logger.error(f"Erro ao abrir planilha {spreadsheet_id}: {e}")
            raise
    
    def add_reserva(self, spreadsheet_id: str, reserva_data: Dict[str, Any]) -> bool:
        """Adiciona nova reserva usando detecção automática de estrutura."""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Detectar estrutura da planilha automaticamente
            from .sheet_structure_detector import sheet_structure_detector
            structure = sheet_structure_detector.detect_structure(worksheet)
            
            if not structure.get('detection_success'):
                logger.error(f"Falha na detecção da estrutura: {structure.get('error')}")
                return False
            
            # Validar estrutura
            is_valid, errors = sheet_structure_detector.validate_structure(structure)
            if not is_valid:
                logger.error(f"Estrutura da planilha inválida: {errors}")
                return False
            
            # Criar linha baseada na estrutura detectada
            row_data = self._create_row_from_structure(structure, reserva_data)
            
            # Adicionar linha à planilha
            worksheet.append_row(row_data)
            logger.info(f"✅ Reserva adicionada com sucesso: {reserva_data.get('nome')}")
            logger.info(f"📊 Estrutura detectada: {len(structure['column_mapping'])} colunas")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao adicionar reserva: {e}")
            return False
    
    def _create_row_from_structure(self, structure: Dict[str, Any], reserva_data: Dict[str, Any]) -> List[str]:
        """Cria linha de dados baseada na estrutura detectada"""
        column_mapping = structure['column_mapping']
        total_columns = structure['total_columns']
        
        # Inicializar linha com valores vazios
        row_data = [''] * total_columns
        
        # Mapear dados para as colunas corretas
        for column_type, column_info in column_mapping.items():
            col_index = column_info['index']
            
            if column_type == 'nome':
                row_data[col_index] = reserva_data.get('nome', '')
            elif column_type == 'waid':
                row_data[col_index] = reserva_data.get('waid', '')
            elif column_type == 'data':
                row_data[col_index] = reserva_data.get('data', '')
            elif column_type == 'horario':
                row_data[col_index] = reserva_data.get('horario', '')
            elif column_type == 'pessoas':
                row_data[col_index] = str(reserva_data.get('pessoas', '')) if reserva_data.get('pessoas') else ''
            elif column_type == 'observacoes':
                row_data[col_index] = reserva_data.get('observacoes', '')
            elif column_type == 'ultima_alteracao':
                row_data[col_index] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"📝 Linha criada: {row_data}")
        return row_data
    
    def update_reserva(self, spreadsheet_id: str, waid: str, reserva_data: Dict[str, Any]) -> bool:
        """Atualiza reserva usando WaId (obrigatório) e estrutura detectada"""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Detectar estrutura da planilha
            from .sheet_structure_detector import sheet_structure_detector
            structure = sheet_structure_detector.detect_structure(worksheet)
            
            if not structure.get('detection_success'):
                logger.error(f"Falha na detecção da estrutura: {structure.get('error')}")
                return False
            
            # Buscar por WaId (coluna obrigatória)
            waid_column_info = structure['column_mapping'].get('waid')
            if not waid_column_info:
                logger.error("Coluna WaId não encontrada para busca")
                return False
            
            try:
                # Buscar célula com o WaId
                cell = worksheet.find(waid)
                row_number = cell.row
                
                # Atualizar cada coluna baseado na estrutura detectada
                for column_type, column_info in structure['column_mapping'].items():
                    if column_type == 'ultima_alteracao':
                        # Sempre atualizar timestamp de modificação
                        worksheet.update(f"{column_info['letter']}{row_number}", 
                                      datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    elif column_type in reserva_data:
                        # Atualizar dados fornecidos
                        worksheet.update(f"{column_info['letter']}{row_number}", 
                                      reserva_data[column_type])
                
                logger.info(f"✅ Reserva atualizada com sucesso: WaId {waid}")
                return True
                
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada com WaId: {waid}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao atualizar reserva: {e}")
            return False
    
    def cancel_reserva(self, spreadsheet_id: str, waid: str) -> bool:
        """Cancela reserva usando WaId (obrigatório) e estrutura detectada"""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Detectar estrutura da planilha
            from .sheet_structure_detector import sheet_structure_detector
            structure = sheet_structure_detector.detect_structure(worksheet)
            
            if not structure.get('detection_success'):
                logger.error(f"Falha na detecção da estrutura: {structure.get('error')}")
                return False
            
            # Buscar por WaId (coluna obrigatória)
            waid_column_info = structure['column_mapping'].get('waid')
            if not waid_column_info:
                logger.error("Coluna WaId não encontrada para busca")
                return False
            
            try:
                # Buscar célula com o WaId
                cell = worksheet.find(waid)
                row_number = cell.row
                
                # Marcar como cancelado nas colunas relevantes
                cancel_columns = ['data', 'horario', 'pessoas', 'observacoes']
                for column_type in cancel_columns:
                    if column_type in structure['column_mapping']:
                        column_info = structure['column_mapping'][column_type]
                        worksheet.update(f"{column_info['letter']}{row_number}", "Cancelado")
                
                # Atualizar timestamp de modificação
                if 'ultima_alteracao' in structure['column_mapping']:
                    ultima_col = structure['column_mapping']['ultima_alteracao']
                    worksheet.update(f"{ultima_col['letter']}{row_number}", 
                                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                logger.info(f"✅ Reserva cancelada com sucesso: WaId {waid}")
                return True
                
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada com WaId para cancelar: {waid}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return False
    
    def buscar_reserva_por_waid(self, spreadsheet_id: str, waid: str) -> Optional[Dict[str, Any]]:
        """Busca reserva específica por WaId usando estrutura detectada"""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Detectar estrutura da planilha
            from .sheet_structure_detector import sheet_structure_detector
            structure = sheet_structure_detector.detect_structure(worksheet)
            
            if not structure.get('detection_success'):
                logger.error(f"Falha na detecção da estrutura: {structure.get('error')}")
                return None
            
            # Buscar por WaId (coluna obrigatória)
            waid_column_info = structure['column_mapping'].get('waid')
            if not waid_column_info:
                logger.error("Coluna WaId não encontrada para busca")
                return None
            
            try:
                # Buscar célula com o WaId
                cell = worksheet.find(waid)
                row_number = cell.row
                
                # Obter dados da linha
                row_data = worksheet.row_values(row_number)
                if len(row_data) < len(structure['column_mapping']):
                    logger.warning(f"Dados insuficientes na linha {row_number}")
                    return None
                
                # Mapear dados baseado na estrutura detectada
                reserva = {}
                for column_type, column_info in structure['column_mapping'].items():
                    col_index = column_info['index']
                    if col_index < len(row_data):
                        reserva[column_type] = row_data[col_index]
                
                logger.info(f"✅ Reserva encontrada com WaId {waid}: {reserva.get('nome', 'N/A')}")
                return reserva
                
            except gspread.CellNotFound:
                logger.info(f"Reserva não encontrada com WaId: {waid}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar reserva por WaId: {e}")
            return None
    
    def get_reservas(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Busca reservas usando estrutura detectada automaticamente"""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            
            # Detectar estrutura da planilha
            from .sheet_structure_detector import sheet_structure_detector
            structure = sheet_structure_detector.detect_structure(worksheet)
            
            if not structure.get('detection_success'):
                logger.error(f"Falha na detecção da estrutura: {structure.get('error')}")
                return []
            
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                return []
            
            reservas: List[Dict[str, Any]] = []
            column_mapping = structure['column_mapping']
            
            for row in all_values[1:]:  # Pular cabeçalho
                if len(row) >= len(column_mapping):
                    reserva = {}
                    
                    # Mapear dados baseado na estrutura detectada
                    for column_type, column_info in column_mapping.items():
                        col_index = column_info['index']
                        if col_index < len(row):
                            reserva[column_type] = row[col_index]
                    
                    reservas.append(reserva)
            
            logger.info(f"✅ {len(reservas)} reservas encontradas usando estrutura detectada")
            return reservas
            
        except Exception as e:
            logger.error(f"Erro ao buscar reservas: {e}")
            return []
    
    def read_data(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                return []
            headers = all_values[0]
            data: List[Dict[str, Any]] = []
            for row in all_values[1:]:
                row_dict: Dict[str, Any] = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = value
                data.append(row_dict)
            return data
        except Exception as e:
            logger.error(f"Erro ao ler dados da planilha: {e}")
            return []
    
    def write_data(self, spreadsheet_id: str, data: List[Dict[str, Any]]) -> bool:
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            if not data:
                return False
            all_values = worksheet.get_all_values()
            if len(all_values) > 1:
                worksheet.delete_rows(2, len(all_values))
            headers = list(data[0].keys())
            rows = [headers]
            for item in data:
                row = [str(item.get(header, "")) for header in headers]
                rows.append(row)
            worksheet.update("A1", rows)
            logger.info(f"Dados escritos na planilha: {len(data)} registros")
            return True
        except Exception as e:
            logger.error(f"Erro ao escrever dados na planilha: {e}")
            return False 
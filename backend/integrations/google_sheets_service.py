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
        """Assinatura antiga: adiciona nova reserva à planilha informada."""
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            row_data = [
                reserva_data.get("nome", ""),
                reserva_data.get("telefone", ""),
                reserva_data.get("data", ""),
                reserva_data.get("horario", ""),
                reserva_data.get("pessoas", ""),
                reserva_data.get("observacoes", ""),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            worksheet.append_row(row_data)
            logger.info(f"Reserva adicionada: {reserva_data.get('nome')}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar reserva: {e}")
            return False
    
    def update_reserva(self, spreadsheet_id: str, nome: str, reserva_data: Dict[str, Any]) -> bool:
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            try:
                cell = worksheet.find(nome)
                row_number = cell.row
                worksheet.update(f"A{row_number}", reserva_data.get("nome", ""))
                worksheet.update(f"B{row_number}", reserva_data.get("telefone", ""))
                worksheet.update(f"C{row_number}", reserva_data.get("data", ""))
                worksheet.update(f"D{row_number}", reserva_data.get("horario", ""))
                worksheet.update(f"E{row_number}", reserva_data.get("pessoas", ""))
                worksheet.update(f"F{row_number}", reserva_data.get("observacoes", ""))
                worksheet.update(
                    f"G{row_number}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                logger.info(f"Reserva atualizada: {nome}")
                return True
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada: {nome}")
                return False
        except Exception as e:
            logger.error(f"Erro ao atualizar reserva: {e}")
            return False
    
    def cancel_reserva(self, spreadsheet_id: str, nome: str) -> bool:
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            try:
                cell = worksheet.find(nome)
                row_number = cell.row
                worksheet.update(f"C{row_number}", "Cancelado")
                worksheet.update(f"D{row_number}", "Cancelado")
                worksheet.update(f"E{row_number}", "Cancelado")
                worksheet.update(f"F{row_number}", "Cancelado")
                worksheet.update(
                    f"G{row_number}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                logger.info(f"Reserva cancelada: {nome}")
                return True
            except gspread.CellNotFound:
                logger.warning(f"Reserva não encontrada para cancelar: {nome}")
                return False
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return False
    
    def get_reservas(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        try:
            spreadsheet = self._get_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.sheet1
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                return []
            reservas: List[Dict[str, Any]] = []
            for row in all_values[1:]:
                if len(row) >= 7:
                    reservas.append(
                        {
                            "nome": row[0],
                            "telefone": row[1],
                            "data": row[2],
                            "horario": row[3],
                            "pessoas": row[4],
                            "observacoes": row[5],
                            "ultima_alteracao": row[6],
                    }
                    )
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
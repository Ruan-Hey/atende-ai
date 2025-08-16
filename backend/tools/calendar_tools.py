from typing import Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from integrations.google_calendar_service import GoogleCalendarService
from integrations.google_sheets_service import GoogleSheetsService
from .api_tools import APITools
import logging

logger = logging.getLogger(__name__)

class CalendarTools:
    """Ferramentas para operações de calendário e reservas"""
    
    def __init__(self):
        self.calendar_service = None
        self.sheets_service = None
        self.api_tools = APITools()
    
    def _get_calendar_service(self, empresa_config: Dict[str, Any]) -> GoogleCalendarService:
        """Inicializa serviço do Google Calendar"""
        if not self.calendar_service:
            # Criar configuração para o Google Calendar Service
            calendar_config = {
                'google_calendar_enabled': True,
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token'),
                'google_calendar_service_account': empresa_config.get('google_calendar_service_account'),
                'google_calendar_project_id': empresa_config.get('google_calendar_project_id'),
                'google_calendar_client_email': empresa_config.get('google_calendar_client_email'),
                'google_calendar_calendar_id': empresa_config.get('google_calendar_calendar_id', 'primary'),
                'google_sheets_id': empresa_config.get('google_sheets_id')
            }
            
            self.calendar_service = GoogleCalendarService(calendar_config)
        return self.calendar_service
    
    def _get_sheets_service(self, empresa_config: Dict[str, Any]) -> GoogleSheetsService | None:
        """Inicializa serviço do Google Sheets somente se houver ID configurado"""
        if not empresa_config.get('google_sheets_id'):
            return None
        if not self.sheets_service:
            # Criar configuração para o Google Sheets Service
            sheets_config = {
                'google_sheets_id': empresa_config.get('google_sheets_id'),
                # Preferir credenciais específicas do Sheets se existirem
                'google_sheets_client_id': empresa_config.get('google_sheets_client_id'),
                'google_sheets_client_secret': empresa_config.get('google_sheets_client_secret'),
                'google_sheets_refresh_token': empresa_config.get('google_sheets_refresh_token'),
                # Manter compatibilidade reutilizando credenciais do Calendar
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_calendar_refresh_token': empresa_config.get('google_calendar_refresh_token')
            }
            
            try:
                self.sheets_service = GoogleSheetsService(sheets_config)
            except Exception as e:
                logger.warning(f"Sheets desabilitado ou não configurado corretamente: {e}")
                self.sheets_service = None
        return self.sheets_service
    
    def _find_calendar_api(self, empresa_config: Dict[str, Any]) -> tuple[str, dict]:
        """Encontra a primeira API de agenda disponível"""
        # Verificar Google Calendar primeiro
        if (empresa_config.get('google_calendar_client_id') and 
            empresa_config.get('google_calendar_client_secret')):
            return "Google Calendar", {
                'google_calendar_client_id': empresa_config.get('google_calendar_client_id'),
                'google_calendar_client_secret': empresa_config.get('google_calendar_client_secret'),
                'google_sheets_id': empresa_config.get('google_sheets_id')
            }
        
        # Verificar Google Sheets como alternativa para reservas
        if (empresa_config.get('google_sheets_id') and 
            (empresa_config.get('google_sheets_client_id') or empresa_config.get('google_sheets_service_account'))):
            return "Google Sheets", {
                'google_sheets_id': empresa_config.get('google_sheets_id'),
                'google_sheets_client_id': empresa_config.get('google_sheets_client_id'),
                'google_sheets_client_secret': empresa_config.get('google_sheets_client_secret'),
                'google_sheets_refresh_token': empresa_config.get('google_sheets_refresh_token'),
                'google_sheets_service_account': empresa_config.get('google_sheets_service_account')
            }
        
        # Verificar Trinks
        if empresa_config.get('trinks_enabled') and empresa_config.get('trinks_api_key'):
            return "Trinks", {
                'api_key': empresa_config.get('trinks_api_key'),
                'base_url': empresa_config.get('trinks_base_url'),
                'estabelecimento_id': empresa_config.get('trinks_estabelecimento_id')
            }
        
        # Verificar outras APIs de agenda dinamicamente
        for key, value in empresa_config.items():
            if key.endswith('_enabled') and value is True:
                api_name = key.replace('_enabled', '').replace('_', ' ').title()
                config_key = f"{key.replace('_enabled', '')}_config"
                config = empresa_config.get(config_key, {})
                
                # Verificar se é uma API de agenda (por nome ou configuração)
                if any(word in api_name.lower() for word in ['calendar', 'agenda', 'booking', 'schedule', 'trinks']):
                    return api_name, config
        
        return None, {}
    
    def verificar_disponibilidade(self, data: str, empresa_config: Dict[str, Any], contexto_reserva: Dict[str, Any] = None, mensagem: str = None) -> str:
        """Verifica disponibilidade usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "Nenhuma API de agenda configurada para esta empresa. Não posso verificar disponibilidade."
            
            # Validar formato da data
            try:
                from datetime import datetime
                datetime.strptime(data, '%Y-%m-%d')
            except ValueError:
                return f"Formato de data inválido: {data}. Use o formato YYYY-MM-DD (ex: 2024-01-15)"
            
            # Usar API específica ou genérica
            if api_name == "Google Calendar":
                return self._verificar_google_calendar(data, empresa_config)
            elif api_name == "Google Sheets":
                return self._verificar_google_sheets(data, empresa_config, api_config)
            elif api_name == "Trinks":
                # Passar empresa_config e contexto para usar ferramentas inteligentes
                return self._verificar_trinks(data, api_config, empresa_config, contexto_reserva=contexto_reserva or {}, mensagem=mensagem)
            else:
                return self._verificar_api_generica(api_name, data, api_config)
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            return f"Erro ao verificar disponibilidade para {data}: {str(e)}"
    
    def _verificar_google_calendar(self, data: str, empresa_config: Dict[str, Any]) -> str:
        """Verifica disponibilidade no Google Calendar"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            slots = calendar_service.get_available_slots(data)
            
            # Logar slots para diagnóstico
            try:
                import logging
                logging.getLogger(__name__).info(f"Calendar slots for {data}: {slots}")
            except Exception:
                pass
            
            if not slots:
                return f"Não há horários disponíveis para {data}. Tente outra data."
            
            slots_info = "\n".join([f"- {slot}" for slot in slots[:10]])
            return f"Horários disponíveis no Google Calendar para {data}:\n{slots_info}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar Google Calendar: {e}")
            return f"Erro ao verificar Google Calendar para {data}: {str(e)}"
    
    def _verificar_google_sheets(self, data: str, empresa_config: Dict[str, Any], api_config: Dict[str, Any]) -> str:
        """Verifica disponibilidade no Google Sheets (sempre retorna disponível)"""
        try:
            # Para Google Sheets, sempre retornamos que está disponível
            # já que não temos lógica de verificação de conflitos implementada
            return f"✅ Horários disponíveis para {data} no Google Sheets.\nA planilha está configurada para receber reservas."
            
        except Exception as e:
            logger.error(f"Erro ao verificar Google Sheets: {e}")
            return f"Erro ao verificar Google Sheets para {data}: {str(e)}"
    
    def _verificar_trinks(self, data: str, config: Dict[str, Any], empresa_config: Dict[str, Any], contexto_reserva: Dict[str, Any] = None, mensagem: str = None) -> str:
        """Verifica disponibilidade na API Trinks usando ferramentas inteligentes"""
        try:
            # Importar ferramentas inteligentes
            from .trinks_intelligent_tools import trinks_intelligent_tools
            
            # MODO THIN: retornar o JSON bruto de disponibilidade por data, sem regras extras
            try:
                import json as _json
                from .api_tools import APITools
                logger.info("THIN: retornando JSON bruto de disponibilidade Trinks")
                endpoint = "/agendamentos/profissionais/{data}".replace("{data}", data)
                params = {
                    'estabelecimentoId': empresa_config.get('trinks_estabelecimento_id') or empresa_config.get('estabelecimentoId')
                }
                raw = APITools().call_api(
                    api_name="Trinks",
                    endpoint_path=endpoint,
                    method="GET",
                    config=empresa_config.get('trinks_config', empresa_config),
                    **params
                )
                if isinstance(raw, str):
                    if raw.strip().startswith("Sucesso na operação"):
                        i = raw.find('{')
                        result_data = _json.loads(raw[i:]) if i != -1 else {}
                    else:
                        result_data = _json.loads(raw)
                else:
                    result_data = raw or {}
                return _json.dumps(result_data, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"THIN: falha ao retornar JSON bruto: {e}")
                import json as _json
                return _json.dumps({'error': 'thin_mode_failed', 'message': str(e), 'data': []}, ensure_ascii=False)

            # Verificar se temos configuração da empresa
            # empresa_config = getattr(self, 'empresa_config', None) # This line is removed as per the edit hint
            
            # Usar ferramentas inteligentes se disponível
            try:
                # 1) Se vier mensagem, tentar detectar serviço pela conversa
                detected_service_id = None
                if mensagem:
                    try:
                        det = trinks_intelligent_tools.detect_service_from_conversation(mensagem, empresa_config)
                        if det.get('detected') and det.get('service_id'):
                            detected_service_id = det.get('service_id')
                    except Exception:
                        pass

                # 2) Caso ainda não tenha, tentar usar contexto_reserva (ex.: nome do serviço)
                if not detected_service_id and contexto_reserva:
                    servico_ctx = (contexto_reserva.get('servico') or contexto_reserva.get('service') or '').strip()
                    if servico_ctx:
                        det2 = trinks_intelligent_tools._search_service_in_api(servico_ctx, empresa_config)
                        if det2.get('detected') and det2.get('service_id'):
                            detected_service_id = det2.get('service_id')

                # 3) Opcional: tentar encontrar profissional pelo serviço (pode filtrar por Amabile no futuro)
                professional_id = None
                if detected_service_id:
                    try:
                        profs = trinks_intelligent_tools.find_professionals_for_service(str(detected_service_id), empresa_config)
                        # Se houver contexto com nome da doutora, tentar filtrar
                        nome_prof_ctx = (contexto_reserva or {}).get('profissional_nome') or ''
                        if profs.get('found') and isinstance(profs.get('professionals'), list):
                            if nome_prof_ctx:
                                for p in profs['professionals']:
                                    nome = (p.get('nome') or '').lower()
                                    if nome_prof_ctx.lower() in nome:
                                        professional_id = p.get('id')
                                        break
                            if not professional_id and profs['professionals']:
                                professional_id = profs['professionals'][0].get('id')
                    except Exception:
                        pass

                # 4) Verificar disponibilidade usando regras expandidas e a duração real do serviço
                # Injetar contexto no config para permitir resolução por nome dentro da tool
                empresa_config_ctx = dict(empresa_config)
                empresa_config_ctx["current_context"] = (contexto_reserva or {})

                # Se não temos professional_id e há nome no contexto, tentar resolver agora
                if not professional_id:
                    try:
                        nome_ctx = (contexto_reserva or {}).get("profissional_nome")
                        if nome_ctx:
                            # Sanitizar sufixos comuns que grudem ao nome ("para", "pra", "p/")
                            clean = nome_ctx.strip()
                            for stop in [" para", " pra", " p/"]:
                                if clean.lower().endswith(stop):
                                    clean = clean[: -len(stop)]
                                    break
                            # Persistir versão limpa no contexto
                            (contexto_reserva or {})["profissional_nome"] = clean
                            # Resolver ID pelo nome (busca lista completa e fuzzy match)
                            logger.info(f"🔎 Tentando resolver profissional por nome a partir do contexto: {clean}")
                            resolved = trinks_intelligent_tools.resolve_professional_id_by_name(clean, empresa_config_ctx)
                            if resolved:
                                professional_id = resolved
                                logger.info(f"🎯 profissional_nome no contexto resolvido para ID: {professional_id}")
                    except Exception:
                        pass

                availability_result = trinks_intelligent_tools.check_professional_availability(
                    data=data,
                    service_id=str(detected_service_id) if detected_service_id else None,
                    empresa_config=empresa_config_ctx,
                    professional_id=str(professional_id) if professional_id else None,
                )
                
                # Retornar JSON estruturado para o agente decidir a apresentação
                try:
                    by_prof = availability_result.get("by_professional", [])
                except Exception:
                    by_prof = []
                matched_prof = availability_result.get("matched_professional_id")
                slots = availability_result.get("available_slots", [])
                # Salvar última disponibilidade resumida (para validação de reserva)
                try:
                    if contexto_reserva is not None:
                        contexto_reserva.setdefault('ultima_disponibilidade', {})
                        contexto_reserva['ultima_disponibilidade'] = {
                            'data': data,
                            'slots': slots,
                            'profissional_id': matched_prof
                        }
                        if matched_prof and not contexto_reserva.get('profissional_id'):
                            contexto_reserva['profissional_id'] = matched_prof
                except Exception:
                    pass
                import json as _json
                payload = {
                    'api': 'trinks',
                    'date': data,
                    'by_professional': by_prof,
                    'matched_professional_id': matched_prof,
                    'all_slots': slots,
                    'available': availability_result.get('available', bool(slots)),
                }
                return _json.dumps(payload, ensure_ascii=False)

            except Exception as e:
                logger.warning(f"Erro ao usar ferramentas inteligentes, usando fallback: {e}")
                # Fallback para método antigo
                result = self.api_tools.call_api(
                    api_name="Trinks",
                    endpoint_path="/api/availability",
                    method="GET",
                    config=config,
                    date=data
                )
                return f"Verificação Trinks para {data}: {result}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar Trinks: {e}")
            return f"Erro ao verificar Trinks para {data}: {str(e)}"
    
    def _verificar_api_generica(self, api_name: str, data: str, config: Dict[str, Any]) -> str:
        """Verifica disponibilidade em API genérica"""
        try:
            # Tentar endpoints comuns de agenda
            endpoints_to_try = [
                "/availability",
                "/slots",
                "/calendar/availability",
                "/booking/available",
                "/schedule/available"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    result = self.api_tools.call_api(
                        api_name=api_name,
                        endpoint_path=endpoint,
                        method="GET",
                        config=config,
                        date=data
                    )
                    
                    if "erro" not in result.lower() and "error" not in result.lower():
                        return f"Verificação {api_name} para {data}: {result}"
                        
                except Exception:
                    continue
            
            return f"Não foi possível verificar disponibilidade na {api_name} para {data}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar {api_name}: {e}")
            return f"Erro ao verificar {api_name} para {data}: {str(e)}"
    
    def fazer_reserva(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any], email: str | None = None, contexto_reserva: Dict[str, Any] = None) -> str:
        """Faz reserva usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "❌ Nenhuma API de agenda configurada para esta empresa. Não posso fazer reservas."
            
            # Validar formato da data
            try:
                from datetime import datetime
                datetime.strptime(data, '%Y-%m-%d')
            except ValueError:
                return f"❌ Formato de data inválido: {data}. Use o formato YYYY-MM-DD (ex: 2024-01-15)"
            
            # Validar formato da hora
            try:
                datetime.strptime(hora, '%H:%M')
            except ValueError:
                return f"❌ Formato de hora inválido: {hora}. Use o formato HH:MM (ex: 14:30)"
            
            # Validar cliente
            if not cliente or cliente.strip() == '':
                return "❌ Nome do cliente é obrigatório para fazer a reserva."
            
            # Guardrail: validar se o horário pertence à última disponibilidade mostrada
            try:
                if contexto_reserva and isinstance(contexto_reserva.get('ultima_disponibilidade'), dict):
                    last = contexto_reserva['ultima_disponibilidade']
                    last_date = last.get('data')
                    last_slots = set(last.get('slots') or [])
                    if last_date == data and last_slots:
                        if hora not in last_slots:
                            exemplos = "\n".join([f"- {s}" for s in list(last_slots)[:10]])
                            return (
                                "❌ Esse horário não está entre os disponíveis recentes.\n"
                                f"Data: {data}\n"
                                "Escolha um dos horários disponíveis abaixo e me diga qual prefere:\n"
                                f"{exemplos}"
                            )
            except Exception:
                pass
            
            # Usar API específica ou genérica
            if api_name == "Google Calendar":
                return self._fazer_reserva_google_calendar(data, hora, cliente, empresa_config, email=email)
            elif api_name == "Google Sheets":
                # Extrair WaId e outras informações do contexto de reserva
                waid = (contexto_reserva or {}).get('waid') or empresa_config.get('cliente_id')
                quantidade_pessoas = (contexto_reserva or {}).get('quantidade_pessoas')
                observacoes = (contexto_reserva or {}).get('observacoes')
                return self._fazer_reserva_google_sheets(data, hora, cliente, empresa_config, api_config, waid=waid, quantidade_pessoas=quantidade_pessoas, observacoes=observacoes)
            elif api_name == "Trinks":
                return self._fazer_reserva_trinks(data, hora, cliente, api_config)
            else:
                return self._fazer_reserva_generica(api_name, data, hora, cliente, api_config)
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva: {e}")
            return f"❌ Erro ao fazer reserva: {str(e)}"
    
    def _fazer_reserva_google_calendar(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any], email: str | None = None) -> str:
        """Faz reserva no Google Calendar (com invite se email informado)"""
        try:
            calendar_service = self._get_calendar_service(empresa_config)
            sheets_service = self._get_sheets_service(empresa_config)
            
            # 1. Criar evento no Google Calendar (com invite se houver email)
            date_time = f"{data}T{hora}:00"
            result = calendar_service.schedule_meeting(
                email=(email or ""),
                name=cliente,
                company=empresa_config.get('nome', 'Empresa'),
                date_time=date_time,
                duration_minutes=60
            )
            
            if not result.get('success'):
                return f"❌ Erro ao criar evento no Google Calendar: {result.get('message')}"
            
            # 2. Registrar no Google Sheets (se configurado)
            try:
                if sheets_service:
                    sheets_service.add_reservation(
                        data=data,
                        hora=hora,
                        cliente=cliente,
                        empresa=empresa_config.get('nome', 'Empresa')
                    )
            except Exception as e:
                logger.warning(f"Erro ao registrar no Google Sheets: {e}")
            
            invite_msg = f"\nConvite enviado para: {email}" if email else ""
            return f"✅ Evento criado no Google Calendar!{invite_msg}\nData: {data}\nHora: {hora}\nCliente: {cliente}\nID do evento: {result.get('event_id')}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva no Google Calendar: {e}")
            return f"❌ Erro ao fazer reserva no Google Calendar: {str(e)}"
    
    def _fazer_reserva_trinks(self, data: str, hora: str, cliente: str, config: Dict[str, Any]) -> str:
        """Faz reserva na API Trinks"""
        try:
            # Chamar endpoint de reserva da Trinks
            result = self.api_tools.call_api(
                api_name="Trinks",
                endpoint_path="/api/bookings",
                method="POST",
                config=config,
                date=data,
                time=hora,
                customer=cliente
            )
            
            return f"✅ Reserva confirmada na Trinks!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nResultado: {result}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva na Trinks: {e}")
            return f"❌ Erro ao fazer reserva na Trinks: {str(e)}"
    
    def _fazer_reserva_generica(self, api_name: str, data: str, hora: str, cliente: str, config: Dict[str, Any]) -> str:
        """Faz reserva em API genérica"""
        try:
            # Tentar endpoints comuns de reserva
            endpoints_to_try = [
                "/bookings",
                "/reservations",
                "/appointments",
                "/schedule",
                "/calendar/book"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    result = self.api_tools.call_api(
                        api_name=api_name,
                        endpoint_path=endpoint,
                        method="POST",
                        config=config,
                        date=data,
                        time=hora,
                        customer=cliente
                    )
                    
                    if "erro" not in result.lower() and "error" not in result.lower():
                        return f"✅ Reserva confirmada na {api_name}!\nData: {data}\nHora: {hora}\nCliente: {cliente}\nResultado: {result}"
                        
                except Exception:
                    continue
            
            return f"❌ Não foi possível fazer reserva na {api_name} para {data} {hora}"
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva na {api_name}: {e}")
            return f"❌ Erro ao fazer reserva na {api_name}: {str(e)}"
    
    def _fazer_reserva_google_sheets(self, data: str, hora: str, cliente: str, empresa_config: Dict[str, Any], api_config: Dict[str, Any], waid: str = None, quantidade_pessoas: int = None, observacoes: str = None) -> str:
        """Faz reserva no Google Sheets"""
        try:
            # Criar configuração para o Google Sheets Service
            sheets_config = {
                'google_sheets_id': api_config.get('google_sheets_id'),
                'google_sheets_client_id': api_config.get('google_sheets_client_id'),
                'google_sheets_client_secret': api_config.get('google_sheets_client_secret'),
                'google_sheets_refresh_token': api_config.get('google_sheets_refresh_token'),
                'google_sheets_service_account': api_config.get('google_sheets_service_account')
            }
            
            from ..integrations.google_sheets_service import GoogleSheetsService
            sheets_service = GoogleSheetsService(sheets_config)
            
            # Montar dados padronizados
            reserva_data = {
                'nome': cliente,
                'telefone': waid or '',  # WaId na coluna Telefone
                'waid': waid or '',
                'data': data,
                'horario': hora,
                'pessoas': str(quantidade_pessoas) if quantidade_pessoas else '',
                'observacoes': observacoes or ''
            }
            
            # Upsert: atualizar se já existir, senão criar
            action = sheets_service.upsert_reserva(
                spreadsheet_id=sheets_config['google_sheets_id'],
                waid=waid or '',
                reserva_data=reserva_data
            )
            
            if action == 'updated':
                waid_info = f" (WaId: {waid})" if waid else ""
                return f"✅ Reserva atualizada no Google Sheets!\nData: {data}\nHora: {hora}\nCliente: {cliente}{waid_info}"
            elif action == 'created':
                waid_info = f" (WaId: {waid})" if waid else ""
                return f"✅ Reserva confirmada no Google Sheets!\nData: {data}\nHora: {hora}\nCliente: {cliente}{waid_info}\nA reserva foi registrada na planilha."
            else:
                return f"❌ Não foi possível registrar/atualizar a reserva no Google Sheets."
            
        except Exception as e:
            logger.error(f"Erro ao fazer reserva no Google Sheets: {e}")
            return f"❌ Erro ao fazer reserva no Google Sheets: {str(e)}"
    
    def cancelar_reserva(self, event_id: str, empresa_config: Dict[str, Any]) -> str:
        """Cancela reserva usando qualquer API de agenda disponível"""
        try:
            # Encontrar API de agenda disponível
            api_name, api_config = self._find_calendar_api(empresa_config)
            
            if not api_name:
                return "❌ Nenhuma API de agenda configurada para esta empresa."
            
            if api_name == "Google Calendar":
                calendar_service = self._get_calendar_service(empresa_config)
                calendar_service.delete_event(event_id)
                return f"✅ Reserva cancelada com sucesso no Google Calendar (ID: {event_id})"
            else:
                # Tentar cancelar em API genérica
                result = self.api_tools.call_api(
                    api_name=api_name,
                    endpoint_path=f"/bookings/{event_id}",
                    method="DELETE",
                    config=api_config
                )
                return f"✅ Reserva cancelada com sucesso na {api_name} (ID: {event_id})"
            
        except Exception as e:
            logger.error(f"Erro ao cancelar reserva: {e}")
            return f"❌ Erro ao cancelar reserva: {str(e)}" 
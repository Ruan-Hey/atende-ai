import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random

logger = logging.getLogger(__name__)

class MessageBuffer:
    """Buffer para agrupar mensagens e otimizar respostas"""
    
    def __init__(self, buffer_timeout: int = 10):
        self.buffer_timeout = buffer_timeout  # Segundos para agrupar mensagens
        self.buffers = defaultdict(list)  # Buffer por cliente
        self.timers = {}  # Timers por cliente
        self.callback = None  # Callback para processar mensagens agrupadas
    

    
    def set_callback(self, callback: Callable):
        """Define o callback para processar mensagens agrupadas"""
        self.callback = callback
    
    def add_message(self, cliente_id: str, empresa: str, message_data: Dict[str, Any]):
        """Adiciona mensagem ao buffer"""
        buffer_key = f"{empresa}:{cliente_id}"
        
        # Adicionar mensagem ao buffer
        self.buffers[buffer_key].append({
            'data': message_data,
            'timestamp': datetime.now()
        })
        
        # Cancelar timer existente se houver
        if buffer_key in self.timers:
            self.timers[buffer_key].cancel()
        
        # Criar novo timer
        timer = asyncio.create_task(self._process_buffer_after_timeout(buffer_key))
        self.timers[buffer_key] = timer
        
        logger.info(f"Mensagem adicionada ao buffer para {buffer_key}")
    
    async def _process_buffer_after_timeout(self, buffer_key: str):
        """Processa buffer após timeout"""
        try:
            await asyncio.sleep(self.buffer_timeout)
            
            # Verificar se ainda há mensagens no buffer
            if buffer_key in self.buffers and self.buffers[buffer_key]:
                await self._process_buffered_messages(buffer_key)
                
        except asyncio.CancelledError:
            logger.info(f"Timer cancelado para {buffer_key}")
        except Exception as e:
            logger.error(f"Erro no timer para {buffer_key}: {e}")
    
    async def _process_buffered_messages(self, buffer_key: str):
        """Processa mensagens agrupadas do buffer"""
        try:
            if not self.callback:
                logger.warning("Callback não definido para processar mensagens")
                return
            
            # Pegar mensagens do buffer
            messages = self.buffers[buffer_key]
            
            if not messages:
                return
            
            # Separar empresa e cliente_id
            empresa, cliente_id = buffer_key.split(':', 1)
            
            # Agrupar mensagens por tipo
            text_messages = []
            audio_messages = []
            
            for msg in messages:
                message_type = msg['data'].get('MessageType', 'text')
                if message_type == 'audio':
                    audio_messages.append(msg)
                else:
                    text_messages.append(msg)
            
            # Processar mensagens de texto agrupadas
            if text_messages:
                await self._process_text_messages_group(empresa, cliente_id, text_messages)
            
            # Processar mensagens de áudio (uma por vez)
            for audio_msg in audio_messages:
                await self._process_single_message(empresa, cliente_id, audio_msg)
            
            # Limpar buffer
            self.buffers[buffer_key] = []
            
            # Limpar timer
            if buffer_key in self.timers:
                del self.timers[buffer_key]
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagens agrupadas: {e}")
    
    async def _process_text_messages_group(self, empresa: str, cliente_id: str, messages: list):
        """Processa grupo de mensagens de texto"""
        try:
            # Combinar todas as mensagens de texto
            combined_text = "\n".join([
                msg['data'].get('Body', '') for msg in messages
            ])
            
            # Criar dados combinados
            combined_data = {
                'Body': combined_text,
                'WaId': cliente_id,
                'MessageType': 'text',
                'ProfileName': messages[0]['data'].get('ProfileName', 'Cliente'),
                'From': messages[0]['data'].get('From', ''),
                'To': messages[0]['data'].get('To', ''),
                'is_grouped': True,
                'original_count': len(messages)
            }
            
            # Processar com callback
            if self.callback:
                await self.callback(combined_data, empresa)
                
        except Exception as e:
            logger.error(f"Erro ao processar grupo de mensagens: {e}")
    
    async def _process_single_message(self, empresa: str, cliente_id: str, message: Dict[str, Any]):
        """Processa mensagem individual (áudio)"""
        try:
            if self.callback:
                await self.callback(message['data'], empresa)
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem individual: {e}")
    
    def force_process_buffer(self, cliente_id: str, empresa: str):
        """Força o processamento do buffer imediatamente"""
        buffer_key = f"{empresa}:{cliente_id}"
        
        if buffer_key in self.timers:
            self.timers[buffer_key].cancel()
        
        # Criar task para processar imediatamente
        asyncio.create_task(self._process_buffered_messages(buffer_key))
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Retorna status dos buffers"""
        return {
            'active_buffers': len(self.buffers),
            'active_timers': len(self.timers),
            'buffer_details': {
                key: {
                    'message_count': len(messages),
                    'oldest_message': min([msg['timestamp'] for msg in messages]) if messages else None
                }
                for key, messages in self.buffers.items()
            }
        } 
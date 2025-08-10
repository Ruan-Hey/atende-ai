import openai
import logging
from typing import Dict, Any, Optional
# from ..config import Config  # not required here

logger = logging.getLogger(__name__)

class OpenAIService:
    """Serviço para integração com OpenAI"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def process_text_message(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> str:
        """Processa mensagem de texto usando OpenAI"""
        try:
            # Construir prompt com contexto da empresa
            prompt = self._build_prompt(message, context, empresa_config)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem com OpenAI: {e}")
            return "Desculpe, tive um problema técnico. Pode tentar novamente?"
    
    def generate_response(self, message: str) -> str:
        """Gera resposta simples para testes"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Você é um assistente útil."},
                    {"role": "user", "content": message}
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            return "Desculpe, tive um problema técnico."
    
    def generate_response_with_context(self, context: list, message: str) -> str:
        """Gera resposta com contexto de conversa"""
        try:
            messages = [{"role": "system", "content": "Você é um assistente útil."}]
            messages.extend(context)
            messages.append({"role": "user", "content": message})
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Erro ao gerar resposta com contexto: {e}")
            return "Desculpe, tive um problema técnico."
    
    def transcribe_audio(self, audio_url: str, twilio_sid: str, twilio_token: str) -> str:
        """Transcreve áudio usando OpenAI"""
        try:
            # Baixar áudio da URL com autenticação do Twilio
            import requests
            response = requests.get(audio_url, auth=(twilio_sid, twilio_token))
            response.raise_for_status()
            
            # Salvar temporariamente
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Transcrever
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Limpar arquivo temporário
            import os
            os.unlink(temp_file_path)
            
            return transcript.text
            
        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {e}")
            return ""
    
    def _build_prompt(self, message: str, context: Dict[str, Any], empresa_config: Dict[str, Any]) -> str:
        """Constrói prompt personalizado para a empresa"""
        base_prompt = empresa_config.get('prompt', 'Você é um atendente virtual.')
        
        # Adicionar contexto da conversa
        context_messages = context.get('messages', [])
        conversation_history = ""
        
        if context_messages:
            conversation_history = "\n".join([
                f"{'Bot' if msg.get('is_bot') else 'Cliente'}: {msg.get('text', '')}"
                for msg in context_messages[-5:]  # Últimas 5 mensagens
            ])
        
        full_prompt = f"""
{base_prompt}

Histórico da conversa:
{conversation_history}

Mensagem atual do cliente: {message}

Responda de forma natural e útil, seguindo o tom e estilo da empresa.
"""
        
        # Adicionar instrução extra se mensagem_quebrada for True
        if empresa_config.get('mensagem_quebrada'):
            full_prompt += "\nIMPORTANTE: Sempre que possível, quebre respostas longas em até 3 mensagens curtas e sequenciais, para facilitar a leitura no WhatsApp."
        
        return full_prompt.strip() 
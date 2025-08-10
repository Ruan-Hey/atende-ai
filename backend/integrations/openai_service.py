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
    
    def classify_message(self, message: str, labels_json: Dict[str, Any]) -> Dict[str, Any]:
        """Classifica uma mensagem em uma das labels definidas no labels_json.
        Retorna dict: { 'label': str|None, 'confidence': float, 'observacoes': dict, 'rationale': str }
        """
        try:
            labels = (labels_json or {}).get('labels', [])
            if not labels:
                return {"label": None, "confidence": 0.0, "observacoes": {}, "rationale": "no labels"}

            min_conf = (labels_json or {}).get('min_confidence', 0.6)

            system_prompt = (
                "Você é um classificador disciplinado. Classifique a mensagem do cliente em UMA label dentre as fornecidas.\n"
                "Respeite estritamente os slugs disponíveis. Se não houver label compatível, retorne null.\n"
                "Se possível, gere observações sucintas seguindo as instruções de cada label (ex.: nome, data, horário).\n"
                "Responda SOMENTE em JSON com as chaves: label, confidence, observacoes, rationale."
            )

            labels_brief = []
            for lb in labels:
                if not lb.get('active', True):
                    continue
                labels_brief.append({
                    'slug': lb.get('slug') or lb.get('title'),
                    'title': lb.get('title'),
                    'description': lb.get('description', ''),
                    'positive_examples': lb.get('positive_examples', [])[:5],
                    'negative_examples': lb.get('negative_examples', [])[:5],
                    'observations_instructions': lb.get('observations_instructions', '')
                })

            user_prompt = {
                "role": "user",
                "content": (
                    "Mensagem: " + message + "\n" +
                    "Labels disponíveis (JSON):\n" + str(labels_brief) + "\n" +
                    f"Limiar mínimo de confiança: {min_conf}"
                )
            }

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    user_prompt
                ],
                temperature=0.2,
                max_tokens=300
            )

            raw = response.choices[0].message.content.strip()
            import json as pyjson
            try:
                data = pyjson.loads(raw)
            except Exception:
                # Tentar extrair bloco JSON
                import re
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    data = pyjson.loads(m.group(0))
                else:
                    return {"label": None, "confidence": 0.0, "observacoes": {}, "rationale": "invalid json"}
            # Sanitização básica
            if data.get('label') is None:
                return {"label": None, "confidence": float(data.get('confidence', 0.0)), "observacoes": data.get('observacoes') or {}, "rationale": data.get('rationale', '')}
            # Garantir que o label está entre os slugs
            slugs = { (lb.get('slug') or lb.get('title')) for lb in labels if lb.get('active', True) }
            if data.get('label') not in slugs:
                return {"label": None, "confidence": float(data.get('confidence', 0.0)), "observacoes": data.get('observacoes') or {}, "rationale": "label not allowed"}
            return {
                "label": data.get('label'),
                "confidence": float(data.get('confidence', 0.0)),
                "observacoes": data.get('observacoes') or {},
                "rationale": data.get('rationale', '')
            }
        except Exception as e:
            logger.error(f"Erro ao classificar mensagem: {e}")
            return {"label": None, "confidence": 0.0, "observacoes": {}, "rationale": "exception"}
    
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
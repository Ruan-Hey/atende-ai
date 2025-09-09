from typing import Dict, Any, List
from tools.trinks_intelligent_tools import TrinksIntelligentTools


class TrinksProvider:
    """Provider para operações de agenda na Trinks."""

    def __init__(self, empresa_config: Dict[str, Any]):
        # Normalização defensiva: aceitar config com variações (api_key/key, base_url/url, etc.)
        cfg = dict(empresa_config)
        trinks_cfg = cfg.get('trinks_config') or {}
        # Extrair de empresa_config plano se vier somente lá
        api_key = (
            trinks_cfg.get('api_key') or trinks_cfg.get('key') or cfg.get('trinks_api_key') or cfg.get('api_key')
        )
        base_url = (
            trinks_cfg.get('base_url') or trinks_cfg.get('url_base') or trinks_cfg.get('url')
            or cfg.get('trinks_base_url') or cfg.get('base_url') or 'https://api.trinks.com/v1'
        )
        if base_url and not str(base_url).startswith(('http://', 'https://')):
            base_url = f"https://{str(base_url).lstrip('/')}"
        estab = (
            trinks_cfg.get('estabelecimento_id') or trinks_cfg.get('estabelecimentoId')
            or trinks_cfg.get('estabelecimento') or cfg.get('trinks_estabelecimento_id')
        )
        normalized = dict(cfg)
        normalized['trinks_api_key'] = api_key
        normalized['trinks_base_url'] = base_url
        normalized['trinks_estabelecimento_id'] = estab

        self.empresa_config = normalized
        self.tools = TrinksIntelligentTools(self.empresa_config)

    def list_appointments_range(self, start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
        resp = self.tools.list_appointments_range(start_iso, end_iso, self.empresa_config)
        if resp.get('success'):
            # Filtrar cancelados (status.nome == 'Cancelado' ou id == 9)
            data = resp.get('data', [])
            filtered = []
            for ap in data:
                st = ap.get('status') or {}
                nome = (st.get('nome') or '').strip().lower()
                sid = st.get('id')
                if nome == 'cancelado' or sid == 9:
                    continue
                filtered.append(ap)
            return filtered
        return []



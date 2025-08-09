import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from .cliente_tools import ClienteTools
    from .calendar_tools import CalendarTools
    from .message_tools import MessageTools
except ImportError:
    from cliente_tools import ClienteTools
    from calendar_tools import CalendarTools
    from message_tools import MessageTools

__all__ = ['ClienteTools', 'CalendarTools', 'MessageTools'] 
# Placeholder to expose future tools 
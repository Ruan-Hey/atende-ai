import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from .services import MetricsService
except ImportError:
    from services import MetricsService

__all__ = ['MetricsService'] 
#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, inspect, text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config

"""
Safe migration:
- Add JSON column empresas.labels_json (nullable)
- Add columns to atendimentos:
  - label_slug VARCHAR(100)
  - source_message_id INTEGER (FK to messages.id) [FK not enforced here for safety]
  - observacoes JSON
  - confidence FLOAT
  - indexes as needed
The script is idempotent and can be re-run safely.
"""

def column_exists(inspector, table_name, column_name):
    cols = inspector.get_columns(table_name)
    return any(c['name'] == column_name for c in cols)

def index_exists(inspector, table_name, index_name):
    try:
        idx = inspector.get_indexes(table_name)
        return any(i['name'] == index_name for i in idx)
    except Exception:
        return False

def main():
    engine = create_engine(Config().POSTGRES_URL)
    insp = inspect(engine)

    with engine.begin() as conn:
        # empresas.labels_json
        if 'empresas' in insp.get_table_names():
            if not column_exists(insp, 'empresas', 'labels_json'):
                conn.execute(text("ALTER TABLE empresas ADD COLUMN labels_json JSON"))
        
        # atendimentos columns
        if 'atendimentos' in insp.get_table_names():
            if not column_exists(insp, 'atendimentos', 'label_slug'):
                conn.execute(text("ALTER TABLE atendimentos ADD COLUMN label_slug VARCHAR(100)"))
            if not column_exists(insp, 'atendimentos', 'source_message_id'):
                conn.execute(text("ALTER TABLE atendimentos ADD COLUMN source_message_id INTEGER"))
            if not column_exists(insp, 'atendimentos', 'observacoes'):
                conn.execute(text("ALTER TABLE atendimentos ADD COLUMN observacoes JSON"))
            if not column_exists(insp, 'atendimentos', 'confidence'):
                conn.execute(text("ALTER TABLE atendimentos ADD COLUMN confidence DOUBLE PRECISION"))
            # indexes
            if not index_exists(insp, 'atendimentos', 'idx_atendimentos_empresa_label_date'):
                conn.execute(text("CREATE INDEX idx_atendimentos_empresa_label_date ON atendimentos (empresa_id, label_slug, data_atendimento)"))
            if not index_exists(insp, 'atendimentos', 'idx_atendimentos_source_message'):
                conn.execute(text("CREATE UNIQUE INDEX idx_atendimentos_source_message ON atendimentos (source_message_id)"))

if __name__ == '__main__':
    main() 
import os
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker

# Caminho do SQLite local
sqlite_url = "sqlite:///finance.db"

# URL do Postgres no Render (pegar no dashboard → Environment → DATABASE_URL)
postgres_url = os.environ.get("DATABASE_URL")
if postgres_url.startswith("postgres://"):
    postgres_url = postgres_url.replace("postgres://", "postgresql://", 1)

# Engines
sqlite_engine = create_engine(sqlite_url)
postgres_engine = create_engine(postgres_url)

# Metadata
sqlite_meta = MetaData(bind=sqlite_engine)
postgres_meta = MetaData(bind=postgres_engine)

sqlite_meta.reflect()
postgres_meta.reflect()

# Sessões
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

sqlite_session = SQLiteSession()
postgres_session = PostgresSession()

for table_name, table in sqlite_meta.tables.items():
    print(f"Migrando tabela: {table_name}")
    rows = sqlite_session.query(table).all()
    if not rows:
        continue

    postgres_table = Table(table_name, postgres_meta, autoload_with=postgres_engine)
    data = [dict(row._mapping) for row in rows]

    postgres_session.execute(postgres_table.insert(), data)
    postgres_session.commit()

print("✅ Migração concluída com sucesso.")

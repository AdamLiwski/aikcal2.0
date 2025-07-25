from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Importujemy Base z naszych modeli, aby Alembic wiedział,
# jakie tabele ma śledzić. To jest kluczowy import.
from core.models import Base
# Importujemy URL do naszej bazy danych
from core.db import SQLALCHEMY_DATABASE_URL
DATABASE_URL = SQLALCHEMY_DATABASE_URL

# To jest obiekt konfiguracyjny Alembic, odczytywany z pliku alembic.ini
config = context.config

# Ustawiamy URL bazy danych w konfiguracji Alembic,
# aby nie trzeba go było wpisywać w pliku .ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpretujemy plik konfiguracyjny dla logowania w Pythonie.
# Ta linia głównie ustawia loggery.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ustawiamy metadane na te z naszych modeli.
# Dzięki temu Alembic wie, jak wyglądają nasze tabele.
target_metadata = Base.metadata

# inne wartości z konfiguracji, zdefiniowane przez potrzeby env.py,
# mogą być pobrane:
# my_important_option = config.get_main_option("my_important_option")
# ... itp.


def run_migrations_offline() -> None:
    """Uruchamia migracje w trybie 'offline'.

    To polecenie konfiguruje kontekst z samym URL-em, bez Engine.
    Wywołanie context.execute() z tym kontekstem zrzuci
    wygenerowany SQL do standardowego wyjścia.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Uruchamia migracje w trybie 'online'.

    W tym scenariuszu potrzebujemy obiektu Engine.
    Tworzymy go tutaj i kojarzymy z nim połączenie
    z kontekstem.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

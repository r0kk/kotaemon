from sqlmodel import create_engine
from theflow.settings import settings

engine = create_engine(
    settings.KH_DATABASE,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True,
)

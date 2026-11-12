from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from src.data.models.base import NAMING_CONVENTION


class ContentBase(DeclarativeBase):
    metadata = MetaData(schema="content", naming_convention=NAMING_CONVENTION)

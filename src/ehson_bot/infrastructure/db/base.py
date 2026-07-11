"""Declarative base for all ORM models. Imported by Alembic's env.py."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

"""
db.base

Shared SQLAlchemy declarative base. All models import Base from here
so main.py can create every table with one Base.metadata.create_all()
call.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

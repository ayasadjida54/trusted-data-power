"""
models

Importing this package registers every model on Base.metadata, which
is what makes Base.metadata.create_all() in main.py create all tables.
Individual modules could be imported directly, but importing them here
means main.py only needs one import to get all of them.
"""

from backend.models.organization import Organization
from backend.models.user import User
from backend.models.dataset import Dataset
from backend.models.analysis_run import AnalysisRun
from backend.models.alert import Alert
from backend.models.datasource import DataSource

__all__ = ["Organization", "User", "Dataset", "AnalysisRun", "Alert", "DataSource"]

"""
services.json_safe

The engine returns numpy/pandas types (np.float64, np.int64, DataFrames,
NaN) that Python's json module - which SQLAlchemy's JSON column type
uses under the hood - cannot serialize directly. to_jsonable() converts
a value (recursively, for dicts/lists/DataFrames) into plain Python
types so it can be safely stored in a JSON column and returned as-is
in an API response.
"""

import numpy as np
import pandas as pd


def to_jsonable(value):
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]

    if isinstance(value, pd.DataFrame):
        return to_jsonable(value.to_dict(orient="records"))

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.ndarray):
        return to_jsonable(value.tolist())

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value

"""
profiling.py

Pure descriptive facts about a dataset's shape and structure.
No judgment calls here (no "good"/"bad") - that belongs in quality_checks.py.
"""

import pandas as pd


def build_dataset_profile(df: pd.DataFrame) -> dict:
    """
    Compute basic structural statistics about a DataFrame.

    Returns a dict of counts that the UI can display directly.
    """
    n_rows, n_cols = df.shape

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    total_cells = n_rows * n_cols if n_rows and n_cols else 0
    total_missing = int(df.isna().sum().sum())
    missing_pct = round((total_missing / total_cells) * 100, 2) if total_cells else 0.0

    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows / n_rows) * 100, 2) if n_rows else 0.0

    return {
        "n_rows": n_rows,
        "n_columns": n_cols,
        "n_numeric_columns": len(numeric_cols),
        "n_categorical_columns": len(categorical_cols),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "total_missing_cells": total_missing,
        "missing_cells_pct": missing_pct,
        "duplicate_rows": duplicate_rows,
        "duplicate_rows_pct": duplicate_pct,
    }


def get_column_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a small table of column name -> detected pandas dtype,
    formatted for display in Streamlit.
    """
    return pd.DataFrame(
        {
            "column": df.columns,
            "dtype": [str(dt) for dt in df.dtypes],
            "non_null_count": [df[c].notna().sum() for c in df.columns],
        }
    )

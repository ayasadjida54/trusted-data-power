"""
services.file_loader

Loads an uploaded CSV or XLSX file into a DataFrame, with user-friendly
ValueError messages on failure. Framework-agnostic: takes a filename and
a file-like object, so it doesn't depend on FastAPI's UploadFile type
directly, which keeps it easy to unit test.
"""

import pandas as pd


def load_dataframe(filename: str, file_obj) -> pd.DataFrame:
    """
    Load a CSV or XLSX file into a DataFrame.

    `file_obj` must be a file-like object opened in binary mode (e.g.
    FastAPI's UploadFile.file, or a plain `open(path, "rb")`).

    Raises ValueError with a user-friendly message on any failure -
    unsupported extension, empty file, or unreadable content.
    """
    lower_name = filename.lower()

    try:
        if lower_name.endswith(".csv"):
            return pd.read_csv(file_obj)
        elif lower_name.endswith(".xlsx"):
            return pd.read_excel(file_obj, engine="openpyxl")
        else:
            raise ValueError(
                "Unsupported file type. Please upload a .csv or .xlsx file."
            )
    except pd.errors.EmptyDataError:
        raise ValueError("The uploaded file appears to be empty.")
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise ValueError(f"Could not read this file: {exc}")

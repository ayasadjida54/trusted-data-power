"""
_text_normalization

Shared logic for "what is the standard form of this text value" - used
by BOTH quality_checks.py (to DETECT capitalization inconsistency) and
cleaning.py (to FIX it). Kept in exactly one place so detection and
cleaning can never silently drift apart: "found N inconsistent values"
and "fixed N inconsistent values" are guaranteed to agree, because
they're computed by the same function.
"""

import pandas as pd


def standardize_capitalization(stripped: pd.Series) -> pd.Series:
    """
    Given a Series of already-whitespace-stripped string values, return
    a same-shaped Series where every value has been replaced with the
    MAJORITY raw variant among all values sharing its lowercase form -
    e.g. if a column has {"Yes": 90, "yes": 10}, every "yes" becomes
    "Yes" (and every "Yes" stays "Yes", since it's already the
    majority form). A value with no other members in its normalized
    group is unaffected (it IS the majority, trivially).
    """
    normalized = stripped.str.lower()
    return stripped.groupby(normalized).transform(lambda group: group.value_counts().idxmax())

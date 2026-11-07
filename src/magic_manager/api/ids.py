"""Identifier types for API/job inputs that reach the MTGJSON wrapper or its cache.

Thin aliases over the ONE engine check (:func:`mtgjson.valid_set_code` /
:func:`mtgjson.valid_deck_name`): a bad value is a 422 before anything runs.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator

from .. import mtgjson

SetCode = Annotated[str, AfterValidator(mtgjson.valid_set_code)]
DeckFileName = Annotated[str, AfterValidator(mtgjson.valid_deck_name)]

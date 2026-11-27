"""Oracle (card-function) tags for filtering: search the local Scryfall Tagger
cache, and resolve chosen tags to the cards that carry them (each tag rolls up
its subtree, like a function root). Adapts ``scryfall_tags`` — no logic here."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .. import scryfall_tags


class OracleTagHitOut(BaseModel):
    id: str
    label: str
    slug: str
    cards: int = Field(description="Cards carrying the tag or anything below it.")


class OracleTagSearchOut(BaseModel):
    synced: bool = Field(description="False until the Scryfall tag cache is loaded (job `scryfall.sync_tags`).")
    tags: list[OracleTagHitOut]


class OracleTagRefOut(BaseModel):
    id: str
    label: str
    slug: str


class OracleTagCardsOut(BaseModel):
    tags: list[OracleTagRefOut] = Field(description="The requested tags that exist locally (unknown slugs are left out).")
    oracle_ids: list[str] = Field(description="Cards carrying ANY of them, sorted.")


def search(q: str, limit: int = 20) -> OracleTagSearchOut:
    return OracleTagSearchOut(synced=scryfall_tags.status()["tags"] > 0, tags=[OracleTagHitOut(**t) for t in scryfall_tags.oracle_tag_search(q, limit)])


def cards(slugs: list[str]) -> OracleTagCardsOut:
    tags, ids = scryfall_tags.oracles_with_tags(slugs)
    return OracleTagCardsOut(tags=[OracleTagRefOut(**t) for t in tags], oracle_ids=sorted(ids))

"""Configuration loaded from .env and constants for the crawler."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    client_id: str
    client_secret: str

    max_artists: int = 300
    album_types: str = "album,single"
    output_path: Path = Path("data/collab_graph.graphml")

    @classmethod
    def load(cls) -> "Config":
        load_dotenv()
        try:
            return cls(
                client_id=os.environ["CLIENT_ID"],
                client_secret=os.environ["CLIENT_SECRET"],
            )
        except KeyError as e:
            sys.exit(f"Missing env var {e} — check your .env file")

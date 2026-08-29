"""The bundled set of 100 natural Trichoderma promoters.

Reference material, not a set of good answers: useful for motif mining and as
opponents for the judge.
"""

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..config import PROMOTERS_CSV, PROMOTERS_CSV_DELIMITER, SEQ_LENGTH
from .validate import normalize


@dataclass
class Promoter:
    name: str
    species: str
    species_short: str
    genome: str
    sequence: str
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_row(cls, row: dict) -> "Promoter":
        return cls(
            name=row.get("nazwa", ""),
            species=row.get("gatunek", ""),
            species_short=row.get("gatunek_krotko", ""),
            genome=row.get("genom", ""),
            sequence=normalize(row.get("sekwencja", "")),
            raw=row,
        )


def load_promoters(path: Path = PROMOTERS_CSV) -> list[Promoter]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"promoter set not found: {path}")
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter=PROMOTERS_CSV_DELIMITER))
    promoters = [Promoter.from_row(row) for row in rows]
    odd = [p.name for p in promoters if len(p.sequence) != SEQ_LENGTH]
    if odd:
        raise ValueError(f"{len(odd)} sequences are not {SEQ_LENGTH} bp: {odd[:5]}")
    return promoters


def species_counts(promoters: list[Promoter]) -> Counter:
    return Counter(p.species_short for p in promoters)


def by_species(promoters: list[Promoter], species_short: str) -> list[Promoter]:
    return [p for p in promoters if p.species_short == species_short]

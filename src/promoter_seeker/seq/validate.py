"""Local mirror of the server-side submission filters.

Running these before uploading turns a wasted five-minute cooldown into an
instant local error.

Per-sequence rules live in `SequenceChecker`; this module adds what the checker
leaves to the caller: normalisation, cross-sequence uniqueness, the server's
filter order and the 100-sequence cap.
"""

from dataclasses import dataclass, field
from typing import Iterable, NamedTuple

from ..config import SUBMISSION_LIMIT
from ..utils.sequence_checker import SequenceChecker


class SeqRecord(NamedTuple):
    name: str
    sequence: str


def normalize(sequence: str) -> str:
    return "".join(sequence.split()).upper()


def n_count(sequence: str) -> int:
    return sequence.count("N")


def problems(sequence: str) -> list[str]:
    """Reasons the server would drop this sequence; empty means acceptable."""
    return SequenceChecker.problems(sequence)


def is_valid(sequence: str) -> bool:
    return SequenceChecker.is_correct(sequence, quiet=True)


@dataclass
class FilterReport:
    n_in_file: int = 0
    n_length_ok: int = 0
    n_unique: int = 0
    n_alphabet_ok: int = 0
    n_after_n_filter: int = 0
    n_scored: int = 0
    rejected_length: list[str] = field(default_factory=list)
    rejected_duplicates: list[str] = field(default_factory=list)
    rejected_alphabet: list[str] = field(default_factory=list)
    rejected_n: list[str] = field(default_factory=list)
    skipped_over_limit: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (
            self.rejected_length
            or self.rejected_duplicates
            or self.rejected_alphabet
            or self.rejected_n
        )

    def summary(self) -> str:
        lines = [
            f"in file        {self.n_in_file}",
            f"length ok      {self.n_length_ok}",
            f"unique         {self.n_unique}",
            f"alphabet ok    {self.n_alphabet_ok}",
            f"after N filter {self.n_after_n_filter}",
            f"scored         {self.n_scored}",
        ]
        for label, ids in (
            ("dropped length", self.rejected_length),
            ("dropped dupes", self.rejected_duplicates),
            ("dropped alphabet", self.rejected_alphabet),
            ("dropped N", self.rejected_n),
            ("over limit", self.skipped_over_limit),
        ):
            if ids:
                lines.append(f"{label:<14} {len(ids)}: {', '.join(ids[:10])}")
        return "\n".join(lines)


def _passes(check, sequence: str) -> bool:
    try:
        check(sequence)
    except ValueError:
        return False
    return True


def filter_records(
    records: Iterable[tuple[str, str]], limit: int = SUBMISSION_LIMIT
) -> tuple[list[SeqRecord], FilterReport]:
    """Apply the server's filters in the server's order and report what fell out.

    Order matters: duplicates are judged after the length check, and the first
    occurrence of a duplicate is the one that survives. Each stage is a separate
    `SequenceChecker` call so a rejection can be attributed to one reason, the
    way the server reports it.
    """
    report = FilterReport()
    seen: set[str] = set()
    kept: list[SeqRecord] = []
    for name, raw in records:
        report.n_in_file += 1
        sequence = normalize(raw)
        if not _passes(SequenceChecker.is_correct_length, sequence):
            report.rejected_length.append(name)
            continue
        report.n_length_ok += 1
        if sequence in seen:
            report.rejected_duplicates.append(name)
            continue
        seen.add(sequence)
        report.n_unique += 1
        if not _passes(SequenceChecker.is_correct_symbol, sequence):
            report.rejected_alphabet.append(name)
            continue
        report.n_alphabet_ok += 1
        if not _passes(SequenceChecker.is_correct_content, sequence):
            report.rejected_n.append(name)
            continue
        report.n_after_n_filter += 1
        kept.append(SeqRecord(name, sequence))

    report.skipped_over_limit = [r.name for r in kept[limit:]]
    kept = kept[:limit]
    report.n_scored = len(kept)
    return kept, report

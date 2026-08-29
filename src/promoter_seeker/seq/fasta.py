"""FASTA serialisation. The API takes the file as a JSON string, not multipart."""

from pathlib import Path
from typing import Iterable

from ..config import MAX_FASTA_CHARS
from .validate import SeqRecord, normalize


def build_fasta(records: Iterable[tuple[str, str]], wrap: int | None = None) -> str:
    lines: list[str] = []
    for name, sequence in records:
        lines.append(">" + str(name).replace("\n", " "))
        if wrap:
            lines.extend(sequence[i : i + wrap] for i in range(0, len(sequence), wrap))
        else:
            lines.append(sequence)
    text = "\n".join(lines)
    if len(text) > MAX_FASTA_CHARS:
        raise ValueError(f"FASTA has {len(text)} chars, limit is {MAX_FASTA_CHARS}")
    return text


def parse_fasta(text: str) -> list[SeqRecord]:
    records: list[SeqRecord] = []
    name: str | None = None
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None:
                records.append(SeqRecord(name, normalize("".join(chunks))))
            name = line[1:].strip()
            chunks = []
        elif name is not None:
            chunks.append(line)
    if name is not None:
        records.append(SeqRecord(name, normalize("".join(chunks))))
    return records


def write_fasta(path: Path, records: Iterable[tuple[str, str]], wrap: int | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_fasta(records, wrap) + "\n", encoding="utf-8")
    return path


def read_fasta(path: Path) -> list[SeqRecord]:
    return parse_fasta(Path(path).read_text(encoding="utf-8"))

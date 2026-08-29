"""Typed wrappers over the hyppe endpoints.

Response objects keep the decoded JSON in `raw`, so a field the organisers add
mid-hackathon is never lost.
"""

from dataclasses import dataclass, field
from typing import Any

from .client import HyppeClient
from .keys import ApiKey


@dataclass
class Me:
    team: str
    participant: str
    valid_until: str
    valid_for_s: float | None
    limits: dict[str, int]
    upload_in_s: float
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "Me":
        return cls(
            team=payload.get("druzyna", ""),
            participant=payload.get("uczestnik", ""),
            valid_until=payload.get("wazny_do", ""),
            valid_for_s=payload.get("wazny_jeszcze_s"),
            limits=payload.get("limity_na_minute", {}),
            upload_in_s=payload.get("zgloszenie_mozliwe_za_s", 0.0),
            raw=payload,
        )


@dataclass
class Wild:
    name: str
    gene: str
    genome: str
    sequence: str
    length: int
    sha256_12: str
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "Wild":
        return cls(
            name=payload.get("nazwa", ""),
            gene=payload.get("gen", ""),
            genome=payload.get("genom", ""),
            sequence=payload["sekwencja"],
            length=payload.get("dlugosc", len(payload["sekwencja"])),
            sha256_12=payload.get("sha256_12", ""),
            raw=payload,
        )


@dataclass
class MapPosition:
    """One position of the navigator map. `pos` is 1-based, as the API reports it."""

    pos: int
    base: str
    change_to: str
    recon: int
    layers: list[int]
    weight: float

    @property
    def is_recommendation(self) -> bool:
        return self.change_to != "."

    @property
    def is_free(self) -> bool:
        """Decoder does not pin this position, so it can be edited outright."""
        return self.recon == 0

    @property
    def is_overwritten(self) -> bool:
        """Reconstructed but tied to no layer: the decoder will overwrite edits here."""
        return self.recon == 1 and sum(self.layers) == 0

    @classmethod
    def from_json(cls, payload: dict) -> "MapPosition":
        return cls(
            pos=payload["poz"],
            base=payload.get("wej", ""),
            change_to=payload.get("zmien_na", "."),
            recon=payload.get("rekon", 0),
            layers=list(payload.get("warstwy", [])),
            weight=payload.get("wagaP", 0.0),
        )


@dataclass
class SeqMap:
    species: str
    recon_fraction: float
    not_reconstructed: int
    changes_for_species: int
    reconstruction_error: int
    layer_distribution: dict[str, int]
    positions: list[MapPosition]
    compact: dict = field(repr=False, default_factory=dict)
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "SeqMap":
        return cls(
            species=payload.get("gatunek", ""),
            recon_fraction=payload.get("rekon_frakcja", 0.0),
            not_reconstructed=payload.get("nie_rekonstruuje", 0),
            changes_for_species=payload.get("zmian_pod_gatunek", 0),
            reconstruction_error=payload.get("blad_odtworzenia", 0),
            layer_distribution=payload.get("rozklad_warstw", {}),
            positions=[MapPosition.from_json(p) for p in payload.get("pozycje", [])],
            compact=payload.get("kompakt", {}),
            raw=payload,
        )

    @property
    def recommendations(self) -> list[MapPosition]:
        return [p for p in self.positions if p.is_recommendation]

    @property
    def free_positions(self) -> list[int]:
        return [p.pos for p in self.positions if p.is_free]

    @property
    def overwritten_positions(self) -> list[int]:
        return [p.pos for p in self.positions if p.is_overwritten]


@dataclass
class EditOption:
    nr: int
    sequence: str
    changes: list[dict] = field(repr=False, default_factory=list)

    @property
    def n_changes(self) -> int:
        return len(self.changes)

    @property
    def changed_positions(self) -> list[int]:
        """1-based positions this option moved relative to the decoded baseline."""
        return [c["poz"] for c in self.changes]

    @classmethod
    def from_json(cls, payload: dict) -> "EditOption":
        return cls(
            nr=payload.get("nr", 0),
            sequence=payload["sekwencja"],
            changes=list(payload.get("zmiany", [])),
        )


@dataclass
class Edits:
    layer: str
    slots: int
    alphabet: int
    reconstruction_error: int
    options: list[EditOption]
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "Edits":
        return cls(
            layer=payload.get("warstwa", ""),
            slots=payload.get("slotow", 0),
            alphabet=payload.get("alfabet", 0),
            reconstruction_error=payload.get("blad_rekonstrukcji_pozycji", 0),
            options=[EditOption.from_json(o) for o in payload.get("opcje", [])],
            raw=payload,
        )


@dataclass
class Verdict:
    stronger: str
    stronger_idx: int
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def b_wins(self) -> bool:
        return self.stronger_idx == 1

    @classmethod
    def from_json(cls, payload: dict) -> "Verdict":
        return cls(
            stronger=payload.get("silniejsza", ""),
            stronger_idx=payload.get("silniejsza_idx", 0),
            raw=payload,
        )


@dataclass
class Submission:
    scored: int
    top10_position: int | None
    top100_position: int | None
    points: float | None
    filtering: dict = field(default_factory=dict)
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "Submission":
        return cls(
            scored=payload.get("ocenionych", 0),
            top10_position=payload.get("pozycja_top10"),
            top100_position=payload.get("pozycja_top100"),
            points=payload.get("punkty_razem"),
            filtering=payload.get("filtrowanie", {}),
            raw=payload,
        )


@dataclass
class RankingRow:
    position: int
    team: str
    scored: int
    points_top10: float
    points_top100: float
    points: float
    uploaded_at: str | None

    @classmethod
    def from_json(cls, payload: dict) -> "RankingRow":
        return cls(
            position=payload.get("pozycja", 0),
            team=payload.get("druzyna", ""),
            scored=payload.get("ocenionych", 0),
            points_top10=payload.get("punkty_top10", 0.0),
            points_top100=payload.get("punkty_top100", 0.0),
            points=payload.get("punkty_razem", 0.0),
            uploaded_at=payload.get("wgranie_o"),
        )


@dataclass
class Ranking:
    teams: int
    started: int
    your_position: int | None
    tiebreak: str
    rows: list[RankingRow]
    raw: dict = field(repr=False, default_factory=dict)

    @classmethod
    def from_json(cls, payload: dict) -> "Ranking":
        return cls(
            teams=payload.get("n_druzyn", 0),
            started=payload.get("n_startujacych", 0),
            your_position=payload.get("twoja_pozycja"),
            tiebreak=payload.get("remis", ""),
            rows=[RankingRow.from_json(r) for r in payload.get("ranking", [])],
            raw=payload,
        )


class Api:
    """Endpoint-level facade; all rate limiting lives in the client's key pool."""

    def __init__(self, client: HyppeClient | None = None):
        self.client = client if client is not None else HyppeClient()

    @property
    def pool(self):
        return self.client.pool

    def me(self, key: ApiKey | None = None) -> Me:
        return Me.from_json(self.client.call("/me", key=key))

    def me_all(self) -> list[Me]:
        """Probe every key, which also syncs each key's upload cooldown."""
        states = []
        for key in self.pool.keys:
            state = self.me(key=key)
            if state.upload_in_s:
                self.pool.mark_upload(key, seconds=float(state.upload_in_s))
            states.append(state)
        return states

    def wild(self) -> Wild:
        return Wild.from_json(self.client.call("/dziki"))

    def map(self, sequence: str, start: int = 0, count: int = 800) -> SeqMap:
        payload = {"sekwencja": sequence, "od": start, "ile": count}
        return SeqMap.from_json(self.client.call("/nawigator/mapa", payload))

    def edits(
        self,
        sequence: str,
        level: int = 2,
        codes: int = 8,
        options: int = 8,
        seed: int | None = None,
    ) -> Edits:
        payload: dict[str, Any] = {
            "sekwencja": sequence,
            "poziom": level,
            "ile_kodow": codes,
            "opcji": options,
        }
        if seed is not None:
            payload["ziarno"] = seed
        return Edits.from_json(self.client.call("/nawigator/edycje", payload))

    def judge(self, a: str, b: str, name_a: str = "a", name_b: str = "b") -> Verdict:
        payload = {"a": a, "b": b, "nazwa_a": name_a, "nazwa_b": name_b}
        return Verdict.from_json(self.client.call("/sedzia", payload))

    def upload(self, fasta: str) -> Submission:
        return Submission.from_json(self.client.call("/wgraj", {"fasta": fasta}))

    def ranking(self) -> Ranking:
        return Ranking.from_json(self.client.call("/ranking"))

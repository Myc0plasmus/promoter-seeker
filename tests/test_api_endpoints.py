"""Live smoke of every hyppe endpoint, mirroring notebooks/Hackathon.ipynb §§5.1–5.9.

Run (needs network + keys in .env):

    uv run --group dev pytest tests/test_api_endpoints.py -m live -v

POST /wgraj uses data/Promotory.csv (100 natural promoters). Skips only when
every key is still inside the five-minute upload cooldown.
"""

from __future__ import annotations

import pytest

from promoter_seeker import Api
from promoter_seeker.api.keys import NoKeysError, load_keys
from promoter_seeker.config import SEQ_LENGTH, SUBMISSION_LIMIT
from promoter_seeker.seq import (
    SequenceChecker,
    build_fasta,
    filter_records,
    load_promoters,
)

pytestmark = pytest.mark.live


def _keys_available() -> bool:
    try:
        return bool(load_keys())
    except NoKeysError:
        return False


requires_keys = pytest.mark.skipif(
    not _keys_available(),
    reason="no hyppe_ keys in .env / HYPPE_KEYS",
)


@pytest.fixture(scope="module")
def api() -> Api:
    return Api()


@pytest.fixture(scope="module")
def wild_sequence(api: Api) -> str:
    wild = api.wild()
    assert wild.length == SEQ_LENGTH
    assert len(wild.sequence) == SEQ_LENGTH
    SequenceChecker.is_correct(wild.sequence)
    return wild.sequence


@requires_keys
class TestNotebookEndpointFlow:
    """Same order as the notebook practical section."""

    def test_01_me(self, api: Api) -> None:
        """GET /me — every key in the pool."""
        states = api.me_all()
        assert len(states) == len(api.pool)
        for me in states:
            assert me.team
            assert me.participant
            assert "/sedzia" in me.limits or "limity_na_minute" in me.raw
            assert me.upload_in_s >= 0

    def test_02_dziki(self, api: Api) -> None:
        """GET /dziki — wild-type pks1 promoter."""
        wild = api.wild()
        assert wild.gene == "pks1"
        assert wild.length == SEQ_LENGTH
        assert len(wild.sequence) == SEQ_LENGTH
        assert wild.sha256_12
        assert set(wild.sequence) <= set("ACGTN")
        SequenceChecker.is_correct(wild.sequence)

    def test_03_nawigator_mapa(self, api: Api, wild_sequence: str) -> None:
        """POST /nawigator/mapa — position map + P1 recommendations."""
        m = api.map(wild_sequence, start=0, count=SEQ_LENGTH)
        assert m.positions
        assert len(m.positions) == SEQ_LENGTH
        assert 0.0 <= m.recon_fraction <= 1.0
        assert m.layer_distribution
        for p in m.recommendations:
            assert 1 <= p.pos <= SEQ_LENGTH
            assert p.base in "ACGTN"
            assert p.change_to in "ACGTN"
            assert p.change_to != "."
        assert all(1 <= pos <= SEQ_LENGTH for pos in m.free_positions)

    def test_04_sedzia(self, api: Api, wild_sequence: str) -> None:
        """POST /sedzia — pairwise verdict (map-edited candidate vs wild)."""
        m = api.map(wild_sequence)
        candidate = list(wild_sequence)
        for p in m.recommendations:
            candidate[p.pos - 1] = p.change_to
        candidate_seq = "".join(candidate)
        SequenceChecker.is_correct(candidate_seq)

        verdict = api.judge(
            wild_sequence, candidate_seq, name_a="dziki", name_b="kandydat"
        )
        assert verdict.stronger_idx in (0, 1)
        assert verdict.stronger in ("dziki", "kandydat", verdict.raw.get("silniejsza", ""))

    def test_05_sedzia_vs_dataset(self, api: Api, wild_sequence: str) -> None:
        """POST /sedzia — wild vs first sequence from Promotory.csv (notebook §5.5)."""
        promoters = load_promoters()
        assert len(promoters) == 100
        first = promoters[0]
        assert len(first.sequence) == SEQ_LENGTH

        verdict = api.judge(
            wild_sequence,
            first.sequence,
            name_a="dziki",
            name_b=first.name,
        )
        assert verdict.stronger_idx in (0, 1)

    def test_06_nawigator_edycje(self, api: Api, wild_sequence: str) -> None:
        """POST /nawigator/edycje — latent edits (notebook §5.6, one round)."""
        edits = api.edits(
            wild_sequence, level=2, codes=8, options=8, seed=1000
        )
        assert edits.layer
        assert edits.slots > 0
        assert edits.options
        for opt in edits.options:
            assert len(opt.sequence) == SEQ_LENGTH
            SequenceChecker.is_correct(opt.sequence)
            assert opt.n_changes == len(opt.changes)
            for change in opt.changes:
                assert "poz" in change
                assert 1 <= change["poz"] <= SEQ_LENGTH

    def test_07_sedzia_batch(self, api: Api, wild_sequence: str) -> None:
        """POST /sedzia — several edit options vs wild (notebook §5.7, shortened)."""
        edits = api.edits(
            wild_sequence, level=2, codes=6, options=4, seed=42
        )
        wins = 0
        for opt in edits.options:
            verdict = api.judge(
                wild_sequence,
                opt.sequence,
                name_a="dziki",
                name_b=f"edycje_{opt.nr}",
            )
            assert verdict.stronger_idx in (0, 1)
            if verdict.b_wins:
                wins += 1
        assert wins >= 0  # any share is fine; we only need the calls to succeed

    def test_08_ranking(self, api: Api) -> None:
        """GET /ranking — scoreboard (notebook §5.9)."""
        board = api.ranking()
        assert board.teams >= 1
        assert board.rows
        positions = [row.position for row in board.rows]
        assert positions == sorted(positions)
        for row in board.rows:
            assert row.team
            assert row.points_top10 >= 0
            assert row.points_top100 >= 0

    @pytest.mark.upload
    def test_09_wgraj_promotory_csv(self, api: Api) -> None:
        """POST /wgraj — submit data/Promotory.csv as FASTA (notebook §5.8).

        The CSV already has 100 unique 800 bp sequences with no N, so local
        filters should pass everything. Skips only if every key is cooling down.
        """
        api.me_all()  # sync upload cooldowns from the server
        wait = api.pool.upload_ready_in()
        if wait > 0:
            pytest.skip(f"all keys still on upload cooldown ({wait:.0f}s left)")

        promoters = load_promoters()
        assert len(promoters) == 100
        records = [(p.name, p.sequence) for p in promoters]
        kept, report = filter_records(records, limit=SUBMISSION_LIMIT)
        assert report.clean, report.summary()
        assert len(kept) == SUBMISSION_LIMIT

        fasta = build_fasta(kept)
        submission = api.upload(fasta)
        assert submission.scored == SUBMISSION_LIMIT
        filt = submission.filtering
        assert filt.get("n_ocenianych", submission.scored) == SUBMISSION_LIMIT
        assert filt.get("odrzucone_dlugosc", 0) == 0
        assert filt.get("odrzucone_duplikaty", 0) == 0
        assert filt.get("odrzucone_alfabet", 0) == 0
        assert filt.get("odrzucone_N", 0) == 0

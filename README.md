# Promoter Seeker

Rozwiązanie drużyny na hackathon **Hack the Promoter** (iGEM Warsaw 2026).
Cel: zaprojektować silny promotor dla genu `pks1` w *Trichoderma atroviride* szczep P1
(kategoria antagonizmu biotycznego / produkcja 6PP).

Logika z notebooka `notebooks/Hackathon.ipynb` jest przeniesiona do pakietu
`src/promoter_seeker/` — klient API, walidacja sekwencji, FASTA i dataset.

## Środowisko

```sh
uv sync
source .venv/bin/activate
```

Klucze API trzymamy w `.env` (plik jest w `.gitignore`). Format: jedna linia = jeden klucz,
bez `KLUCZ=`:

```
hyppe_...
hyppe_...
```

Opcjonalnie: `HYPPE_KEYS=klucz1,klucz2` w środowisku. Pakiet ładuje wszystkie klucze i
rotuje je (round-robin), więc limity Sędziego/Nawigatora i sloty `/wgraj` mnożą się
przez liczbę kluczy.

## Zadanie w skrócie

| Wymaganie | Wartość |
|---|---|
| Długość | dokładnie **800 pz** |
| Alfabet | `ACGTN` |
| Udział `N` | najwyżej **10%** (≤ 80 pozycji) |
| Unikalność | w obrębie pliku FASTA |
| Ocena | pierwsze **100** sekwencji w pliku |
| Wgranie | `POST /wgraj`, raz na **5 min** na klucz |

Punktacja automatyczna (50% oceny końcowej):

- **25%** — średnia 10 najlepszych (TOP10), rangowo między drużynami
- **25%** — średnia wszystkich 100 (ALL100), rangowo

Pozostałe 50% to prezentacja przed Jury.

API: `https://hyppe.futura.foundation`, nagłówek `X-API-Key`.
Trzy role modelu: **Sędzia** (para → silniejsza), **Nawigator** (mapa / edycje),
**Wyrocznia** (tylko Jury, ocena punktowa).

### Endpointy

| Metoda | Ścieżka | Opis | Limit |
|---|---|---|---|
| `GET` | `/dziki` | promotor wyjściowy `pks1`, 800 pz | bez limitu |
| `POST` | `/sedzia` | para sekwencji → silniejsza | 600/min |
| `POST` | `/nawigator/mapa` | mapa pozycji | 600/min |
| `POST` | `/nawigator/edycje` | propozycje edycji latentu | 600/min |
| `POST` | `/wgraj` | zgłoszenie FASTA | raz / 5 min |
| `GET` | `/ranking` | tablica punktów | bez limitu |
| `GET` | `/me` | stan klucza, limity | bez limitu |

## Struktura pakietu

```
src/promoter_seeker/
  config.py          # URL, ścieżki, stałe (800 pz, limity, …)
  api/
    keys.py          # KeyPool — 4 klucze, rotacja, cooldown /wgraj
    client.py        # HyppeClient — retry, backoff, User-Agent
    endpoints.py     # Api — typowane me/dziki/mapa/edycje/sedzia/wgraj/ranking
  seq/
    validate.py      # filtry serwera (kolejność + limit 100)
    fasta.py         # budowa / parsowanie FASTA
    dataset.py       # data/Promotory.csv
  utils/
    sequence_checker.py   # reguły per sekwencja (długość, alfabet, N)
```

## Szybki start

```python
from promoter_seeker import Api

api = Api()

# stan wszystkich kluczy + sync cooldownów wgrywania
for me in api.me_all():
    print(me.team, me.participant, me.upload_in_s)

# promotor wyjściowy
wild = api.wild()
print(wild.name, wild.gene, wild.length, wild.sha256_12)
DZIKI = wild.sequence
```

### Nawigator: mapa

`POST /nawigator/mapa` opisuje każdą pozycję. Pozycje są **1-based** (jak w API).

| pole | znaczenie |
|---|---|
| `recon` | `1` = pozycja odtwarza się z kodów, `0` = swobodna |
| `layers` | które warstwy (L1/L2/L3) ruszają tę pozycję |
| `change_to` | zasada pod P1; `.` = bez zmiany |
| `weight` | znormalizowana waga gradientu |

```python
m = api.map(DZIKI)
print(m.species, m.recon_fraction, m.layer_distribution)
print("rekomendacje:", [(p.pos, p.base, p.change_to) for p in m.recommendations])
print("swobodne:", m.free_positions[:15])
print("nadpisze dekoder:", m.overwritten_positions[:15])

# kandydat z rekomendacji mapy
kandydat = list(DZIKI)
for p in m.recommendations:
    kandydat[p.pos - 1] = p.change_to
kandydat = "".join(kandydat)
```

### Sędzia: porównanie parowe

```python
v = api.judge(DZIKI, kandydat, name_a="dziki", name_b="kandydat")
print(v.stronger, v.stronger_idx, "b wygrywa:", v.b_wins)
```

Sędzia nie ma odstępu między wywołaniami (tylko limit 600/min na klucz).
`KeyPool` rozkłada ruch na wszystkie klucze i czeka, zamiast zbierać 429.

### Nawigator: edycje

Poziomy latentu:

| poziom | warstwa | slotów | bp/slot | alfabet |
|---|---|---|---|---|
| 0 | L1 | 50 | 16 | 4 |
| 1 | L2 | 200 | 4 | 8 |
| 2 | L3 | 400 | 2 | 4 |

```python
e = api.edits(DZIKI, level=2, codes=8, options=8, seed=1000)
print(e.layer, e.slots, e.alphabet)
for o in e.options:
    print(o.nr, o.n_changes, o.changed_positions[:5], len(o.sequence))
```

`zmiany` w odpowiedzi API to lista `{poz, z, na}`, nie liczba —
`EditOption.n_changes` / `changed_positions` to gotowe widoki.

### Zbiór 100 naturalnych promotorów

Plik `data/Promotory.csv` (separator `;`): 100 promotorów z 19 gatunków/szczepów
*Trichoderma*, każdy 800 pz, bez `N`. **To nie jest zestaw dobrych odpowiedzi** —
materiał do porównań i motywów.

```python
from promoter_seeker.seq import load_promoters, species_counts

promoters = load_promoters()
print(len(promoters), species_counts(promoters))
```

Genom referencyjny P1 (opcjonalnie):  
[GCF_020647795.1](https://www.ncbi.nlm.nih.gov/datasets/genome/GCF_020647795.1/)
— lokalnie w `data/*.gbff`.

### Walidacja przed wgraniem

Lokalne filtry lustrzane względem serwera. Zły plik kosztuje sekundę, nie 5 minut cooldownu.

```python
from promoter_seeker.seq import (
    SequenceChecker,
    filter_records,
    build_fasta,
    is_valid,
    problems,
)

SequenceChecker.is_correct(DZIKI)          # True albo ValueError
problems("ACGT")                           # lista wszystkich naruszeń
is_valid(DZIKI)                            # bool (quiet)

kept, report = filter_records([
    ("a", DZIKI),
    ("b", kandydat),
    # ... do 100
])
print(report.summary())
fasta = build_fasta(kept)
```

Kolejność jak na serwerze: długość → duplikaty → alfabet → próg N → pierwsze 100.

### Wgranie i ranking

```python
# raz na 5 minut na klucz — pool ma 4 niezależne sloty
sub = api.upload(fasta)
print(sub.scored, sub.top10_position, sub.top100_position, sub.points)
print(sub.filtering)

r = api.ranking()
print("wasza pozycja:", r.your_position)
for row in r.rows:
    print(row.position, row.team, row.points_top10, row.points_top100, row.points)
```

## Konfiguracja (opcjonalne zmienne)

| zmienna | domyślnie | znaczenie |
|---|---|---|
| `HYPPE_KEYS` | zawartość `.env` | lista kluczy |
| `PS_API_URL` | `https://hyppe.futura.foundation` | baza API |
| `PS_DATA_DIR` | `data/` | katalog danych |
| `PS_PROMOTERS_CSV` | `data/Promotory.csv` | zbiór 100 |
| `PS_ENV_FILE` | `.env` | plik z kluczami |
| `PS_RUNS_DIR` | `runs/` | stan pipeline'u (kolejne kroki) |

## Kody błędów API

| kod | znaczenie |
|---|---|
| 401 | brak `X-API-Key` |
| 403 | klucz nieznany / wygasły / endpoint jury |
| 422 | sekwencja ≠ 800 pz, znaki poza `ACGTN` lub >10% `N` |
| 429 | limit na minutę / dzienny / 5 min od wgrania |
| 503 | kolejka GPU — klient ponawia automatycznie |
| `error code: 1010` | brak `User-Agent` (Cloudflare) |

## Testy API

Live smoke wszystkich endpointów (jak §§5.1–5.9 w notebooku):

```sh
uv sync --group dev
uv run --group dev pytest tests/test_api_endpoints.py -m live -v
```

`POST /wgraj` wgrywa `data/Promotory.csv` (100 sekwencji). Pomija się tylko, gdy
wszystkie klucze są jeszcze w cooldownie 5 min.

## Uwagi

- Liczy się **najlepsze** zgłoszenie drużyny, nie ostatnie.
- Plik z <100 sekwencjami nie jest odrzucany, ale ALL100 ma stały dzielnik 100 —
  50 sekwencji ≈ połowa punktów w tej kategorii.
- Model nie był walidowany mokro — wynik to ranking względem Wyroczni, nie gwarancja
  aktywności w laboratorium.
- Notebook `notebooks/Hackathon.ipynb` zostaje jako dokumentacja zadania;
  do pracy używamy pakietu powyżej.

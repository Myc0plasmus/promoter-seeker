from ..config import ALPHABET, MAX_N_FRACTION, SEQ_LENGTH

CORRECT_LENGTH = SEQ_LENGTH
N_CONTENT_PERCENTAGE_THRESHOLD = MAX_N_FRACTION * 100
SYMBOLS_POOL = ["A", "C", "G", "T", "N"]


class SequenceChecker:
    """
    Klasa odpowiedzialna za walidację sekwencji DNA pod kątem wymaganych standardów.

    Wymagania dotyczące sekwencji:
    - mieć dokładnie 800 pz,
    - składać się ze znaków ACGTN,
    - zawierać najwyżej 10% 'N',
    - być unikalna w obrębie pliku (sprawdzane zewnętrznie).

    Unikalność, kolejność filtrów serwera i limit 100 sekwencji obsługuje
    `promoter_seeker.seq.validate.filter_records`, które wywołuje tę klasę
    dla każdej sekwencji osobno. Progi pochodzą z `promoter_seeker.config`,
    więc obie warstwy nie mogą się rozjechać.

    Sekwencja jest sprawdzana bez normalizacji: małe litery zostaną odrzucone
    przez `is_correct_symbol`. Do wyrównania wielkości znaków służy
    `promoter_seeker.seq.validate.normalize`.

    Usage:
        >>> sample_seq = "ATCG..." # sekwencja o długości 800
        >>> is_valid = SequenceChecker.is_correct(sample_seq)
        >>> print(is_valid)
        True
    """

    @staticmethod
    def is_correct_length(seq: str) -> None:
        if len(seq) != CORRECT_LENGTH:
            raise ValueError(
                f"Niepoprawna długość sekwencji: ma {len(seq)} pz, a wymagane jest dokładnie {CORRECT_LENGTH} pz."
            )

    @staticmethod
    def is_correct_symbol(seq: str) -> None:
        for i, symbol in enumerate(seq, 1):
            if symbol not in ALPHABET:
                raise ValueError(
                    f"Niedozwolony znak '{symbol}' na pozycji {i}. Dozwolone znaki to: {SYMBOLS_POOL}"
                )

    @staticmethod
    def is_correct_content(seq: str) -> None:
        if len(seq) == 0:
            raise ValueError("Sekwencja jest pusta.")

        n_percentage = (seq.count("N") / len(seq)) * 100
        if n_percentage > N_CONTENT_PERCENTAGE_THRESHOLD:
            raise ValueError(
                f"Zbyt duża zawartość znaków 'N': {n_percentage:.2f}%. "
                f"Dopuszczalne maksimum to {N_CONTENT_PERCENTAGE_THRESHOLD:g}%."
            )

    @staticmethod
    def is_correct(seq: str, quiet: bool = False) -> bool:
        try:
            SequenceChecker.is_correct_length(seq)
            SequenceChecker.is_correct_symbol(seq)
            SequenceChecker.is_correct_content(seq)
            return True
        except ValueError as e:
            if not quiet:
                raise e
            return False

    @staticmethod
    def problems(seq: str) -> list[str]:
        """Wszystkie naruszenia naraz, nie tylko pierwsze. Pusta lista = sekwencja przejdzie.

        Przydatne przy poprawianiu wygenerowanych kandydatów, gdzie jedno
        zgłoszenie na wywołanie wymuszałoby wielokrotne przebiegi.
        """
        found = []
        for check in (
            SequenceChecker.is_correct_length,
            SequenceChecker.is_correct_symbol,
            SequenceChecker.is_correct_content,
        ):
            try:
                check(seq)
            except ValueError as e:
                found.append(str(e))
        return found

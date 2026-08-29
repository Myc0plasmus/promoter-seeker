CORRECT_LENGTH = 800
N_CONTENT_PERCENTAGE_THRESHOLD = 10
SYMBOLS_POOL = ["A", "C", "G", "T", "N"]


class SequenceChecker:
    """
    Klasa odpowiedzialna za walidację sekwencji DNA pod kątem wymaganych standardów.

    Wymagania dotyczące sekwencji:
    - mieć dokładnie 800 pz,
    - składać się ze znaków ACGTN,
    - zawierać najwyżej 10% 'N',
    - być unikalna w obrębie pliku (sprawdzane zewnętrznie).

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
        for i, symbol in enumerate(seq):
            if symbol not in SYMBOLS_POOL:
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
                f"Zbyt duża zawartość znaków 'N': {n_percentage:.2f}%. Dopuszczalne maksimum to {N_CONTENT_PERCENTAGE_THRESHOLD}%."
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

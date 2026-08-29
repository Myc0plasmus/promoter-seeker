import random

IUPAC = {
    "R": "AG",
    "Y": "CT",
    "S": "GC",
    "W": "AT",
    "K": "GT",
    "M": "AC",
    "B": "CGT",
    "D": "AGT",
    "H": "ACT",
    "V": "ACG",
    "N": "N",
}

def randomize_iupac(sequence):
    return "".join(
        random.choice(IUPAC.get(base.upper(), base))
        for base in sequence
    )

def limit_ns(sequence, max_n_fraction=0.10):
    sequence = sequence.upper()

    n_positions = [
        i for i, base in enumerate(sequence)
        if base == "N"
    ]

    max_ns = int(len(sequence) * max_n_fraction)

    if len(n_positions) <= max_ns:
        return sequence

    positions_to_replace = random.sample(
        n_positions,
        len(n_positions) - max_ns
    )

    sequence = list(sequence)

    for i in positions_to_replace:
        sequence[i] = random.choice("ACGT")

    return "".join(sequence)

import pandas as pd
from pandas import DataFrame
from pathlib import Path
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO


def species_promoter_fasta_factory(query: str) -> None:
    path = Path.cwd() / "data/Promotory.csv"
    df: DataFrame = pd.read_csv(path,sep=";")
    species_specific = df[df["gatunek"].str.contains(query, na=False)]
    
    records = [
        SeqRecord(Seq(row["sekwencja"]), id=str(row["nazwa"]), description="")
        for _, row in species_specific.iterrows()
    ]

    SeqIO.write(records, f"{query.replace(" ", "_")}_sequences.fasta", "fasta")

if __name__ == "__main__":
    species_promoter_fasta_factory("Trichoderma atroviride")



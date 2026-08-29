import pandas as pd
from pandas import DataFrame
from pathlib import Path
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
import numpy as np


def length_checker(query: str) -> None:
    path = Path.cwd() / "data/Promotory.csv"
    df: DataFrame = pd.read_csv(path,sep=";")
    print(np.unique(df["dlugosc"]))   

if __name__ == "__main__":
    length_checker("Trichoderma atroviride")



import pandas as pd
from pathlib import Path


def main():
    path = Path.cwd() / "promotory.csv"
    df = pd.read_csv(path,sep=";")
    print(df)


if __name__ == "__main__":
    main()

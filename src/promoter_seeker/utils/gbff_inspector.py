from Bio import SeqIO
import numpy as np
from pathlib import Path

gbff_file = Path.cwd() / "data/GCF_020647795.1_ASM2064779v1_genomic.gbff"

records = SeqIO.parse(gbff_file, "genbank")

for record in SeqIO.parse(gbff_file, "genbank"):

    for feature in record.features:

        if feature.type == "CDS":

            gene = feature.qualifiers.get("gene", [None])[0]
            product = feature.qualifiers.get("product", [None])[0]
            protein_id = feature.qualifiers.get("protein_id", [None])[0]

            print(
                gene,
                product,
                protein_id,
                feature.location
            )

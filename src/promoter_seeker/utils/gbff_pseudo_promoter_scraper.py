from Bio import SeqIO
from pathlib import Path

gbff_file = Path.cwd() / "data/GCF_020647795.1_ASM2064779v1_genomic.gbff"
size = 4000
current_size = 0
output_file = Path.cwd() / f"data/upstream_800bp_size_{size}.fasta"


with open(output_file, "w") as fasta:

    for record in SeqIO.parse(gbff_file, "genbank"):
        for feature in record.features:
            current_size +=1
            if current_size > size:
                break

            if feature.type != "CDS":
                continue

            gene = feature.qualifiers.get("gene", [None])[0]
            product = feature.qualifiers.get("product", [None])[0]
            protein_id = feature.qualifiers.get("protein_id", [None])[0]

            start = int(feature.location.start)
            end = int(feature.location.end)
            strand = feature.location.strand

            # Get 800 bp upstream, respecting strand
            if strand == 1:
                upstream_start = max(0, start - 800)
                upstream_end = start

                upstream_seq = record.seq[upstream_start:upstream_end]

            elif strand == -1:
                upstream_start = end
                upstream_end = min(len(record.seq), end + 800)

                upstream_seq = record.seq[upstream_start:upstream_end].reverse_complement()

            else:
                continue

            # Make a safe FASTA ID
            gene_id = gene or protein_id or f"CDS_{start}"

            fasta_id = (
                f"{record.id}|{gene_id}"
            )

            fasta.write(f">{fasta_id}\n")

            # Wrap sequence at 80 characters
            sequence = str(upstream_seq)

            for i in range(0, len(sequence), 80):
                fasta.write(sequence[i:i+80] + "\n")

print(f"Written to: {output_file}")

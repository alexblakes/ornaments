from pathlib import Path


def test_conversion_on_bundled_annotation(tmp_path):
    from ornaments.convert import cli
    examples = Path(__file__).resolve().parents[1] / 'examples'
    output, coordinates = tmp_path / 'out.vcf', tmp_path / 'coords.tsv'
    assert cli(['-v', str(examples / 'truncated_chr1.vcf.gz'),
                '-g', str(examples / 'truncated_v36.annotation.gtf'),
                '-t', str(examples / 'truncated_transcriptome.fasta'),
                '-o', str(output), '-c', str(coordinates)]) == 0
    records = [row for row in output.read_text().splitlines() if not row.startswith('#')]
    assert records
    assert coordinates.read_text().startswith('CHR\tGENOME_POS\tTRANSCRIPT')

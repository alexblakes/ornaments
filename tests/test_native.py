from pathlib import Path
import subprocess
import pytest


def test_native_format_and_path_spaces(tmp_path):
    from ornaments import native
    engine = Path(native.__file__).parent / '_bin' / 'ornaments'
    if not engine.is_file():
        pytest.skip('Native integration requires the installed package')
    examples = Path(__file__).resolve().parents[1] / 'examples'
    def quantify(vcf, output):
        result = subprocess.run([str(engine), 'quant', '-i', str(examples / 'HG00405.ornament.index'),
            '-o', str(output), '--vcf', str(vcf), '--sample', 'HG00405',
            str(examples / 'HG00405_1.fastq'), str(examples / 'HG00405_2.fastq')], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert 'Sample index found' in result.stderr
        return (output / 'allele_counts.txt').read_text()
    expected = quantify(examples / 'sorted.transcriptome.vcf', tmp_path / 'baseline')
    variant = tmp_path / 'variants with spaces.vcf'
    rows = []
    for row in (examples / 'sorted.transcriptome.vcf').read_text().splitlines():
        if not row.startswith('#'):
            fields = row.split('\t')
            fields[8] = 'DP:GT'
            fields[9:] = ['8:' + value.split(':')[0] for value in fields[9:]]
            row = '\t'.join(fields)
        rows.append(row)
    variant.write_text('\n'.join(rows) + '\n')
    assert quantify(variant, tmp_path / 'with-fields') == expected


def test_native_gzip_vcf_matches_plain(tmp_path):
    import gzip
    from ornaments import native
    engine = Path(native.__file__).parent / '_bin' / 'ornaments'
    if not engine.is_file():
        pytest.skip('Requires installed native engine')
    examples = Path(__file__).resolve().parents[1] / 'examples'
    compressed = tmp_path / 'sorted.vcf.gz'
    with gzip.open(compressed, 'wt') as stream:
        stream.write((examples / 'sorted.transcriptome.vcf').read_text())
    counts = []
    for vcf, name in [(examples / 'sorted.transcriptome.vcf', 'plain'), (compressed, 'gzip')]:
        output = tmp_path / name
        result = subprocess.run([str(engine), 'quant', '-i', str(examples / 'HG00405.ornament.index'),
            '-o', str(output), '--vcf', str(vcf), '--sample', 'HG00405',
            str(examples / 'HG00405_1.fastq'), str(examples / 'HG00405_2.fastq')], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        counts.append((output / 'allele_counts.txt').read_text())
    assert counts[0] and counts[1] == counts[0]


@pytest.mark.parametrize('case', ['missing-header', 'missing-sample-gzip'])
def test_native_invalid_vcf_fails(tmp_path, case):
    import gzip
    from ornaments import native
    engine = Path(native.__file__).parent / '_bin' / 'ornaments'
    if not engine.is_file():
        pytest.skip('Requires installed native engine')
    examples = Path(__file__).resolve().parents[1] / 'examples'
    vcf = tmp_path / 'bad.vcf.gz'
    with gzip.open(vcf, 'wt') as stream:
        stream.write('not a VCF\n' if case == 'missing-header' else
                     (examples / 'sorted.transcriptome.vcf').read_text())
    result = subprocess.run([str(engine), 'quant', '-i', str(examples / 'HG00405.ornament.index'),
        '-o', str(tmp_path / 'result'), '--vcf', str(vcf), '--sample', 'MISSING',
        str(examples / 'HG00405_1.fastq'), str(examples / 'HG00405_2.fastq')], capture_output=True, text=True)
    assert result.returncode != 0
    assert 'VCF' in result.stderr or 'vcf' in result.stderr

import pytest


def inputs(tmp_path, sample_fields='A\tB'):
    vcf, fasta = tmp_path / 'variants.vcf', tmp_path / 'ref.fa'
    vcf.write_text('##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t' + sample_fields + '\n')
    fasta.write_text('>tx\n' + 'ACGT' * 25 + '\n')
    return ['-f', str(fasta), '-v', str(vcf), '-o', str(tmp_path / 'out.fa')], vcf


def test_all_resolves_samples_and_writes_fasta(tmp_path):
    from ornaments.personalize import cli
    args, _ = inputs(tmp_path)
    assert cli(args + ['-t', 'ornament', '-s', 'ALL']) == 0
    assert (tmp_path / 'out.fa').read_text().startswith('>tx\n')


@pytest.mark.parametrize('extra', [
    ['-t', 'ornament', '-s', 'MISSING'],
    ['-t', 'ornament', '-s', 'A,A'],
    ['-t', 'diploid', '-s', 'A'],
    ['-t', 'diploid', '-s', 'A,B', '-c', 'coords.tsv'],
    ['-t', 'ornament', '-s', 'A', '-k', '2'],
    ['-t', 'ornament', '-s', 'A', '-k', '33'],
    ['-t', 'ornament', '-s', 'A', '-k', '1'],
])
def test_invalid_personalization_does_not_create_output(tmp_path, extra):
    from ornaments.personalize import cli
    args, _ = inputs(tmp_path)
    with pytest.raises(SystemExit) as result:
        cli(args + extra)
    assert result.value.code != 0
    assert not (tmp_path / 'out.fa').exists()


def test_diploid_coordinate_output(tmp_path):
    from ornaments.personalize import cli
    args, _ = inputs(tmp_path)
    coords = tmp_path / 'coords.tsv'
    assert cli(args + ['-t', 'diploid', '-s', 'A', '-c', str(coords)]) == 0
    text = (tmp_path / 'out.fa').read_text()
    assert '>tx_L\n' in text and '>tx_R\n' in text
    assert coords.exists()


def test_genotype_format_fields_are_read(tmp_path):
    from ornaments.personalize import cli
    args, vcf = inputs(tmp_path, 'A')
    with vcf.open('a') as stream:
        stream.write('tx\t2\t.\tC\tT\t.\t.\t.\tDP:GT\t8:1|1\n')
    assert cli(args + ['-t', 'ornament', '-s', 'A']) == 0
    text = (tmp_path / 'out.fa').read_text()
    assert 'ATGT' in text


def test_personalize_rejects_output_alias(tmp_path):
    from ornaments.personalize import cli
    args, vcf = inputs(tmp_path)
    args[args.index('-o')+1] = str(vcf)
    with pytest.raises(ValueError, match='same'):
        cli(args + ['-t', 'ornament', '-s', 'A'])

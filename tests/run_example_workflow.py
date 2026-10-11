"""Run every stage on the bundled data using an installed CLI."""
import argparse
import math
from pathlib import Path
import shutil
import subprocess
import tempfile


def invoke(cli, *args):
    subprocess.run([str(cli), *map(str, args)], check=True)


def workflow(cli, source, output):
    examples = source / 'examples'
    converted, coords = output / 'converted.vcf', output / 'conversion.tsv'
    merged, sorted_vcf = output / 'merged.vcf', output / 'sorted.vcf'
    fasta, index = output / 'ornament.fa', output / 'ornament.index'
    file_list = output / 'files.txt'
    invoke(cli, 'convert', '-v', examples / 'truncated_chr1.vcf.gz',
           '-g', examples / 'truncated_v36.annotation.gtf',
           '-t', examples / 'truncated_transcriptome.fasta', '-o', converted, '-c', coords)
    file_list.write_text(str(converted) + '\n')
    invoke(cli, 'merge', '-i', file_list, '-s', 'HG00405', '-o', merged)
    invoke(cli, 'sort', '-i', merged, '-o', sorted_vcf, '--chunk-size', '2')
    lines = sorted_vcf.read_text().splitlines()
    keys = [(row.split('\t')[0], int(row.split('\t')[1])) for row in lines if not row.startswith('#')]
    assert keys and keys == sorted(keys)
    assert next(row for row in lines if row.startswith('#CHROM')).endswith('\tHG00405')
    invoke(cli, 'personalize', '-f', examples / 'truncated_transcriptome.fasta',
           '-v', sorted_vcf, '-t', 'ornament', '-o', fasta, '-s', 'HG00405')
    invoke(cli, 'index', '-i', index, fasta)
    assert fasta.stat().st_size > 0 and index.stat().st_size > 0
    for mode in ('paired', 'single'):
        quant = output / mode
        reads = [examples / 'HG00405_1.fastq', examples / 'HG00405_2.fastq'] if mode == 'paired' else ['--single', '-l', '150', '-s', '25', examples / 'HG00405.fastq']
        invoke(cli, 'quant', '-i', index, '-o', quant, '--vcf', sorted_vcf,
               '--sample', 'HG00405', *reads)
        for filename in ('allele_counts.txt', 'tpms.txt', 'thetas.txt'):
            path = quant / filename
            assert path.is_file() and path.stat().st_size > 0, path
        # Native abundance tables have transcript names and numeric values.
        for filename in ('tpms.txt', 'thetas.txt'):
            for row in (quant / filename).read_text().splitlines():
                if row.startswith('#') or row.strip() in ('', '{', '}'):
                    continue
                value = float(row.split()[-1].rstrip(','))
                assert math.isfinite(value) and value >= 0, row
    diploid, diploid_coords = output / 'diploid.fa', output / 'diploid.coords'
    invoke(cli, 'personalize', '-f', examples / 'truncated_transcriptome.fasta',
           '-v', sorted_vcf, '-t', 'diploid', '-o', diploid, '-s', 'HG00405', '-c', diploid_coords)
    headers = [line for line in diploid.read_text().splitlines() if line.startswith('>')]
    assert any(line.endswith('_L') for line in headers) and any(line.endswith('_R') for line in headers)
    assert diploid_coords.is_file()
    print('Verified conversion, merge, sorting, ornament and diploid generation, index, paired and single quantification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', default=shutil.which('ornaments'))
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.cli:
        parser.error('Install ornaments first or supply --cli')
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        workflow(args.cli, args.source.resolve(), args.output.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='ornaments example ') as temporary:
            workflow(args.cli, args.source.resolve(), Path(temporary))


if __name__ == '__main__':
    main()

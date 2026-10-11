"""Concatenate transcriptomic VCF records with ordered sample projection."""
import argparse
from pathlib import Path
import re
from .vcf import atomic_output, distinct_outputs, open_text, read_header, record_fields


def merge_vcfs(paths: list[str], output: str, samples: list[str]) -> None:
    if not paths:
        raise ValueError('The input file list is empty')
    distinct_outputs(paths, [output])
    headers, metadata, definitions = [], [], {}
    for path in paths:
        with open_text(path) as stream:
            meta, columns, number = read_header(stream, path)
        if not samples:
            samples = columns[9:]
        if not samples or len(set(samples)) != len(samples) or any(not s for s in samples):
            raise ValueError('Select at least one sample; names must be unique and nonempty')
        missing = [s for s in samples if s not in columns[9:]]
        if missing:
            raise ValueError(f'{path}: samples absent from VCF: {", ".join(missing)}')
        headers.append((columns, [columns.index(s, 9) for s in samples]))
        for line in meta:
            match = re.match(r'##([^=]+)=<ID=([^,>]+)', line)
            key = match.groups() if match else ('fileformat', '') if line.startswith('##fileformat=') else None
            if key and key in definitions and definitions[key] != line:
                raise ValueError(f'{path}: conflicting metadata definition {key}')
            if key:
                definitions[key] = line
            if line not in metadata:
                metadata.append(line)
    with atomic_output(output) as target:
        for line in metadata:
            target.write(line + '\n')
        target.write('\t'.join(headers[0][0][:9] + samples) + '\n')
        for path, (columns, indices) in zip(paths, headers):
            with open_text(path) as stream:
                _, _, number = read_header(stream, path)
                for number, line in enumerate(stream, number + 1):
                    fields = record_fields(line, path, number, len(columns))
                    target.write('\t'.join(fields[:9] + [fields[i] for i in indices]) + '\n')


def cli(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--in-files', required=True, help='File listing input VCF paths, one per line (relative to the working directory)')
    parser.add_argument('-o', '--outfile', required=True)
    parser.add_argument('-s', '--sample-file', required=True, help='Sample name or file of sample names, one per line; an empty file selects all samples')
    args = parser.parse_args(argv)
    paths = [line.strip() for line in Path(args.in_files).read_text().splitlines() if line.strip()]
    sample_path = Path(args.sample_file)
    samples = [s.strip() for s in sample_path.read_text().splitlines() if s.strip()] if sample_path.is_file() else [args.sample_file]
    distinct_outputs([args.in_files, *([args.sample_file] if sample_path.is_file() else [])], [args.outfile])
    merge_vcfs(paths, args.outfile, samples)
    return 0

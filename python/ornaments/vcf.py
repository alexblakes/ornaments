"""VCF text, header validation, and safe output helpers."""
from contextlib import contextmanager
import gzip
import os
from pathlib import Path
import tempfile

COLUMNS = ['#CHROM', 'POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO']


def open_text(path, mode='rt'):
    return (gzip.open if str(path).endswith('.gz') else open)(path, mode, encoding='utf-8')


def distinct_outputs(inputs, outputs):
    paths = [Path(p).resolve() for p in inputs]
    seen = set()
    for output in outputs:
        path = Path(output).resolve()
        if path in paths or path in seen or any(path.exists() and p.exists() and os.path.samefile(path, p) for p in paths):
            raise ValueError(f'Input and output paths must not refer to the same file: {output}')
        seen.add(path)
        paths.append(path)


def read_header(stream, path):
    metadata = []
    for number, line in enumerate(stream, 1):
        if line.startswith('##'):
            metadata.append(line.rstrip('\r\n'))
        elif line.startswith('#CHROM\t'):
            columns = line.rstrip('\r\n').split('\t')
            if columns[:8] != COLUMNS or (len(columns) > 8 and columns[8] != 'FORMAT'):
                raise ValueError(f'{path}: malformed VCF column header')
            samples = columns[9:]
            if len(set(samples)) != len(samples) or any(not s for s in samples):
                raise ValueError(f'{path}: empty or duplicate sample names')
            return metadata, columns, number
        else:
            raise ValueError(f'{path}: expected VCF header at line {number}')
    raise ValueError(f'{path}: missing #CHROM header')


def read_samples(path):
    with open_text(path) as stream:
        return read_header(stream, path)[1][9:]


def record_fields(line, path, number, columns):
    fields = line.rstrip('\r\n').split('\t')
    if len(fields) != columns or len(fields) < 8 or not fields[0]:
        raise ValueError(f'{path}: malformed VCF record at line {number}')
    try:
        # Ornaments represents transcript-start deletions with REF='.' and
        # a numeric ALT length; their transcript coordinates can be <= 0.
        edge_deletion = fields[3] == '.' and fields[4].isdigit() and int(fields[4]) > 0
        if int(fields[1]) < 1 and not edge_deletion:
            raise ValueError()
    except ValueError:
        raise ValueError(f'{path}: invalid VCF position at line {number}') from None
    return fields


@contextmanager
def atomic_output(path):
    """Replace the destination only after successfully writing all output."""
    destination = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.ornaments-', suffix='.gz' if str(path).endswith('.gz') else '', dir=destination.parent)
    os.close(fd)
    try:
        with open_text(temporary, 'wt') as stream:
            yield stream
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

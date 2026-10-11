"""Stable transcript/position sorting using bounded-memory temporary runs."""
import argparse
from contextlib import ExitStack
import heapq
import json
from pathlib import Path
import tempfile
from .vcf import atomic_output, distinct_outputs, open_text, read_header, record_fields


def sort_vcf(input_path: str, output_path: str, *, temp_dir=None, chunk_size=100000) -> None:
    if chunk_size < 1:
        raise ValueError('Chunk size must be positive')
    distinct_outputs([input_path], [output_path])
    with tempfile.TemporaryDirectory(prefix='ornaments-sort-', dir=temp_dir) as scratch:
        chunks, records = [], []
        def flush():
            path = Path(scratch) / str(len(chunks))
            with path.open('w') as stream:
                for record in sorted(records):
                    stream.write(json.dumps(record) + '\n')
            chunks.append(path)
            records.clear()
        with open_text(input_path) as source:
            metadata, columns, header_line = read_header(source, input_path)
            for ordinal, line in enumerate(source):
                fields = record_fields(line, input_path, header_line + ordinal + 1, len(columns))
                records.append((fields[0], int(fields[1]), ordinal, line.rstrip('\r\n') + '\n'))
                if len(records) >= chunk_size:
                    flush()
            if records:
                flush()
        # Consolidate runs in batches to bound open file descriptors as well as RAM.
        generation = 0
        while len(chunks) > 64:
            merged = []
            for offset in range(0, len(chunks), 64):
                path = Path(scratch) / f'merged-{generation}-{offset}'
                with ExitStack() as stack, path.open('w') as target:
                    runs = [map(json.loads, stack.enter_context(p.open())) for p in chunks[offset:offset + 64]]
                    for record in heapq.merge(*runs):
                        target.write(json.dumps(record) + '\n')
                for old in chunks[offset:offset + 64]:
                    old.unlink()
                merged.append(path)
            chunks = merged
            generation += 1
        with atomic_output(output_path) as target, ExitStack() as stack:
            for line in metadata:
                target.write(line + '\n')
            target.write('\t'.join(columns) + '\n')
            runs = [map(json.loads, stack.enter_context(path.open())) for path in chunks]
            for record in heapq.merge(*runs):
                target.write(record[3])


def cli(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('--temp-dir', help='Directory for temporary sorted runs')
    parser.add_argument('--chunk-size', type=int, default=100000, help='Records per in-memory run (default: 100000)')
    args = parser.parse_args(argv)
    sort_vcf(args.input, args.output, temp_dir=args.temp_dir, chunk_size=args.chunk_size)
    return 0

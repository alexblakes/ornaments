import gzip
from pathlib import Path
import pytest

HEADER = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"


def test_sort_across_chunks_preserves_ties(tmp_path):
    from ornaments.sort import sort_vcf
    source, target = tmp_path / "in.vcf", tmp_path / "out.vcf"
    rows = ["txB\t2\ta\tA\tG\t.\t.\t.\n", "txA\t10\tb\tA\tG\t.\t.\t.\n",
            "txA\t2\tc\tA\tG\t.\t.\t.\n", "txA\t2\td\tA\tG\t.\t.\t.\n"]
    source.write_text(HEADER + "".join(rows))
    sort_vcf(str(source), str(target), chunk_size=1, temp_dir=str(tmp_path))
    assert target.read_text() == HEADER + "".join(rows[i] for i in [2, 3, 1, 0])
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.vcf", "out.vcf"]


def test_empty_body(tmp_path):
    from ornaments.sort import sort_vcf
    source, target = tmp_path / "in.vcf", tmp_path / "out.vcf"
    source.write_text(HEADER)
    sort_vcf(str(source), str(target))
    assert target.read_text() == HEADER


def test_gzip_sort(tmp_path):
    from ornaments.sort import sort_vcf
    source, target = tmp_path / "in.vcf.gz", tmp_path / "out.vcf.gz"
    with gzip.open(source, "wt") as stream:
        stream.write(HEADER + "tx\t2\t.\tA\tG\t.\t.\t.\n")
    sort_vcf(str(source), str(target))
    with gzip.open(target, "rt") as stream:
        assert stream.read() == HEADER + "tx\t2\t.\tA\tG\t.\t.\t.\n"


@pytest.mark.parametrize("record", ["tx\tbad\t.\tA\tG\t.\t.\t.", "tx\t0\t.\tA\tG\t.\t.\t.", "tx\t1"])
def test_invalid_record_leaves_output_untouched(tmp_path, record):
    from ornaments.sort import sort_vcf
    source, target = tmp_path / "in.vcf", tmp_path / "out.vcf"
    source.write_text(HEADER + record + "\n")
    target.write_text("existing output\n")
    with pytest.raises(ValueError, match="line 3"):
        sort_vcf(str(source), str(target))
    assert target.read_text() == "existing output\n"


def test_input_output_alias(tmp_path):
    from ornaments.sort import sort_vcf
    source = tmp_path / "in.vcf"
    source.write_text(HEADER)
    alias = tmp_path / "alias.vcf"
    alias.symlink_to(source)
    with pytest.raises(ValueError, match="same"):
        sort_vcf(str(source), str(alias))
    assert source.read_text() == HEADER


def write_samples(path, samples, record):
    path.write_text(HEADER.replace("\n#CHROM", "\n##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n#CHROM").rstrip()
        + "\tFORMAT\t" + "\t".join(samples) + "\n" + record + "\n")


def test_merge_projects_samples_in_requested_order(tmp_path):
    from ornaments.merge import merge_vcfs
    a, b, out = tmp_path / "a.vcf", tmp_path / "b.vcf", tmp_path / "out.vcf"
    write_samples(a, ["A", "B"], "tx1\t1\t.\tA\tG\t.\tPASS\tAC=1\tGT:DP\t0|1:7\t1|1:9")
    write_samples(b, ["B", "A"], "tx2\t2\t.\tC\tT\t.\tPASS\tAC=1\tGT:DP\t0|0:8\t1|0:3")
    merge_vcfs([str(a), str(b)], str(out), ["A", "B"])
    rows = out.read_text().splitlines()
    assert rows[-3].endswith("\tFORMAT\tA\tB")
    assert rows[-2].endswith("\tAC=1\tGT:DP\t0|1:7\t1|1:9")
    assert rows[-1].endswith("\tAC=1\tGT:DP\t1|0:3\t0|0:8")
    assert sum(row.startswith("##FORMAT") for row in rows) == 1


def test_merge_missing_sample_is_atomic(tmp_path):
    from ornaments.merge import merge_vcfs
    a, out = tmp_path / "a.vcf", tmp_path / "out.vcf"
    write_samples(a, ["A"], "tx\t1\t.\tA\tG\t.\t.\t.\tGT\t0|1")
    with pytest.raises(ValueError, match="B"):
        merge_vcfs([str(a)], str(out), ["B"])
    assert not out.exists()


def test_merge_list_blanks_and_sample_file(tmp_path):
    from ornaments.cli import main
    a, out = tmp_path / "a.vcf", tmp_path / "out.vcf"
    write_samples(a, ["B", "A"], "tx\t1\t.\tA\tG\t.\t.\t.\tGT\t0|1\t1|1")
    files, samples = tmp_path / "files.txt", tmp_path / "samples.txt"
    files.write_text("\n" + str(a) + "\n\n")
    samples.write_text("A\nB\n")
    assert main(["merge", "-i", str(files), "-s", str(samples), "-o", str(out)]) == 0
    assert out.read_text().splitlines()[-1].endswith("\t1|1\t0|1")


@pytest.mark.parametrize("header", ["##fileformat=VCFv4.2\n", HEADER.rstrip()+"\tFORMAT\tA\tA\n"])
def test_sample_header_invalid(tmp_path, header):
    from ornaments.vcf import read_samples
    source = tmp_path / "in.vcf"
    source.write_text(header)
    with pytest.raises(ValueError):
        read_samples(source)


def test_conflicting_metadata_rejected(tmp_path):
    from ornaments.merge import merge_vcfs
    a, b = tmp_path / "a.vcf", tmp_path / "b.vcf"
    write_samples(a, ["A"], "tx\t1\t.\tA\tG\t.\t.\t.\tGT\t0|1")
    b.write_text(a.read_text().replace('Description="Genotype"', 'Description="Other"'))
    with pytest.raises(ValueError, match="conflict"):
        merge_vcfs([str(a), str(b)], str(tmp_path / "out.vcf"), ["A"])

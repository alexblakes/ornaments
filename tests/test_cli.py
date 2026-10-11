import json
import sys


def test_top_level_help(capsys):
    from ornaments.cli import main
    assert main(["--help"]) == 0
    help_text = capsys.readouterr().out
    assert all(name in help_text for name in
               ["convert", "merge", "sort", "personalize", "index", "quant"])


def test_native_arguments_and_status(monkeypatch, tmp_path, capfd):
    from ornaments import native
    from ornaments.cli import main
    engine = tmp_path / "_bin" / "ornaments"
    engine.parent.mkdir()
    engine.write_text(f'#!{sys.executable}\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\nsys.exit(7)\n')
    engine.chmod(0o755)
    monkeypatch.setattr(native, "__file__", str(tmp_path / "native.py"))
    assert main(["index", "-i", "path with spaces/index", "input.fa"]) == 7
    assert json.loads(capfd.readouterr().out) == ["index", "-i", "path with spaces/index", "input.fa"]


def test_missing_engine_fails(monkeypatch, tmp_path, capsys):
    from ornaments import native
    from ornaments.cli import main
    monkeypatch.setattr(native, "__file__", str(tmp_path / "native.py"))
    assert main(["index", "-i", "out.index", "input.fa"]) != 0
    assert "reinstall" in capsys.readouterr().err.lower()


def test_unknown_command(capsys):
    from ornaments.cli import main
    assert main(["unknown"]) != 0
    assert "unknown" in capsys.readouterr().err


def test_help_is_lazy():
    import subprocess
    result = subprocess.run([sys.executable, "-c",
        'import sys; from ornaments.cli import main; main(["--help"]); '
        'assert not any(x in sys.modules for x in ("numpy", "Bio", "gtfparse"))'],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

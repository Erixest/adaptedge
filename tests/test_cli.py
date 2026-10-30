import json

from adaptedge.cli import main
from adaptedge.evaluate import build_parser


def test_evaluate_cli_writes_artifact(tmp_path):
    out = tmp_path / "metrics.json"
    assert main(["evaluate", "--runs", "30", "--seed", "5", "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["tool"] == "adaptedge"
    assert payload["config"]["runs"] == 30
    assert "episodes" not in payload
    assert payload["summaries"]["adaptive"]["n"] == 30
    assert payload["pilot"]["captures"]["sf7"]["samples"] == 46


def test_version_cli(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_parser_defaults():
    args = build_parser().parse_args([])
    assert args.runs == 200
    assert args.seed == 42
    assert str(args.out) == "reports/metrics.json"

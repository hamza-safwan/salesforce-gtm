import json
from types import SimpleNamespace

import pytest
import yaml

from gtmdq.salesforce import cli


def test_command_failures_do_not_echo_credentials(monkeypatch):
    monkeypatch.setattr(cli, "executable", lambda: ["sf"])
    result = SimpleNamespace(
        returncode=1,
        stdout=json.dumps({"status": 1, "name": "AuthError", "accessToken": "SECRET"}),
        stderr="diagnostic containing SECRET",
    )
    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: result)
    with pytest.raises(RuntimeError, match="AuthError") as error:
        cli.run_json(["sobject", "describe", "--sobject", "Account"], "gtmdq")
    assert "SECRET" not in str(error.value)


def test_inspection_preserves_custom_stage_api_names(tmp_path, monkeypatch):
    stage_rows = [
        {
            "ApiName": "Discovery_Custom",
            "DefaultProbability": 25,
            "IsClosed": False,
            "IsWon": False,
        },
        {"ApiName": "Signed_Custom", "DefaultProbability": 100, "IsClosed": True, "IsWon": True},
        {"ApiName": "No_Go_Custom", "DefaultProbability": 0, "IsClosed": True, "IsWon": False},
    ]

    def mock_command(arguments, target_org):
        assert target_org == "dedicated-test-org"
        if arguments[0] == "sobject":
            return {
                "name": arguments[-1],
                "fields": [
                    {"name": name, "type": "string"}
                    for name in (
                        "ApiName",
                        "IsActive",
                        "DefaultProbability",
                        "IsClosed",
                        "IsWon",
                        "SortOrder",
                    )
                ],
            }
        return {"done": True, "totalSize": 3, "records": stage_rows}

    monkeypatch.setattr(cli, "run_json", mock_command)
    summary = cli.inspect_org("dedicated-test-org", tmp_path)
    assert summary["active_stages"] == 3
    stages = yaml.safe_load((tmp_path / "opportunity_stages.yml").read_text())
    assert stages["source"] == "salesforce_describe"
    assert [stage["api_name"] for stage in stages["stages"]] == [
        "Discovery_Custom",
        "Signed_Custom",
        "No_Go_Custom",
    ]
    assert stages["stages"][1]["is_won"] is True

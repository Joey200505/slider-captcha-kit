import json

from slider_captcha_kit.cli import main


def test_offline_cli_sample_and_both_algorithms(tmp_path,capsys):
    assert main(["sample","--output",str(tmp_path)]) == 0
    capsys.readouterr()
    for method in ["outline","template"]:
        args=["analyze","--background",str(tmp_path/f"{method}_background.png"),"--piece",str(tmp_path/f"{method}_piece.png"),"--method",method]
        if method=="template":
            args += ["--piece-y","64"]
        assert main(args) == 0
        assert json.loads(capsys.readouterr().out)["offset_x"] == 168

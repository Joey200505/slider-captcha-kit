"""Public source archives must never scoop up unreviewed local files."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("source_package", PROJECT_ROOT / "scripts/package.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def test_release_includes_only_reviewed_files_and_verifiable_manifest(tmp_path):
    root = tmp_path / "project"
    list_content = (PROJECT_ROOT / "scripts/public-files.txt").read_text(encoding="utf-8")
    names = [line.strip() for line in list_content.splitlines() if line.strip() and not line.startswith("#")]
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"Public fixture: {name}\n", encoding="utf-8")
    (root / "scripts/public-files.txt").write_text(list_content, encoding="utf-8")
    for name in ["configs/.env", "configs/site.local.json", "src/slider_captcha_kit/secret.py"]:
        (root / name).write_text("PRIVATE_TEST_SENTINEL", encoding="utf-8")

    target = tmp_path / "release.zip"
    result = package.build_archive(root, target)
    prefix = "slider-captcha-kit-0.1.0/"
    with ZipFile(target) as archive:
        assert set(archive.namelist()) == {prefix + name for name in names} | {prefix + "BUILD-MANIFEST.json"}
        assert all(b"PRIVATE_TEST_SENTINEL" not in archive.read(name) for name in archive.namelist())
        manifest = json.loads(archive.read(prefix + "BUILD-MANIFEST.json"))
        assert {entry["path"] for entry in manifest["files"]} == set(names)
        for entry in manifest["files"]:
            content = archive.read(prefix + entry["path"])
            assert content == (root / entry["path"]).read_bytes()
            assert len(content) == entry["bytes"]
            assert sha256(content).hexdigest() == entry["sha256"]
    digest = sha256(target.read_bytes()).hexdigest()
    assert result["sha256"] == digest
    assert target.with_suffix(".zip.sha256").read_text(encoding="utf-8") == f"{digest}  release.zip\n"
    second = tmp_path / "second.zip"
    package.build_archive(root, second)
    assert second.read_bytes() == target.read_bytes()


@pytest.mark.parametrize("declaration", [
    "../outside.txt", "/absolute.txt", "configs/../outside.txt", "./README.md",
    "configs//demo.json", "configs\\demo.json", "C:/outside.txt", "BUILD-MANIFEST.json",
    "README.md\nREADME.md", "README.md\nreadme.md", "missing.txt", "# nothing declared\n",
])
def test_release_refuses_unsafe_missing_or_duplicate_declarations(tmp_path, declaration):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/public-files.txt").write_text(declaration, encoding="utf-8")
    (tmp_path / "README.md").write_text("Public fixture", encoding="utf-8")
    target = tmp_path / "release.zip"
    with pytest.raises(ValueError):
        package.build_archive(tmp_path, target)
    assert not target.exists()

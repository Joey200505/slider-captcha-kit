"""Build a deterministic source ZIP from an explicit, credential-free allowlist."""
import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


def public_files(root: Path) -> list[Path]:
    """Only reviewed, individually listed paths may enter a public source ZIP."""
    root = root.resolve()
    declared = (root / "scripts/public-files.txt").read_text(encoding="utf-8").splitlines()
    paths = []
    seen = set()
    for line in declared:
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        relative = PurePosixPath(name)
        if (relative.is_absolute() or name != relative.as_posix() or
                any(part in {".", ".."} for part in relative.parts) or
                "\\" in name or ":" in name or name == "BUILD-MANIFEST.json"):
            raise ValueError(f"Unsafe public file path: {name}")
        if name.casefold() in seen:
            raise ValueError(f"Duplicate public file path: {name}")
        seen.add(name.casefold())
        path = root.joinpath(*relative.parts)
        if (not path.resolve().is_relative_to(root) or
                any(parent.is_symlink() for parent in [path, *path.parents] if parent != root)):
            raise ValueError(f"Unsafe public file path: {name}")
        if not path.is_file():
            raise ValueError(f"Missing public file: {name}")
        paths.append(path)
    if not paths:
        raise ValueError("Public file list is empty")
    return sorted(paths)


def build_archive(root: Path, target: Path) -> dict:
    root = root.resolve()
    version="0.1.0"
    prefix=f"slider-captcha-kit-{version}"
    files = {path.relative_to(root).as_posix(): path.read_bytes() for path in public_files(root)}
    manifest={"name":"slider-captcha-kit","version":version,"files":[{"path":name,"sha256":sha256(content).hexdigest(),"bytes":len(content)} for name,content in files.items()]}
    target=target.resolve();target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,"w",ZIP_DEFLATED,compresslevel=9) as archive:
        def write(name,content):
            info=ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=ZIP_DEFLATED
            info.create_system=3
            info.external_attr=0o100644<<16
            archive.writestr(info,content)
        for name,content in files.items():
            write(prefix+"/"+name,content)
        write(prefix+"/BUILD-MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    digest=sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix+".sha256").write_text(digest+"  "+target.name+"\n",encoding="utf-8")
    return {"archive":str(target),"files":len(files)+1,"bytes":target.stat().st_size,"sha256":digest}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    print(json.dumps(build_archive(Path(__file__).resolve().parents[1], Path(args.output))))


if __name__=="__main__":main()

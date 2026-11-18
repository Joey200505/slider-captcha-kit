"""Build a deterministic source ZIP from an explicit, credential-free allowlist."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    version="0.1.0"
    prefix=f"slider-captcha-kit-{version}"
    directories={"src","configs","examples","tests","docs","scripts",".github"}
    top={"pyproject.toml","README.md","LICENSE","CHANGELOG.md","THIRD_PARTY_NOTICES.md","CONTRIBUTING.md","MANIFEST.in",".gitignore"}
    files=[]
    for path in sorted(root.rglob("*")):
        if not path.is_file():continue
        relative=path.relative_to(root)
        if any(p in {"__pycache__",".pytest_cache",".git",".venv","private","samples"} or p.endswith(".egg-info") for p in relative.parts):continue
        if path.suffix in {".pyc",".pyo"}:continue
        if (len(relative.parts)==1 and relative.name in top) or relative.parts[0] in directories:
            files.append(path)
    manifest={"name":"slider-captcha-kit","version":version,"files":[{"path":p.relative_to(root).as_posix(),"sha256":sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in files]}
    target=Path(args.output).resolve();target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,"w",ZIP_DEFLATED,compresslevel=9) as archive:
        def write(name,content):
            info=ZipInfo(name,date_time=(2026,1,1,0,0,0))
            info.compress_type=ZIP_DEFLATED
            info.create_system=3
            info.external_attr=0o100644<<16
            archive.writestr(info,content)
        for path in files:
            write(prefix+"/"+path.relative_to(root).as_posix(),path.read_bytes())
        write(prefix+"/BUILD-MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    digest=sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix+".sha256").write_text(digest+"  "+target.name+"\n",encoding="utf-8")
    print(json.dumps({"archive":str(target),"files":len(files)+1,"bytes":target.stat().st_size,"sha256":digest}))


if __name__=="__main__":main()

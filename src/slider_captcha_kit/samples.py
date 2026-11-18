"""Opt-in local images and allowlisted metadata, without DOM/URLs/credentials."""
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import threading
from uuid import uuid4

from PIL import Image
from .images import pixels

_LOCK = threading.Lock()
_REASONS = {"SUCCESS_CONFIRMED","MATCH_LOW_SCORE","MATCH_AMBIGUOUS","MATCH_SEARCH_TOO_LARGE","MATCH_FAILED",
            "IMAGE_CHANGED","DISTANCE_INVALID","LAYOUT_UNSUPPORTED","BROWSER_OR_IMAGE_ERROR","PLATFORM_NOT_CONFIRMED",
            "PIECE_Y_REQUIRED","PIECE_MASK_EMPTY","PIECE_OUTLINE_MISSING","PIECE_TEXTURE_EMPTY",
            "IMAGE_SIZE_INVALID","IMAGE_DIMENSIONS_UNSUPPORTED","IMAGE_DECODE_FAILED","CHALLENGE_NOT_FOUND"}


class SampleStore:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def capture(self, background: bytes, piece: bytes) -> dict | None:
        try:
            with _LOCK:
                self.directory.mkdir(parents=True,exist_ok=True)
                stem = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"_"+uuid4().hex[:8]
                receipt = {"background_file":stem+"_background.png", "piece_file":stem+"_piece.png"}
                for key,content in [("background_file",background),("piece_file",piece)]:
                    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                        normalized = io.BytesIO()
                        Image.fromarray(pixels(content,"RGBA")).save(normalized,format="PNG")
                        content = normalized.getvalue()
                    with (self.directory/receipt[key]).open("xb") as stream:
                        stream.write(content)
                return receipt
        except (OSError,ValueError):
            return None

    def record(self, outcome: str, *, receipt=None, **metrics) -> None:
        if outcome not in {"seen","solved","failed","manual"}:
            return
        record = {"timestamp":datetime.now(timezone.utc).isoformat(),"outcome":outcome}
        if metrics.get("reason") in _REASONS:
            record["reason"] = metrics["reason"]
        for key,value in (receipt or {}).items():
            if key in {"background_file","piece_file"} and isinstance(value,str) and Path(value).name==value:
                record[key] = value
        numeric = {"attempt","offset_x","score","runner_up_score","distance_css","background_width","piece_width","piece_y"}
        for key,value in metrics.items():
            if key in numeric and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
                record[key] = value
        try:
            with _LOCK:
                self.directory.mkdir(parents=True,exist_ok=True)
                with (self.directory/"attempts.jsonl").open("a",encoding="utf-8") as stream:
                    stream.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+"\n")
        except OSError:
            pass

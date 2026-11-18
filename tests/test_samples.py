import json
import io
from PIL import Image

from slider_captcha_kit.samples import SampleStore
from slider_captcha_kit.synthetic import puzzle


def test_only_explicit_safe_metadata_is_saved(tmp_path):
    store = SampleStore(tmp_path)
    background,piece,_ = puzzle()
    receipt = store.capture(background,piece)
    store.record("solved",receipt=receipt,attempt=1,score=1.0,
                 password="DO_NOT_SAVE",url="https://private.invalid",cookie="DO_NOT_SAVE",score_nan=float("nan"))
    text = (tmp_path/"attempts.jsonl").read_text("utf-8")
    assert "DO_NOT_SAVE" not in text and "private.invalid" not in text
    assert json.loads(text)["score"] == 1.0
    assert (tmp_path/receipt["background_file"]).read_bytes() == background


def test_readonly_destination_does_not_break_login(tmp_path):
    blocked = tmp_path/"file"
    blocked.write_text("not a directory")
    store = SampleStore(blocked)
    bg,piece,_ = puzzle()
    assert store.capture(bg,piece) is None
    store.record("failed",attempt=1)


def test_jpeg_samples_are_normalized_to_actual_png(tmp_path):
    stream=io.BytesIO()
    Image.new("RGB",(20,20),(100,80,50)).save(stream,format="JPEG")
    store=SampleStore(tmp_path)
    receipt=store.capture(stream.getvalue(),stream.getvalue())
    assert (tmp_path/receipt["background_file"]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    store.record("failed",reason="MATCH_LOW_SCORE",receipt=receipt)
    store.record("failed",reason="DO_NOT_SAVE")
    lines=[json.loads(s) for s in (tmp_path/"attempts.jsonl").read_text().splitlines()]
    assert lines[0]["reason"]=="MATCH_LOW_SCORE"
    assert "reason" not in lines[1]

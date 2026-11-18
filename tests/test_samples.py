import json
import io
from PIL import Image
from PIL.PngImagePlugin import PngInfo

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
    with Image.open(io.BytesIO(background)) as original:
        with Image.open(tmp_path/receipt["background_file"]) as saved:
            assert saved.convert("RGBA").tobytes() == original.convert("RGBA").tobytes()


def test_png_metadata_is_removed_without_changing_pixels(tmp_path):
    image = Image.new("RGBA", (20,20), (100,80,50,128))
    metadata = PngInfo()
    metadata.add_text("Comment", "PRIVATE_TEST_VALUE")
    exif = Image.Exif()
    exif[270] = "PRIVATE_TEST_VALUE"
    stream = io.BytesIO()
    image.save(stream, format="PNG", pnginfo=metadata, exif=exif)
    receipt = SampleStore(tmp_path).capture(stream.getvalue(),stream.getvalue())
    assert receipt is not None
    for name in receipt.values():
        path = tmp_path/name
        assert b"PRIVATE_TEST_VALUE" not in path.read_bytes()
        with Image.open(path) as saved:
            assert saved.info == {}
            assert not saved.getexif()
            assert saved.convert("RGBA").tobytes() == image.tobytes()


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

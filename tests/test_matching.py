import io
import random

import numpy as np
import pytest
from PIL import Image

from slider_captcha_kit import AmbiguousMatch, MatchError, MatchOptions, match_images
from slider_captcha_kit.images import ImageError, decode_data_url, pixels
from slider_captcha_kit.synthetic import png, puzzle
from slider_captcha_kit.trajectory import drag_points


@pytest.mark.parametrize("offset",[21,110,168,290])
def test_outline_offsets_and_css_scale(offset):
    bg,piece,expected = puzzle(offset=offset)
    result = match_images(bg,piece)
    assert result.offset_x == offset
    assert result.score == 1
    assert result.distance_css(540,12) == offset*1.5-12


def test_masked_texture_and_vertical_position():
    bg,piece,expected = puzzle(compact=True,texture=True)
    result = match_images(bg,piece,piece_y=expected["piece_y"],options=MatchOptions(method="template"))
    assert result.offset_x == expected["offset_x"]
    assert result.score > .99
    with pytest.raises(MatchError,match="PIECE_Y_REQUIRED"):
        match_images(bg,piece)


@pytest.mark.parametrize("method",["outline","template"])
def test_duplicate_candidates_require_manual_decision(method):
    bg,piece,_ = puzzle(texture=method=="template")
    array = pixels(bg,"RGB")
    array[:,60:104] = array[:,168:212]
    with pytest.raises(AmbiguousMatch,match="MATCH_AMBIGUOUS"):
        match_images(png(array),piece,options=MatchOptions(method=method))


def test_low_score_and_unsupported_images_are_explicit():
    bg,piece,_ = puzzle()
    with pytest.raises(MatchError,match="MATCH_LOW_SCORE"):
        match_images(png(np.zeros((180,360,3),np.uint8)),piece)
    with pytest.raises(MatchError,match="IMAGE_DECODE_FAILED"):
        match_images(b"not an image",piece)
    with pytest.raises(MatchError,match="LAYOUT_UNSUPPORTED"):
        match_images(bg,piece,piece_y=100)


def test_transparent_or_constant_texture_is_rejected():
    bg,piece,_ = puzzle()
    with pytest.raises(MatchError,match="PIECE_MASK_EMPTY"):
        match_images(bg,png(np.zeros((180,44,4),np.uint8)))
    flat = np.full((180,44,4),255,np.uint8)
    with pytest.raises(MatchError,match="PIECE_TEXTURE_EMPTY"):
        match_images(bg,png(flat),options=MatchOptions(method="template"))


def test_image_limits_and_data_url_validation():
    with pytest.raises(ImageError):
        decode_data_url("https://example.invalid/image.png")
    with pytest.raises(ImageError):
        decode_data_url("data:image/png;base64,!!!!")
    out = io.BytesIO()
    Image.new("RGB",(4097,1)).save(out,format="PNG")
    with pytest.raises(ImageError,match="IMAGE_DIMENSIONS_UNSUPPORTED"):
        pixels(out.getvalue(),"RGB")


def test_large_search_is_bounded_before_expensive_matching():
    bg = png(np.zeros((1024,1024,3),np.uint8))
    piece = png(np.full((1024,512,4),255,np.uint8))
    with pytest.raises(MatchError,match="MATCH_SEARCH_TOO_LARGE"):
        match_images(bg,piece,options=MatchOptions(method="template"))


@pytest.mark.parametrize("seed",range(10))
def test_trajectory_duration_endpoint_and_bounded_overshoot(seed):
    points = drag_points(160,rng=random.Random(seed))
    assert 25 <= len(points) <= 45
    assert 700 <= sum(p[2] for p in points) <= 1400
    assert points[-1][:2] == (160,0)
    assert 163 <= max(x for x,_,_ in points) <= 168
    assert all(abs(y) <= 2 and delay >= 0 for _,y,delay in points)
    near_boundary = drag_points(160,rng=random.Random(seed),available_distance=160)
    assert max(x for x,_,_ in near_boundary) <= 160


@pytest.mark.parametrize("distance",[0,-1,float("nan"),float("inf")])
def test_invalid_trajectory_never_moves(distance):
    with pytest.raises(ValueError):
        drag_points(distance)

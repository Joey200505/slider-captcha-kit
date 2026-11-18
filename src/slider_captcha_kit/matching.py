"""Horizontal white-outline and alpha-masked normalized texture matching."""
from dataclasses import asdict, dataclass
import math

import numpy as np

from .images import ImageError, pixels


class MatchError(ValueError):
    def __init__(self, code: str, result=None):
        super().__init__(code)
        self.code, self.result = code, result


class AmbiguousMatch(MatchError):
    pass


@dataclass(frozen=True)
class MatchOptions:
    method: str = "outline"
    min_score: float = 0.8
    min_margin: float = 0.03
    candidate_separation: int = 1
    alpha_threshold: int = 200
    piece_white_threshold: int = 180
    background_white_threshold: int = 160

    def __post_init__(self):
        if self.method not in {"outline", "template"}:
            raise ValueError("MATCH_METHOD_INVALID")
        if not (0 <= self.min_score <= 1 and 0 <= self.min_margin <= 1):
            raise ValueError("MATCH_THRESHOLDS_INVALID")
        if not isinstance(self.candidate_separation, int) or not 1 <= self.candidate_separation <= 100:
            raise ValueError("MATCH_SEPARATION_INVALID")
        if any(not isinstance(v, int) or not 0 <= v <= 255 for v in (
                self.alpha_threshold, self.piece_white_threshold, self.background_white_threshold)):
            raise ValueError("MATCH_PIXEL_THRESHOLD_INVALID")


@dataclass(frozen=True)
class MatchResult:
    offset_x: int
    score: float
    runner_up_score: float
    background_width: int
    piece_width: int
    piece_y: int
    method: str

    def to_dict(self):
        return asdict(self)

    def distance_css(self, display_width: float, piece_start_css: float = 0.0) -> float:
        if not math.isfinite(display_width) or display_width <= 0 or not math.isfinite(piece_start_css):
            raise ValueError("DISPLAY_GEOMETRY_INVALID")
        return self.offset_x * display_width / self.background_width - piece_start_css


def match_images(background: bytes, piece: bytes, *, piece_y: int | None = None,
                 options: MatchOptions | None = None) -> MatchResult:
    options = options or MatchOptions()
    try:
        bg, part = pixels(background, "RGB"), pixels(piece, "RGBA")
    except ImageError as error:
        raise MatchError(str(error)) from None
    h, w = bg.shape[:2]
    ph, pw = part.shape[:2]
    if piece_y is None:
        if ph != h:
            raise MatchError("PIECE_Y_REQUIRED")
        piece_y = 0
    if not isinstance(piece_y, int) or piece_y < 0 or piece_y+ph > h or pw >= w:
        raise MatchError("LAYOUT_UNSUPPORTED")
    opaque = part[:, :, 3] > options.alpha_threshold
    if int(opaque.sum()) < 8:
        raise MatchError("PIECE_MASK_EMPTY")
    if options.method == "outline":
        mask = opaque & (part[:, :, :3].min(axis=2) > options.piece_white_threshold)
        if int(mask.sum()) < 8:
            raise MatchError("PIECE_OUTLINE_MISSING")
        if (w-pw+1)*int(mask.sum()) > 50_000_000:
            raise MatchError("MATCH_SEARCH_TOO_LARGE")
        region = bg[piece_y:piece_y+ph].min(axis=2) > options.background_white_threshold
        scores = np.array([region[:, x:x+pw][mask].mean() for x in range(w-pw+1)])
    else:
        if (w-pw+1)*int(opaque.sum()) > 50_000_000:
            raise MatchError("MATCH_SEARCH_TOO_LARGE")
        # Per-channel centering handles a darkened gap while retaining texture.
        target = part[:, :, :3][opaque].astype(np.float64)
        target -= target.mean(axis=0)
        target_norm = float(np.linalg.norm(target))
        if target_norm < 1e-9:
            raise MatchError("PIECE_TEXTURE_EMPTY")
        scores = []
        for x in range(w-pw+1):
            candidate = bg[piece_y:piece_y+ph, x:x+pw][opaque].astype(np.float64)
            candidate -= candidate.mean(axis=0)
            norm = float(np.linalg.norm(candidate))
            score = float(np.sum(candidate*target)/(norm*target_norm)) if norm > 1e-9 else 0.0
            scores.append(float(np.clip(score, 0, 1)))
        scores = np.array(scores)
    order = np.argsort(-scores, kind="stable")
    offset = int(order[0])
    others = [int(i) for i in order[1:] if abs(int(i)-offset) >= options.candidate_separation]
    runner_up = float(scores[others[0]]) if others else 0.0
    result = MatchResult(offset,float(scores[offset]),runner_up,w,pw,piece_y,options.method)
    if result.score < options.min_score:
        raise MatchError("MATCH_LOW_SCORE", result)
    if result.score-runner_up < options.min_margin:
        raise AmbiguousMatch("MATCH_AMBIGUOUS", result)
    return result

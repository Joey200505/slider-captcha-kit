"""Synchronous Playwright adapter with explicit site configuration and success proof."""
from dataclasses import asdict, dataclass, field
import random
import time
from typing import Callable

from .images import IMAGE_READY_JS, READ_IMAGE_JS, decode_data_url, pixels
from .matching import MatchError, MatchOptions, MatchResult, match_images
from .samples import SampleStore
from .trajectory import drag_points


@dataclass(frozen=True)
class BrowserConfig:
    background: str
    piece: str
    handle: str
    success: str | None = None
    panel: str | None = None
    piece_container: str | None = None
    refresh: str | None = None
    failure: str | None = None
    frame: str | None = None
    piece_y: int | None = None
    drag_ratio: float = 1.0

    def __post_init__(self):
        if any(not isinstance(v,str) or not v.strip() for v in (self.background,self.piece,self.handle)):
            raise ValueError("SELECTORS_REQUIRED")
        if not isinstance(self.drag_ratio,(int,float)) or not 0.1 <= self.drag_ratio <= 10:
            raise ValueError("DRAG_RATIO_INVALID")
        if self.piece_y is not None and (not isinstance(self.piece_y,int) or self.piece_y < 0):
            raise ValueError("PIECE_Y_INVALID")


@dataclass(frozen=True)
class SolveOptions:
    enabled: bool = True
    max_attempts: int = 3
    detection_timeout: float = 5.0
    result_timeout: float = 8.0
    samples: str | None = None
    matching: MatchOptions = field(default_factory=MatchOptions)

    def __post_init__(self):
        if not isinstance(self.max_attempts,int) or not 1 <= self.max_attempts <= 3:
            raise ValueError("ATTEMPTS_MUST_BE_1_TO_3")
        if not 0 < self.detection_timeout <= 120 or not 0 < self.result_timeout <= 120:
            raise ValueError("TIMEOUT_INVALID")


@dataclass(frozen=True)
class Attempt:
    number: int
    outcome: str
    reason: str
    match: dict | None = None
    distance_css: float | None = None


@dataclass(frozen=True)
class SolveResult:
    status: str
    reason: str
    attempts: tuple[Attempt,...] = ()

    @property
    def passed(self) -> bool:
        return self.status in {"solved","already_passed"}

    def to_dict(self):
        return {**asdict(self),"passed":self.passed}


def _scopes(page, config):
    if config.frame:
        return [page.frame_locator(config.frame)]
    return [page]+[f for f in page.frames if f != page.main_frame]


def _visible(scope, selector):
    return bool(selector and scope.locator(selector).first.is_visible())


def _challenge(page, config):
    for scope in _scopes(page,config):
        try:
            if all(_visible(scope,s) for s in (config.background,config.piece,config.handle)):
                if all(scope.locator(s).first.evaluate(IMAGE_READY_JS,timeout=1000)
                       for s in (config.background,config.piece)):
                    return scope
        except Exception:
            continue
    return None


def _accepted(page, config, success):
    if _challenge(page,config) is not None:
        return False
    try:
        if success is not None:
            return bool(success(page))
        return any(_visible(scope,config.success) for scope in _scopes(page,config))
    except Exception:
        return False


def _images(scope, config):
    return tuple(scope.locator(selector).first.evaluate(READ_IMAGE_JS,timeout=1500)
                 for selector in (config.background,config.piece))


def _box(scope, selector):
    box = scope.locator(selector).first.bounding_box(timeout=1500)
    if box is None or box["width"] <= 0 or box["height"] <= 0:
        raise MatchError("LAYOUT_UNSUPPORTED")
    return box


_MATCH_CODES = {"IMAGE_SIZE_INVALID","IMAGE_DIMENSIONS_UNSUPPORTED","IMAGE_DECODE_FAILED","PIECE_Y_REQUIRED",
                "LAYOUT_UNSUPPORTED","PIECE_MASK_EMPTY","PIECE_OUTLINE_MISSING","PIECE_TEXTURE_EMPTY",
                "MATCH_LOW_SCORE","MATCH_AMBIGUOUS","MATCH_SEARCH_TOO_LARGE","IMAGE_CHANGED","DISTANCE_INVALID"}


def solve(page, config: BrowserConfig, *, options: SolveOptions | None = None,
          success: Callable | None = None, matcher: Callable | None = None,
          rng: random.Random | None = None) -> SolveResult:
    """Operate only the visible challenge, leaving account/CA/SMS work to the caller.

    matcher(background_bytes, piece_bytes, *, piece_y, options) -> MatchResult
    may replace the built-in matcher without replacing the browser adapter.
    """
    options = options or SolveOptions()
    if not options.enabled:
        return SolveResult("disabled","AUTO_DISABLED")
    if not config.success and success is None:
        raise ValueError("SUCCESS_SELECTOR_OR_CALLBACK_REQUIRED")
    rng, matcher = rng or random.Random(), matcher or match_images
    store = SampleStore(options.samples) if options.samples else None
    deadline = time.monotonic()+options.detection_timeout
    while _challenge(page,config) is None:
        if _accepted(page,config,success):
            return SolveResult("already_passed","SUCCESS_CONFIRMED")
        if time.monotonic() >= deadline:
            return SolveResult("manual","CHALLENGE_NOT_FOUND")
        page.wait_for_timeout(100)
    history = []
    for number in range(1,options.max_attempts+1):
        receipt = match = distance = None
        reason = "CHALLENGE_NOT_FOUND"
        try:
            scope = _challenge(page,config)
            if scope is None:
                if _accepted(page,config,success):
                    return SolveResult("solved","SUCCESS_CONFIRMED",tuple(history))
                raise MatchError("LAYOUT_UNSUPPORTED")
            sources = _images(scope,config)
            background,piece = [decode_data_url(s) for s in sources]
            if store:
                receipt = store.capture(background,piece)
                store.record("seen",receipt=receipt,attempt=number)
            panel = _box(scope,config.panel or config.background)
            block = _box(scope,config.piece_container or config.piece)
            handle = _box(scope,config.handle)
            bg_pixels = pixels(background,"RGB")
            piece_pixels = pixels(piece,"RGBA")
            piece_y = config.piece_y
            if piece_y is None:
                piece_y = 0 if bg_pixels.shape[0]==piece_pixels.shape[0] else round(
                    (block["y"]-panel["y"])*bg_pixels.shape[0]/panel["height"])
            match = matcher(background,piece,piece_y=piece_y,options=options.matching)
            if not isinstance(match,MatchResult):
                raise MatchError("MATCH_LOW_SCORE")
            start = block["x"]-panel["x"]
            distance = match.distance_css(panel["width"],start)*config.drag_ratio
            available = (panel["width"]-block["width"]-start)*config.drag_ratio
            if start < -1 or not 0 < distance <= available:
                raise MatchError("DISTANCE_INVALID")
            points = drag_points(distance,rng=rng,available_distance=available)
            if _images(scope,config) != sources:
                raise MatchError("IMAGE_CHANGED")
            x,y = handle["x"]+handle["width"]/2,handle["y"]+handle["height"]/2
            page.mouse.move(x,y)
            # Mouse movement may dispatch a refresh; inspect again at mouse-down.
            if _images(scope,config) != sources:
                raise MatchError("IMAGE_CHANGED")
            page.mouse.down()
            try:
                for dx,dy,delay in points:
                    page.mouse.move(x+dx,y+dy)
                    page.wait_for_timeout(delay)
            finally:
                page.mouse.up()
            deadline = time.monotonic()+options.result_timeout
            while time.monotonic() < deadline:
                if _accepted(page,config,success):
                    history.append(Attempt(number,"solved","SUCCESS_CONFIRMED",match.to_dict(),distance))
                    if store:
                        store.record("solved",receipt=receipt,attempt=number,reason="SUCCESS_CONFIRMED",distance_css=distance,**match.to_dict())
                    return SolveResult("solved","SUCCESS_CONFIRMED",tuple(history))
                if config.failure and _visible(scope,config.failure):
                    break
                page.wait_for_timeout(100)
            reason = "PLATFORM_NOT_CONFIRMED"
        except MatchError as error:
            reason = error.code if error.code in _MATCH_CODES else "MATCH_FAILED"
            match = error.result if isinstance(error.result,MatchResult) else match
        except Exception:
            # Playwright exceptions may contain DOM or session data.
            reason = "BROWSER_OR_IMAGE_ERROR"
        metrics = match.to_dict() if isinstance(match,MatchResult) else None
        history.append(Attempt(number,"failed",reason,metrics,distance))
        if store:
            store.record("failed",receipt=receipt,attempt=number,reason=reason,distance_css=distance,**(metrics or {}))
        if number < options.max_attempts:
            try:
                scope = _challenge(page,config)
                if scope is not None and config.refresh and _visible(scope,config.refresh):
                    scope.locator(config.refresh).first.click(timeout=1500)
                page.wait_for_timeout(rng.randint(1000,2000))
            except Exception:
                break
    if store:
        store.record("manual",attempt=len(history),reason=history[-1].reason if history else "CHALLENGE_NOT_FOUND")
    return SolveResult("manual",history[-1].reason if history else "CHALLENGE_NOT_FOUND",tuple(history))

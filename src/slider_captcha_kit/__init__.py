"""Reusable local matching; browser integration does not own authentication."""
from .matching import AmbiguousMatch, MatchError, MatchOptions, MatchResult, match_images
from .browser import BrowserConfig, SolveOptions, SolveResult, solve

__version__ = "0.1.0"
__all__ = ["AmbiguousMatch", "MatchError", "MatchOptions", "MatchResult", "match_images",
           "BrowserConfig", "SolveOptions", "SolveResult", "solve"]

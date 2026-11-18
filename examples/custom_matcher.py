"""A functional matcher hook; no browser dependency in the image algorithm."""
from dataclasses import replace
from slider_captcha_kit import MatchOptions, match_images


def texture_matcher(background, piece, *, piece_y, options):
    return match_images(background,piece,piece_y=piece_y,
                        options=replace(options,method="template",candidate_separation=3))


# In an existing Playwright program:
# result = solve(page, config, matcher=texture_matcher)

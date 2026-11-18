"""Original synthetic images for offline examples and the local demo."""
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image


def png(array) -> bytes:
    out = io.BytesIO()
    Image.fromarray(array).save(out,format="PNG")
    return out.getvalue()


def puzzle(*, offset=168, seed=7, width=360, height=180, compact=False, texture=False):
    rng = np.random.default_rng(seed)
    background = rng.integers(35,145,(height,width,3),dtype=np.uint8)
    # A stepped puzzle silhouette with transparent pixels outside the outline.
    ph, pw, top = (52,44,64) if compact else (height,44,0)
    mask = np.zeros((ph,pw),bool)
    y = 0 if compact else 64
    mask[y+8:y+44,5:36] = True
    mask[y+19:y+33,36:43] = True
    mask[y:y+12,16:29] = True
    inner = mask.copy()
    inner[1:] &= mask[:-1]; inner[:-1] &= mask[1:]
    inner[:,1:] &= mask[:,:-1]; inner[:,:-1] &= mask[:,1:]
    border = mask & ~inner
    part = np.zeros((ph,pw,4),np.uint8)
    target = background[top:top+ph,offset:offset+pw]
    part[:,:,:3] = target
    part[:,:,3] = mask.astype(np.uint8)*255
    if texture:
        # The gap is darker than the original piece; correlation remains valid.
        target[mask] = (target[mask].astype(float)*0.55+12).astype(np.uint8)
    else:
        part[border,:3] = 255
        target[border] = 255
    return png(background),png(part),{"offset_x":offset,"piece_y":top,"background_width":width,"piece_width":pw}


def write_sample(directory):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    for name, kwargs in [("outline",{}),("template",{"compact":True,"texture":True})]:
        bg,piece,expected = puzzle(**kwargs)
        (directory/f"{name}_background.png").write_bytes(bg)
        (directory/f"{name}_piece.png").write_bytes(piece)
        (directory/f"{name}_expected.json").write_text(json.dumps(expected,indent=2)+"\n",encoding="utf-8")

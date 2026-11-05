#!/usr/bin/env python3
"""Put a chosen still onto the memoriescore reference colour before it seeds the render.

usage: uv run --no-project --python 3.12 --with numpy --with pillow --with scikit-image --with scipy \
           python scripts/still_match.py <in.png> <out.png>

Histogram matching of the skin in CIELAB onto the reference's own skin distribution (refgrade.py); the rest
of the picture is untouched. Check with still_check.py afterwards.
"""
import sys

import numpy as np
from PIL import Image
from refgrade import transfer

src, dst = sys.argv[1:3]
transfer(np.asarray(Image.open(src).convert("RGB"))).save(dst)
print(dst)

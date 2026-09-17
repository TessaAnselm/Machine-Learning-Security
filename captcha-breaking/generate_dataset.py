"""Renders labeled CAPTCHA images to disk. Only used to build the fixed
validation set now — training itself streams fresh images on the fly (see
StreamingCaptchaDataset in train_solver.py) instead of reading from here, so
`--train` is normally left at 0. The label is baked into each filename
(TEXT_hash.png) since we control the generator and always know the answer."""

import argparse
import os
import random
import uuid

from captcha.image import ImageCaptcha

from model import CHARSET, CAPTCHA_LENGTH, IMG_WIDTH, IMG_HEIGHT


def random_text():
    return "".join(random.choices(CHARSET, k=CAPTCHA_LENGTH))


def generate(out_dir, count):
    os.makedirs(out_dir, exist_ok=True)
    generator = ImageCaptcha(width=IMG_WIDTH, height=IMG_HEIGHT)
    for _ in range(count):
        text = random_text()
        # uuid suffix avoids filename collisions if the same text is ever
        # generated twice; the label itself is the part before the underscore.
        generator.write(text, os.path.join(out_dir, f"{text}_{uuid.uuid4().hex[:8]}.png"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=8000)
    parser.add_argument("--val", type=int, default=1000)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    generate(os.path.join(args.out, "train"), args.train)
    generate(os.path.join(args.out, "val"), args.val)
    print(f"generated {args.train} train and {args.val} val captchas in {args.out}/")

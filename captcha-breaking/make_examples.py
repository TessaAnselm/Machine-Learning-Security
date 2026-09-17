"""Generates a handful of fresh CAPTCHAs, runs the trained solver on them, and
saves the images + a results table for the README's example gallery. Unlike
predict.py (one image you supply) or solve.py (attacks the live server), this
generates its own images directly, so it needs no server running."""

import argparse
import os
import random

import numpy as np
import torch
from captcha.image import ImageCaptcha

from model import CHARSET, CAPTCHA_LENGTH, IMG_HEIGHT, IMG_WIDTH, CaptchaSolver


def predict(model, img, device):
    gray = img.convert("L").resize((IMG_WIDTH, IMG_HEIGHT))
    arr = np.asarray(gray, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
    return "".join(CHARSET[o.argmax(1).item()] for o in outputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/solver.pt")
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument("--out", default="examples")
    args = parser.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = CaptchaSolver().to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    os.makedirs(args.out, exist_ok=True)
    generator = ImageCaptcha(width=IMG_WIDTH, height=IMG_HEIGHT)

    rows = []
    for i in range(args.count):
        text = "".join(random.choices(CHARSET, k=CAPTCHA_LENGTH))  # we generate it, so we know the true answer
        img = generator.generate_image(text)
        guess = predict(model, img, device)
        filename = f"example_{i + 1}.png"
        img.save(os.path.join(args.out, filename))
        rows.append((filename, text, guess, text == guess))

    # Prints ready-to-paste GitHub-flavored Markdown for the README gallery.
    print("| Image | True | Guessed | Result |")
    print("|---|---|---|---|")
    for filename, text, guess, correct in rows:
        mark = "✅" if correct else "❌"
        print(f"| ![]({args.out}/{filename}) | `{text}` | `{guess}` | {mark} |")


if __name__ == "__main__":
    main()

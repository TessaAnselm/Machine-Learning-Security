"""Solves one specific CAPTCHA image from a file, instead of solve.py's
automated batch against fresh server-generated challenges. Useful for solving
the exact CAPTCHA you're looking at in the browser: save/screenshot it, run
this on that file, and type the printed guess into the form yourself. This is
what was used for the manual "real-world verification" screenshots in the
README — proof against a human-visible challenge, not just an automated loop."""

import argparse

import numpy as np
import torch
from PIL import Image

from model import CHARSET, IMG_HEIGHT, IMG_WIDTH, CaptchaSolver


def predict(model, image_path, device):
    img = Image.open(image_path).convert("L").resize((IMG_WIDTH, IMG_HEIGHT))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
    return "".join(CHARSET[o.argmax(1).item()] for o in outputs)


def main():
    parser = argparse.ArgumentParser(description="Read the model's guess for a single saved CAPTCHA image.")
    parser.add_argument("image", help="Path to a CAPTCHA image, e.g. one saved from the browser")
    parser.add_argument("--model", default="models/solver.pt")
    args = parser.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = CaptchaSolver().to(device)
    model.load_state_dict(torch.load(args.model, map_location=device))
    model.eval()

    print(predict(model, args.image, device))


if __name__ == "__main__":
    main()

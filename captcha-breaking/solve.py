"""The automated attacker: repeatedly fetches a brand-new CAPTCHA from the
live server, guesses it, and submits the guess, reporting the real-world pass
rate. Unlike training/validation (which score against a fixed generated
dataset), this is the only measurement here that proves the model works
against the actual running server, over HTTP, exactly like a real bot would."""

import argparse
import io

import numpy as np
import requests
import torch
from PIL import Image

from model import CHARSET, IMG_HEIGHT, IMG_WIDTH, CaptchaSolver


def load_model(path, device):
    model = CaptchaSolver().to(device)
    model.load_state_dict(torch.load(path, map_location=device))
    model.eval()
    return model


def predict(model, image_bytes, device):
    # Same preprocessing (grayscale, resize, normalize) used at training
    # time — the model only performs correctly if inputs match that exactly.
    img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((IMG_WIDTH, IMG_HEIGHT))
    arr = np.asarray(img, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(arr).unsqueeze(0).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
    # Each of the 5 heads independently picks its most likely character.
    return "".join(CHARSET[o.argmax(1).item()] for o in outputs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:5000")
    parser.add_argument("--model", default="models/solver.pt")
    parser.add_argument("--attempts", type=int, default=20)
    args = parser.parse_args()

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = load_model(args.model, device)

    # A single requests.Session so the server's session cookie (and therefore
    # its per-challenge token) carries correctly from /captcha.png to /verify.
    http = requests.Session()
    successes = 0
    for i in range(args.attempts):
        resp = http.get(f"{args.url}/captcha.png")
        resp.raise_for_status()
        guess = predict(model, resp.content, device)

        verify = http.post(f"{args.url}/verify", data={"answer": guess})
        passed = "Correct" in verify.text
        successes += passed
        print(f"attempt {i + 1}: guessed {guess} -> {'PASS' if passed else 'FAIL'}")

    print(f"\nsolved {successes}/{args.attempts} ({successes / args.attempts:.1%})")


if __name__ == "__main__":
    main()

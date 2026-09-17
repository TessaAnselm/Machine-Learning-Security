"""Trains the CNN solver. Two data sources are used on purpose: a small fixed
CaptchaDataset (data/val/) for scoring, so accuracy is measured consistently
across epochs and runs, and an unlimited StreamingCaptchaDataset for training,
so the model never trains on the same image twice."""

import argparse
import glob
import os
import random

import numpy as np
import torch
from captcha.image import ImageCaptcha
from PIL import Image
from torch.utils.data import DataLoader, Dataset, IterableDataset, get_worker_info

from model import CAPTCHA_LENGTH, CHARSET, IMG_HEIGHT, IMG_WIDTH, CaptchaSolver

CHAR_TO_IDX = {c: i for i, c in enumerate(CHARSET)}


class CaptchaDataset(Dataset):
    """Reads pre-generated CAPTCHA files from disk (see generate_dataset.py).
    Used only for the held-out validation set, which needs to stay fixed so
    accuracy numbers are comparable across epochs and training runs."""

    def __init__(self, folder):
        self.paths = glob.glob(os.path.join(folder, "*.png"))

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        label = os.path.basename(path).split("_")[0]  # generate_dataset.py names files "TEXT_hash.png"
        img = Image.open(path).convert("L").resize((IMG_WIDTH, IMG_HEIGHT))
        arr = np.asarray(img, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).unsqueeze(0)
        target = torch.tensor([CHAR_TO_IDX[c] for c in label], dtype=torch.long)
        return tensor, target


class StreamingCaptchaDataset(IterableDataset):
    """Generates a fresh, unique, labeled CAPTCHA per sample instead of reading
    a fixed set of files from disk, so training never repeats the same image."""

    def __init__(self, samples_per_epoch):
        self.samples_per_epoch = samples_per_epoch

    def __iter__(self):
        # PyTorch calls __iter__ separately in each DataLoader worker process
        # when num_workers > 0, so each worker gets its own RNG/generator here
        # and only needs to produce its own share of the epoch's samples.
        worker_info = get_worker_info()
        num_workers = worker_info.num_workers if worker_info else 1
        worker_id = worker_info.id if worker_info else 0
        # os.urandom seeds each worker independently so parallel workers don't
        # all generate the exact same "random" sequence of CAPTCHAs.
        rng = random.Random(os.urandom(8))
        generator = ImageCaptcha(width=IMG_WIDTH, height=IMG_HEIGHT)

        # Split the epoch's sample count across workers as evenly as possible.
        count = self.samples_per_epoch // num_workers
        if worker_id < self.samples_per_epoch % num_workers:
            count += 1

        for _ in range(count):
            text = "".join(rng.choices(CHARSET, k=CAPTCHA_LENGTH))
            img = generator.generate_image(text).convert("L").resize((IMG_WIDTH, IMG_HEIGHT))
            arr = np.asarray(img, dtype=np.float32) / 255.0
            tensor = torch.from_numpy(arr).unsqueeze(0)
            target = torch.tensor([CHAR_TO_IDX[c] for c in text], dtype=torch.long)
            yield tensor, target


def evaluate(model, loader, device):
    """Scores the model against the fixed validation set. Reports two numbers
    because they tell different stories: char accuracy shows raw recognition
    skill, full accuracy shows the real-world pass rate (all 5 characters have
    to be right for a CAPTCHA to actually be solved)."""
    model.eval()
    correct_chars = total_chars = correct_full = total_full = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            outputs = model(x)
            preds = torch.stack([o.argmax(1) for o in outputs], dim=1)
            correct_chars += (preds == y).sum().item()
            total_chars += y.numel()
            correct_full += (preds == y).all(dim=1).sum().item()  # every position must match
            total_full += y.size(0)
    return correct_chars / total_chars, correct_full / total_full


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--samples-per-epoch", type=int, default=15000)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", default="models/solver.pt")
    args = parser.parse_args()

    # MPS = Apple Silicon GPU acceleration; falls back to CPU elsewhere.
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    # The validation set stays fixed for the whole run (loaded once, outside
    # the epoch loop) so every epoch's score is comparable to the last.
    val_loader = DataLoader(CaptchaDataset(os.path.join(args.data, "val")), batch_size=args.batch_size)

    model = CaptchaSolver().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    # Halves the learning rate once validation accuracy stops improving for 3
    # epochs in a row, instead of grinding at a fixed rate that eventually
    # stops making progress. This is what let training keep squeezing out
    # small gains after it first plateaued (see the epoch log in the README).
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=3)
    criterion = torch.nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        # Rebuilt every epoch on purpose: a fresh StreamingCaptchaDataset means
        # a completely new set of generated images each time, so the model
        # never sees the same CAPTCHA twice across the whole training run.
        train_loader = DataLoader(
            StreamingCaptchaDataset(args.samples_per_epoch),
            batch_size=args.batch_size,
            num_workers=args.workers,
        )

        model.train()
        total_loss = 0.0
        num_batches = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            outputs = model(x)
            # Sum the loss across all 5 character-position heads so one
            # backward pass updates the whole network for the whole word.
            loss = sum(criterion(outputs[i], y[:, i]) for i in range(CAPTCHA_LENGTH))
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            num_batches += 1

        char_acc, full_acc = evaluate(model, val_loader, device)
        scheduler.step(full_acc)  # decide here whether to decay the LR
        lr = optimizer.param_groups[0]["lr"]
        print(
            f"epoch {epoch + 1}/{args.epochs} loss={total_loss / num_batches:.4f} "
            f"val_char_acc={char_acc:.4f} val_full_acc={full_acc:.4f} lr={lr:.2e}"
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save(model.state_dict(), args.out)
    print(f"saved model to {args.out}")


if __name__ == "__main__":
    main()

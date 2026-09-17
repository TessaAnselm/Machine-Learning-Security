"""The classic CAPTCHA-breaking approach (crop each letter, classify each one
individually) instead of reading the whole image at once. Kept in the repo as
a documented negative result: on our CAPTCHAs it only isolates exactly 5 clean
letters ~4.5% of the time, because the `captcha` library's noise curves are
drawn specifically to cross letter boundaries and defeat this trick. See the
README's "Results" section for the comparison against the whole-image CNN."""

import cv2
import numpy as np


def segment_letters(gray, expected=5):
    """Split a grayscale CAPTCHA image into `expected` letter crops via
    thresholding + contour detection, splitting any contour that spans two
    merged letters. Returns None if segmentation doesn't yield exactly
    `expected` regions."""
    # Padding first so a letter touching the image edge still gets a full
    # bounding contour instead of being clipped.
    padded = cv2.copyMakeBorder(gray, 8, 8, 8, 8, cv2.BORDER_REPLICATE)
    # Otsu picks the threshold automatically instead of a fixed brightness
    # cutoff, since the CAPTCHA background/ink contrast varies per image.
    _, thresh = cv2.threshold(padded, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h < 20:
            continue  # ignore tiny specks of noise, not real letters
        if w / h > 1.4:
            # Unusually wide box: probably two letters that touched/merged
            # into one contour. Split it down the middle as a best guess.
            half = w // 2
            boxes.append((x, y, half, h))
            boxes.append((x + half, y, w - half, h))
        else:
            boxes.append((x, y, w, h))

    # If we didn't land on exactly the expected letter count, segmentation
    # failed on this image — better to report failure than guess wrong boxes.
    if len(boxes) != expected:
        return None

    boxes.sort(key=lambda b: b[0])  # left to right, matching reading order
    crops = []
    for x, y, w, h in boxes:
        crops.append(padded[y : y + h, x : x + w])
    return crops

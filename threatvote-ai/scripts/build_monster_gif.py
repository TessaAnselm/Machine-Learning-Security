"""Package a generated 4-by-2 monster sprite sheet into a looping GIF.

Usage: python scripts/build_monster_gif.py assets/monster-talking-sprites.png
Requires Pillow and scipy for asset building only (scipy already ships as a
scikit-learn dependency); the app itself only serves the finished files.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]


def largest_component_mask(mask):
    """Keep only the largest True blob in a boolean mask, drop the rest."""
    labeled, count = ndimage.label(mask)
    if count <= 1:
        return mask
    sizes = ndimage.sum(np.ones_like(mask), labeled, range(1, count + 1))
    largest_label = int(np.argmax(sizes)) + 1
    return labeled == largest_label


def keep_largest_component(cell):
    """Drop every alpha blob except the biggest one.

    The source sheet's two rows sit close enough together that the row
    above's horn tips cross the row boundary into this cell, surviving the
    crop as a small disconnected fragment near the top edge. The character
    itself is always one single connected blob, so zeroing out every
    smaller component removes that bleed without touching the character.
    """
    alpha = np.array(cell.getchannel('A'))
    keep = largest_component_mask(alpha > 10)
    cell = cell.copy()
    cell.putalpha(Image.fromarray(np.where(keep, alpha, 0).astype('uint8')))
    return cell


def build(sheet_path):
    sheet = Image.open(sheet_path).convert('RGBA')
    width, height = sheet.size
    if abs(width / height - 2) > 0.05:
        raise ValueError('Expected a 4-by-2 sheet of approximately square cells.')
    frames = []
    for row in range(2):
        for col in range(4):
            bounds = (col * width // 4, row * height // 2,
                      (col + 1) * width // 4, (row + 1) * height // 2)
            cell = sheet.crop(bounds)
            cell = keep_largest_component(cell)
            # The source art is cropped flush to each cell's edge (zero margin),
            # which hard-clips the antialiased hair/horn and foot pixels right at
            # the boundary. After downscaling and binarizing alpha for the GIF
            # palette, that clipped edge detaches into a floating sliver with a
            # gap above/below the character. Re-cropping to the tight content
            # bbox and re-adding a small transparent margin lets that edge fade
            # out fully within the frame instead of being cut mid-fade.
            content = cell.crop(cell.getbbox())
            pad = max(8, round(max(content.size) * 0.04))
            padded = Image.new('RGBA', (content.width + 2 * pad, content.height + 2 * pad))
            padded.paste(content, (pad, pad), content)
            padded.thumbnail((296, 296), Image.Resampling.LANCZOS)
            frame = Image.new('RGBA', (320, 320))
            # Anchor every frame to the same bottom baseline and horizontal
            # center (the monster's feet) rather than centering each frame's
            # own bounding box, so frames don't jitter vertically relative to
            # each other when played back.
            frame.alpha_composite(padded, ((320 - padded.width) // 2, 320 - 12 - padded.height))
            frames.append(frame)
    frames[0].save(ROOT / 'monster-talking-still.png')

    # Use one palette for every frame, avoiding flickering colors. GIF reserves
    # index 255 for transparency; the full-alpha PNG remains the static poster.
    atlas = Image.new('RGB', (320 * len(frames), 320), 'white')
    for index, frame in enumerate(frames):
        atlas.paste(frame, (320 * index, 0), frame)
    palette = atlas.quantize(colors=255)
    indexed_frames = []
    for frame in frames:
        matte = Image.new('RGB', frame.size, 'white')
        matte.paste(frame, mask=frame.getchannel('A'))
        indexed = matte.quantize(palette=palette, dither=Image.Dither.NONE)
        # Downscaling can thin a hair-thin connection (e.g. a horn's narrow
        # base) below this 128 cutoff even though it read as solid before
        # scaling, splitting off a tiny fleck right at the cutoff boundary.
        # Re-applying the largest-component filter here catches that case too.
        opaque = largest_component_mask(np.array(frame.getchannel('A')) >= 128)
        transparent = Image.fromarray((~opaque * 255).astype('uint8'))
        indexed.paste(255, mask=transparent)
        indexed.info['transparency'] = 255
        indexed_frames.append(indexed)

    # Speech syllables, blink, cookie lift, bite, chew, then a return to speaking.
    order = [0, 1, 2, 1, 0, 3, 0, 4, 5, 6, 7, 6, 7, 0]
    durations = [340, 160, 200, 160, 280, 130, 200, 280, 240, 220, 240, 200, 240, 300]
    sequence = [indexed_frames[index] for index in order]
    destination = ROOT / 'monster-talking.gif'
    sequence[0].save(destination, save_all=True, append_images=sequence[1:],
                     duration=durations, loop=0, transparency=255,
                     disposal=2, optimize=False)
    print(f'Saved {destination.name}: {len(sequence)} frames, {sum(durations)} ms loop')


if __name__ == '__main__':
    build(Path(sys.argv[1]))

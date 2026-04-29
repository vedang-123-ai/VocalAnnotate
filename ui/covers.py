"""Book cover image handling: pick from disk, normalize, cache thumbnails."""

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COVERS_DIR = PROJECT_ROOT / "assets" / "covers"
STORE_SIZE = (256, 256)  # source-of-truth size on disk

_thumbnail_cache: dict = {}


def _ensure_dir():
    COVERS_DIR.mkdir(parents=True, exist_ok=True)


def _absolute(rel_or_abs: str) -> Path:
    p = Path(rel_or_abs)
    return p if p.is_absolute() else PROJECT_ROOT / p


def pick_cover(book_id: int):
    """Open a file dialog, normalize the chosen image, save under assets/covers/.

    Returns the relative path stored in DB (e.g. "assets/covers/3.png"), or None
    if the user cancelled or the file couldn't be read.
    """
    path = filedialog.askopenfilename(
        title="Choose a cover image",
        filetypes=[
            ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("All files", "*.*"),
        ],
    )
    if not path:
        return None

    try:
        img = Image.open(path)
    except (OSError, ValueError):
        return None

    img = img.convert("RGB")
    img = _center_crop_square(img)
    img = img.resize(STORE_SIZE, Image.LANCZOS)

    _ensure_dir()
    out = COVERS_DIR / f"{book_id}.png"
    img.save(out, "PNG", optimize=True)

    rel = out.relative_to(PROJECT_ROOT).as_posix()
    invalidate(rel)
    return rel


def _center_crop_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


def load_thumbnail(rel_path: str, size: int = 32):
    """Return a CTkImage at the given pixel size, or None if path is missing.

    Cached by (path, size) to keep _load_books() cheap.
    """
    if not rel_path:
        return None
    abs_path = _absolute(rel_path)
    if not abs_path.exists():
        return None

    key = (rel_path, size)
    cached = _thumbnail_cache.get(key)
    if cached is not None:
        return cached

    try:
        pil_img = Image.open(abs_path).convert("RGBA")
    except (OSError, ValueError):
        return None

    pil_img.thumbnail((size * 2, size * 2), Image.LANCZOS)
    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
    _thumbnail_cache[key] = ctk_img
    return ctk_img


def invalidate(rel_path: str) -> None:
    """Drop cached thumbnails for a given path (e.g. after a re-upload)."""
    for key in list(_thumbnail_cache.keys()):
        if key[0] == rel_path:
            del _thumbnail_cache[key]


def delete_cover(rel_path) -> None:
    """Remove the cover file from disk and clear its cache. No-op if missing."""
    if not rel_path:
        return
    abs_path = _absolute(rel_path)
    try:
        if abs_path.exists():
            os.remove(abs_path)
    except OSError:
        pass
    invalidate(str(rel_path))

"""Central palette + typography tokens for VocalAnnotate.

All visual styling reads from here. Never hardcode hex values in ui/app.py —
add a token here and reference it via self.colors[...] / FONTS[...] so dark
mode keeps working.
"""

LIGHT = {
    "bg":           "#FAF6EC",  # warm cream parchment (window background)
    "sidebar_bg":   "#F1E9D2",  # deeper parchment (sidebar)
    "card_bg":      "#FFFCF3",  # near-white cream (cards, header, input)
    "accent":       "#1F5D3A",  # deep emerald (primary buttons, mic idle)
    "accent_hover": "#164A2C",
    "secondary":    "#8B2E3C",  # burgundy (selected book, active dropdown)
    "highlight":    "#C9A227",  # antique gold (page badges, highlights)
    "text_dark":    "#1A1410",  # ink black (body text)
    "text_mid":     "#4A4039",
    "text_light":   "#8A7F73",
    "border":       "#D8CDB4",
    "success":      "#2E7D52",
    "danger":       "#A8281E",
    "mic_idle":     "#1F5D3A",
    "mic_active":   "#A8281E",
    "page_badge":   "#C9A227",
    "on_accent":    "#FFFCF3",  # text/icon on top of accent fills
    "on_secondary": "#FFFCF3",
    "hover_soft":   "#EBDEB8",  # subtle row hover
    "danger_soft":  "#F5DAD7",  # subtle delete-button hover
}

DARK = {
    "bg":           "#161B26",  # midnight navy
    "sidebar_bg":   "#1E2535",
    "card_bg":      "#242C3D",
    "accent":       "#5DD39E",  # soft jade
    "accent_hover": "#7FE3B5",
    "secondary":    "#E0A458",  # warm amber (selected/active)
    "highlight":    "#E0A458",
    "text_dark":    "#F5EFE0",  # warm cream text
    "text_mid":     "#B8AE9C",
    "text_light":   "#7E7668",
    "border":       "#2F3850",
    "success":      "#5DD39E",
    "danger":       "#E07A6E",
    "mic_idle":     "#5DD39E",
    "mic_active":   "#E07A6E",
    "page_badge":   "#E0A458",
    "on_accent":    "#161B26",  # dark text on light jade buttons
    "on_secondary": "#161B26",
    "hover_soft":   "#2A3346",
    "danger_soft":  "#3D2530",
}

FONTS = {
    "title":   ("Georgia", 20, "bold"),
    "head":    ("Georgia", 15, "bold"),
    "body":    ("Georgia", 13),
    "small":   ("Georgia", 11),
    "mono":    ("Courier", 12),
    "big_mic": ("Georgia", 28),
    "label":   ("Georgia", 10, "bold"),
}


def get_palette(mode: str) -> dict:
    """Return LIGHT or DARK palette dict. Defaults to LIGHT for any unknown mode."""
    return DARK if mode == "dark" else LIGHT


def ctk_appearance(mode: str) -> str:
    """Map our mode string to CustomTkinter's appearance mode value."""
    return "dark" if mode == "dark" else "light"

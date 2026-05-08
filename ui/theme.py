"""Central palette + typography tokens for VocalAnnotate.

Aesthetic direction — "Refined library":
    Warm parchment surfaces with an ink-blue primary accent. Oxblood is
    reserved as a scarce signal color (selected book only). Antique gold
    carries numerical emphasis (page headings). Typography pairs Iowan Old
    Style (macOS-bundled scholarly serif) for editorial content with
    Avenir Next for UI chrome — replacing the previous all-Georgia stack.

All visual styling reads from here. Never hardcode hex or font tuples in
ui/app.py — add a token and reference it via self.colors[...] / FONTS[...]
so dark mode keeps working.
"""

LIGHT = {
    # Surfaces (warm parchment scale)
    "bg":             "#F4EEDD",  # window background — warm parchment
    "sidebar_bg":     "#ECE4CE",  # deeper parchment — left rail
    "card_bg":        "#FBF6E5",  # card / cluster fill
    "surface_alt":    "#FFFCEF",  # input surface, segmented unselected

    # Inks
    "text_dark":      "#15110C",  # near-black ink
    "text_mid":       "#5B5046",
    "text_light":     "#998D7B",
    "wordmark":       "#15110C",

    # Accents
    "accent":         "#1F3A5F",  # ink blue — primary affordance
    "accent_hover":   "#15294A",
    "accent_soft":    "#DCE2EB",  # tinted background for tagged pills
    "secondary":      "#7A2330",  # oxblood — selection signal (scarce)
    "secondary_soft": "#EDD8D9",
    "highlight":      "#B68A3A",  # antique gold — page numerals

    # Functional
    "success":        "#2E7D52",
    "danger":         "#9C2A1F",
    "danger_soft":    "#EFD8D2",

    # Lines & states
    "border":         "#D5C8AC",
    "divider":        "#E8DEC4",  # softer than border, hairlines
    "hover_soft":     "#E5DBC0",

    # On-fill text (flips with theme so contrast stays readable)
    "on_accent":      "#FBF6E5",
    "on_secondary":   "#FBF6E5",

    # Back-compat aliases used by app.py and frontend.md
    "mic_idle":       "#1F3A5F",
    "mic_active":     "#9C2A1F",
    "page_badge":     "#B68A3A",
}

DARK = {
    "bg":             "#11161E",  # deep midnight
    "sidebar_bg":     "#18202C",
    "card_bg":        "#1E2735",
    "surface_alt":    "#25304A",

    "text_dark":      "#F0E6D2",  # warm parchment text on dark
    "text_mid":       "#B6AA90",
    "text_light":     "#7B7264",
    "wordmark":       "#F0E6D2",

    "accent":         "#8AB4DC",  # soft sky blue
    "accent_hover":   "#A6C7E5",
    "accent_soft":    "#213047",
    "secondary":      "#DA8B95",  # warm rose — selection signal
    "secondary_soft": "#382128",
    "highlight":      "#DAB073",

    "success":        "#5DD39E",
    "danger":         "#E07A6E",
    "danger_soft":    "#3A2630",

    "border":         "#28344B",
    "divider":        "#1F2A3D",
    "hover_soft":     "#243047",

    "on_accent":      "#11161E",
    "on_secondary":   "#11161E",

    "mic_idle":       "#8AB4DC",
    "mic_active":     "#E07A6E",
    "page_badge":     "#DAB073",
}

# Font families — chosen for distinctive personality. macOS-bundled so they
# resolve without extra installs; Tk falls back automatically if absent.
_SERIF = "Iowan Old Style"      # scholarly, generous, slightly old-style
_SANS = "Avenir Next"            # modern humanist sans for chrome
_MONO = "Menlo"

FONTS = {
    # Editorial / display
    "wordmark":   (_SERIF, 22, "bold"),
    "tagline":    (_SERIF, 11, "italic"),
    "title":      (_SERIF, 28, "bold"),
    "head":       (_SERIF, 17, "bold"),
    "page_num":   (_SERIF, 26, "bold"),

    # Body
    "body":       (_SERIF, 14),
    "body_small": (_SERIF, 12),

    # UI chrome
    "subtitle":   (_SANS, 12),
    "small":      (_SANS, 11),
    "label":      (_SANS, 10, "bold"),       # all-caps section labels
    "btn":        (_SANS, 12),
    "btn_bold":   (_SANS, 12, "bold"),
    "big_mic":    (_SANS, 22),
    "mono":       (_MONO, 12),
}


def get_palette(mode: str) -> dict:
    """Return LIGHT or DARK palette dict. Defaults to LIGHT for unknown mode."""
    return DARK if mode == "dark" else LIGHT


def ctk_appearance(mode: str) -> str:
    """Map our mode string to CustomTkinter's appearance mode value."""
    return "dark" if mode == "dark" else "light"

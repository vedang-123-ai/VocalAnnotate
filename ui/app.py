"""
VocalAnnotate - Main Application
A voice-first annotation companion for students reading physical books.

Aesthetic: refined library — warm parchment surfaces, ink-blue accent,
oxblood as a scarce selection signal, antique gold for numerical emphasis.
See frontend.md for the full design language.
"""

import customtkinter as ctk
import tkinter.messagebox
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import (
    add_book, get_all_books, delete_book,
    add_annotation, get_annotations_for_book, delete_annotation,
    add_theme, get_themes_for_book, delete_theme, update_annotation_theme,
    update_book_cover,
)
from voice.parser import parse_annotation
from voice.recorder import VoiceRecorder

from ui import theme, preferences, covers
from ui.theme import FONTS

UNCLASSIFIED = "Unclassified"
ALL_FILTER = "All"


class VocalAnnotateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VocalAnnotate")
        self.geometry("1180x760")
        self.minsize(960, 620)

        self.prefs = preferences.load()
        self.appearance_mode = self.prefs.get("appearance_mode", "light")
        self.colors = theme.get_palette(self.appearance_mode)
        ctk.set_appearance_mode(theme.ctk_appearance(self.appearance_mode))
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=self.colors["bg"])

        self.recorder = VoiceRecorder()
        self.selected_book_id = None
        self.selected_book_title = ""
        self._status_timer = None
        self.sort_mode = "page"       # "page" | "newest" | "oldest"
        self.theme_filter = None      # None | "unclassified" | int (theme_id)

        self._build_layout()
        self._load_books()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_panel()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=272, corner_radius=0,
            fg_color=self.colors["sidebar_bg"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(4, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        # Wordmark — editorial title block
        wm = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        wm.grid(row=0, column=0, padx=24, pady=(28, 0), sticky="ew")

        ctk.CTkLabel(
            wm, text="VocalAnnotate",
            font=FONTS["wordmark"], text_color=self.colors["wordmark"],
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            wm, text="a voice-first reading companion",
            font=FONTS["tagline"], text_color=self.colors["text_light"],
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        # Hairline rule under wordmark
        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.colors["divider"]).grid(
            row=1, column=0, sticky="ew", padx=24, pady=(20, 18)
        )

        # Add-book module
        add_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        add_frame.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            add_frame, text="ADD A BOOK", font=FONTS["label"],
            text_color=self.colors["text_light"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.book_entry = ctk.CTkEntry(
            add_frame, placeholder_text="New book title",
            font=FONTS["body_small"], height=34,
            fg_color=self.colors["surface_alt"],
            border_color=self.colors["border"], border_width=1,
            text_color=self.colors["text_dark"],
            placeholder_text_color=self.colors["text_light"],
            corner_radius=6,
        )
        self.book_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.book_entry.bind("<Return>", lambda e: self._add_book())

        ctk.CTkButton(
            add_frame, text="+", width=34, height=34,
            font=FONTS["btn_bold"],
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            corner_radius=6,
            command=self._add_book,
        ).grid(row=1, column=1)

        # Library label
        ctk.CTkLabel(
            self.sidebar, text="LIBRARY", font=FONTS["label"],
            text_color=self.colors["text_light"], anchor="w",
        ).grid(row=3, column=0, padx=24, pady=(22, 6), sticky="ew")

        self.book_list_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=self.colors["border"],
            scrollbar_button_hover_color=self.colors["text_light"],
        )
        self.book_list_frame.grid(row=4, column=0, sticky="nsew", padx=14, pady=(0, 16))
        self.book_list_frame.grid_columnconfigure(0, weight=1)

    def _build_main_panel(self):
        self.main = ctk.CTkFrame(self, fg_color=self.colors["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main.grid_rowconfigure(2, weight=1)  # ann_scroll grows
        self.main.grid_columnconfigure(0, weight=1)

        # ── Header (row 0) ────────────────────────────────────────────────────
        self.header_frame = ctk.CTkFrame(
            self.main, fg_color=self.colors["bg"], corner_radius=0,
        )
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=32, pady=(28, 0))
        self.header_frame.grid_columnconfigure(0, weight=1)

        # Title + appearance toggle (row 0 of header)
        self.book_title_label = ctk.CTkLabel(
            self.header_frame, text="Select or create a book to begin",
            font=FONTS["title"], text_color=self.colors["text_dark"], anchor="w",
        )
        self.book_title_label.grid(row=0, column=0, sticky="w")

        toggle_text = "◐" if self.appearance_mode == "light" else "◑"
        self.theme_toggle_btn = ctk.CTkButton(
            self.header_frame, text=toggle_text,
            width=36, height=32, corner_radius=16,
            font=FONTS["btn_bold"],
            fg_color="transparent", hover_color=self.colors["hover_soft"],
            text_color=self.colors["text_mid"],
            border_width=1, border_color=self.colors["border"],
            command=self._toggle_appearance,
        )
        self.theme_toggle_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Subtitle row: count (left) + sort (right)
        sub = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        sub.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 18))
        sub.grid_columnconfigure(0, weight=1)

        self.annotation_count_label = ctk.CTkLabel(
            sub, text="",
            font=FONTS["subtitle"], text_color=self.colors["text_light"], anchor="w",
        )
        self.annotation_count_label.grid(row=0, column=0, sticky="w")

        # text_color is single across all segments, so unselected_color must
        # contrast with `on_accent` too — text_mid sits at the right weight
        # in both modes.
        self.sort_btn = ctk.CTkSegmentedButton(
            sub,
            values=["Page", "Newest", "Oldest"],
            command=self._on_sort_change,
            font=FONTS["small"],
            selected_color=self.colors["accent"],
            selected_hover_color=self.colors["accent_hover"],
            unselected_color=self.colors["text_mid"],
            unselected_hover_color=self.colors["text_dark"],
            text_color=self.colors["on_accent"],
            text_color_disabled=self.colors["text_light"],
            height=28,
            corner_radius=6,
        )
        self.sort_btn.set({"page": "Page", "newest": "Newest", "oldest": "Oldest"}[self.sort_mode])
        self.sort_btn.grid(row=0, column=1, sticky="e")

        # Hairline rule beneath header
        ctk.CTkFrame(self.header_frame, height=1, fg_color=self.colors["divider"]).grid(
            row=2, column=0, columnspan=2, sticky="ew"
        )

        # ── Themes bar (row 1) ────────────────────────────────────────────────
        self._build_themes_bar()

        # ── Annotation area (row 2) ───────────────────────────────────────────
        self.ann_scroll = ctk.CTkScrollableFrame(
            self.main, fg_color=self.colors["bg"],
            scrollbar_button_color=self.colors["border"],
            scrollbar_button_hover_color=self.colors["text_light"],
        )
        self.ann_scroll.grid(row=2, column=0, sticky="nsew", padx=24, pady=(8, 8))
        self.ann_scroll.grid_columnconfigure(0, weight=1)

        self._render_empty_state()

        # ── Bottom input bar (row 3) ──────────────────────────────────────────
        self._build_input_bar()

    def _build_themes_bar(self):
        # Transparent bar — sits flush in the page rhythm.
        self.themes_bar = ctk.CTkFrame(self.main, fg_color="transparent", corner_radius=0)
        # Not gridded until a book is selected.

    def _build_input_bar(self):
        self.input_bar = ctk.CTkFrame(
            self.main, fg_color=self.colors["card_bg"], corner_radius=14,
            border_width=1, border_color=self.colors["border"],
        )
        self.input_bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(8, 18))
        self.input_bar.grid_columnconfigure(1, weight=1)

        # Mic — large, perfectly round
        self.mic_btn = ctk.CTkButton(
            self.input_bar, text="🎤", width=58, height=58,
            font=FONTS["big_mic"],
            fg_color=self.colors["mic_idle"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            corner_radius=29,
            command=self._toggle_voice,
        )
        self.mic_btn.grid(row=0, column=0, rowspan=2, padx=(16, 14), pady=14)

        # Status line above the input
        self.status_label = ctk.CTkLabel(
            self.input_bar,
            text='Speak or type — try “page 42, theme symbolism, the green light”',
            font=FONTS["small"], text_color=self.colors["text_light"], anchor="w",
        )
        self.status_label.grid(row=0, column=1, columnspan=2, sticky="ew", padx=4, pady=(12, 2))

        # Manual entry + save button on the same row
        self.manual_entry = ctk.CTkEntry(
            self.input_bar,
            placeholder_text='page 47, theme patriarchy, symbolism of green light',
            font=FONTS["body_small"], height=38,
            fg_color=self.colors["surface_alt"],
            border_color=self.colors["border"], border_width=1,
            text_color=self.colors["text_dark"],
            placeholder_text_color=self.colors["text_light"],
            corner_radius=8,
        )
        self.manual_entry.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=(0, 14))
        self.manual_entry.bind("<Return>", lambda e: self._submit_manual())

        ctk.CTkButton(
            self.input_bar, text="Save", width=82, height=38,
            font=FONTS["btn_bold"],
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            corner_radius=8,
            command=self._submit_manual,
        ).grid(row=1, column=2, padx=(0, 16), pady=(0, 14))

    # ── Theme Mode (Dark/Light) ────────────────────────────────────────────────

    def _toggle_appearance(self):
        self.appearance_mode = "dark" if self.appearance_mode == "light" else "light"
        self.prefs["appearance_mode"] = self.appearance_mode
        preferences.save(self.prefs)
        self.colors = theme.get_palette(self.appearance_mode)
        ctk.set_appearance_mode(theme.ctk_appearance(self.appearance_mode))
        self._apply_theme()

    def _apply_theme(self):
        """Rebuild the entire layout with the current palette.

        CTk doesn't expose a clean way to recolor every widget in-place, so we
        tear down sidebar + main and rebuild. State (selection, filters, sort)
        is preserved on `self`.
        """
        self.configure(fg_color=self.colors["bg"])
        for child in (self.sidebar, self.main):
            child.destroy()
        self._build_layout()
        self._load_books()
        if self.selected_book_id is not None:
            self.book_title_label.configure(text=self.selected_book_title)
            self._refresh_themes_bar()
            self._load_annotations()

    # ── Book Logic ─────────────────────────────────────────────────────────────

    def _load_books(self):
        for widget in self.book_list_frame.winfo_children():
            widget.destroy()

        books = get_all_books()
        for b in books:
            self._render_book_row(b["id"], b["title"], b.get("cover_path"))

        if not books:
            ctk.CTkLabel(
                self.book_list_frame,
                text="No books yet.\nAdd one above.",
                font=FONTS["small"], text_color=self.colors["text_light"],
                justify="center",
            ).pack(pady=24)

    def _render_book_row(self, book_id, title, cover_path):
        is_selected = (book_id == self.selected_book_id)
        row_bg = self.colors["secondary"] if is_selected else "transparent"
        txt_color = self.colors["on_secondary"] if is_selected else self.colors["text_dark"]
        sub_color = self.colors["on_secondary"] if is_selected else self.colors["text_light"]
        hover = self.colors["secondary"] if is_selected else self.colors["hover_soft"]
        del_hover = self.colors["secondary"] if is_selected else self.colors["danger_soft"]

        row = ctk.CTkFrame(self.book_list_frame, fg_color=row_bg, corner_radius=8)
        row.pack(fill="x", pady=2, padx=2)
        row.grid_columnconfigure(1, weight=1)

        thumb = covers.load_thumbnail(cover_path, size=30) if cover_path else None
        if thumb is not None:
            label_text = f"  {title[:24]}{'…' if len(title) > 24 else ''}"
            btn = ctk.CTkButton(
                row, text=label_text, image=thumb, compound="left",
                font=FONTS["btn"], anchor="w",
                fg_color="transparent", hover_color=hover,
                text_color=txt_color,
                height=44, corner_radius=8,
                command=lambda bid=book_id, t=title: self._select_book(bid, t),
            )
        else:
            btn = ctk.CTkButton(
                row, text=f"📖   {title[:24]}{'…' if len(title) > 24 else ''}",
                font=FONTS["btn"], anchor="w",
                fg_color="transparent", hover_color=hover,
                text_color=txt_color,
                height=44, corner_radius=8,
                command=lambda bid=book_id, t=title: self._select_book(bid, t),
            )
        btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=2)

        cover_btn = ctk.CTkButton(
            row, text="🖼", width=24, height=24,
            font=FONTS["small"],
            fg_color="transparent", hover_color=hover,
            text_color=sub_color,
            command=lambda bid=book_id: self._set_cover(bid),
        )
        cover_btn.grid(row=0, column=2, padx=(0, 2))

        del_btn = ctk.CTkButton(
            row, text="×", width=24, height=24,
            font=FONTS["btn_bold"],
            fg_color="transparent", hover_color=del_hover,
            text_color=sub_color,
            command=lambda bid=book_id: self._delete_book(bid),
        )
        del_btn.grid(row=0, column=3, padx=(0, 4))

    def _add_book(self):
        title = self.book_entry.get().strip()
        if not title:
            return
        book = add_book(title)
        self.book_entry.delete(0, "end")
        self._load_books()
        self._select_book(book.id, book.title)

    def _delete_book(self, book_id):
        # Look up the cover path before deletion so we can clean up the file too
        existing = next((b for b in get_all_books() if b["id"] == book_id), None)
        cover_path = existing.get("cover_path") if existing else None

        delete_book(book_id)
        if cover_path:
            covers.delete_cover(cover_path)

        if self.selected_book_id == book_id:
            self.selected_book_id = None
            self.selected_book_title = ""
            self.sort_mode = "page"
            self.theme_filter = None
            self.sort_btn.set("Page")
            self.book_title_label.configure(text="Select or create a book to begin")
            self.annotation_count_label.configure(text="")
            self._clear_annotations()
            self._refresh_themes_bar()
        self._load_books()

    def _select_book(self, book_id, title):
        self.selected_book_id = book_id
        self.selected_book_title = title
        self.sort_mode = "page"
        self.theme_filter = None
        self.sort_btn.set("Page")
        self.book_title_label.configure(text=title)
        self._load_books()
        self._refresh_themes_bar()
        self._load_annotations()

    def _set_cover(self, book_id):
        rel = covers.pick_cover(book_id)
        if rel is None:
            return
        update_book_cover(book_id, rel)
        self._load_books()

    # ── Themes Bar ─────────────────────────────────────────────────────────────

    def _refresh_themes_bar(self):
        for w in self.themes_bar.winfo_children():
            w.destroy()

        if not self.selected_book_id:
            self.themes_bar.grid_remove()
            return

        self.themes_bar.grid(row=1, column=0, sticky="ew", padx=32, pady=(14, 4))

        themes = get_themes_for_book(self.selected_book_id)
        theme_names = [t["name"] for t in themes]
        self._theme_name_to_id = {t["name"]: t["id"] for t in themes}

        ctk.CTkLabel(
            self.themes_bar, text="THEMES",
            font=FONTS["label"], text_color=self.colors["text_light"],
        ).pack(side="left", padx=(0, 12))

        # Filter dropdown
        filter_values = [ALL_FILTER, UNCLASSIFIED] + theme_names
        current = self._current_filter_label(themes)
        is_filtered = self.theme_filter is not None
        self._filter_menu = ctk.CTkOptionMenu(
            self.themes_bar,
            values=filter_values,
            command=self._on_filter_select,
            font=FONTS["small"],
            dropdown_font=FONTS["small"],
            fg_color=self.colors["secondary"] if is_filtered else self.colors["surface_alt"],
            text_color=self.colors["on_secondary"] if is_filtered else self.colors["text_dark"],
            button_color=self.colors["secondary"] if is_filtered else self.colors["surface_alt"],
            button_hover_color=self.colors["accent_hover"] if is_filtered else self.colors["hover_soft"],
            dropdown_fg_color=self.colors["card_bg"],
            dropdown_text_color=self.colors["text_dark"],
            dropdown_hover_color=self.colors["hover_soft"],
            width=160, height=28, corner_radius=14,
        )
        self._filter_menu.set(current)
        self._filter_menu.pack(side="left", padx=(0, 12))

        # Inline new-theme entry
        self._theme_entry = ctk.CTkEntry(
            self.themes_bar, placeholder_text="New theme",
            font=FONTS["small"], height=28, width=160,
            fg_color=self.colors["surface_alt"],
            border_color=self.colors["border"], border_width=1,
            text_color=self.colors["text_dark"],
            placeholder_text_color=self.colors["text_light"],
            corner_radius=6,
        )
        self._theme_entry.pack(side="left", padx=(0, 4))
        self._theme_entry.bind("<Return>", lambda e: self._add_theme())

        ctk.CTkButton(
            self.themes_bar, text="+", width=28, height=28,
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            font=FONTS["btn_bold"], corner_radius=6,
            command=self._add_theme,
        ).pack(side="left")

        ctk.CTkButton(
            self.themes_bar, text="Manage",
            width=82, height=28, corner_radius=14,
            font=FONTS["small"],
            fg_color="transparent", hover_color=self.colors["hover_soft"],
            text_color=self.colors["text_mid"],
            border_width=1, border_color=self.colors["border"],
            command=self._open_manage_themes,
        ).pack(side="right")

    def _current_filter_label(self, themes):
        if self.theme_filter is None:
            return ALL_FILTER
        if self.theme_filter == "unclassified":
            return UNCLASSIFIED
        match = next((t for t in themes if t["id"] == self.theme_filter), None)
        return match["name"] if match else ALL_FILTER

    def _on_filter_select(self, value):
        if value == ALL_FILTER:
            self._set_theme_filter(None)
        elif value == UNCLASSIFIED:
            self._set_theme_filter("unclassified")
        else:
            tid = self._theme_name_to_id.get(value)
            self._set_theme_filter(tid)

    def _set_theme_filter(self, value):
        self.theme_filter = value
        self._refresh_themes_bar()
        self._load_annotations()

    def _add_theme(self):
        if not hasattr(self, "_theme_entry"):
            return
        name = self._theme_entry.get().strip()
        if not name:
            return
        try:
            add_theme(self.selected_book_id, name)
            self._theme_entry.delete(0, "end")
            self._refresh_themes_bar()
            self._load_annotations()
        except Exception:
            self._set_status(
                f'⚠ Theme "{name}" already exists for this book.',
                color=self.colors["danger"], duration=3000,
            )

    def _open_manage_themes(self):
        themes = get_themes_for_book(self.selected_book_id)

        modal = ctk.CTkToplevel(self)
        modal.title("Manage themes")
        modal.geometry("420x460")
        modal.configure(fg_color=self.colors["bg"])
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal, text="Themes",
            font=FONTS["title"], text_color=self.colors["text_dark"],
            anchor="w",
        ).pack(pady=(20, 0), padx=24, anchor="w")
        ctk.CTkLabel(
            modal, text=self.selected_book_title,
            font=FONTS["tagline"], text_color=self.colors["text_light"],
            anchor="w",
        ).pack(pady=(2, 12), padx=24, anchor="w")
        ctk.CTkLabel(
            modal,
            text="Deleting a theme keeps its annotations — they become Unclassified.",
            font=FONTS["small"], text_color=self.colors["text_mid"],
            wraplength=370, justify="left",
        ).pack(pady=(0, 14), padx=24, anchor="w")

        scroll = ctk.CTkScrollableFrame(
            modal, fg_color=self.colors["card_bg"],
            scrollbar_button_color=self.colors["border"],
            corner_radius=10,
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)

        if not themes:
            ctk.CTkLabel(
                scroll, text="No themes yet.",
                font=FONTS["body"], text_color=self.colors["text_light"],
            ).grid(row=0, column=0, pady=24)

        for i, t in enumerate(themes):
            ctk.CTkLabel(
                scroll, text=t["name"], anchor="w",
                font=FONTS["body"], text_color=self.colors["text_dark"],
            ).grid(row=i, column=0, sticky="ew", padx=14, pady=8)

            ctk.CTkButton(
                scroll, text="Delete", width=72, height=26,
                font=FONTS["small"],
                fg_color="transparent", hover_color=self.colors["danger_soft"],
                text_color=self.colors["danger"],
                border_width=1, border_color=self.colors["danger"],
                corner_radius=6,
                command=lambda tid=t["id"], tn=t["name"], m=modal: self._delete_theme_from_modal(tid, tn, m),
            ).grid(row=i, column=1, padx=(0, 14), pady=8)

        ctk.CTkButton(
            modal, text="Done", height=36, corner_radius=8,
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"], font=FONTS["btn_bold"],
            command=modal.destroy,
        ).pack(pady=(0, 20), padx=24, fill="x")

    def _delete_theme_from_modal(self, theme_id, theme_name, modal):
        confirmed = tkinter.messagebox.askyesno(
            "Delete Theme",
            f'Delete theme "{theme_name}"?\n\nAnnotations tagged with this theme will become Unclassified.',
            parent=modal,
        )
        if not confirmed:
            return
        delete_theme(theme_id)
        if self.theme_filter == theme_id:
            self.theme_filter = None
        modal.destroy()
        self._refresh_themes_bar()
        self._load_annotations()
        self._open_manage_themes()  # reopen with refreshed list

    # ── Annotation Logic ───────────────────────────────────────────────────────

    def _render_empty_state(self):
        self._empty_label = ctk.CTkLabel(
            self.ann_scroll,
            text=(
                "No annotations yet.\n\n"
                "Click the mic to record, or type a note below.\n"
                "Try:  page 42, theme symbolism, the green light"
            ),
            font=FONTS["body"], text_color=self.colors["text_light"],
            justify="center",
        )
        self._empty_label.grid(row=0, column=0, pady=80)

    def _load_annotations(self):
        self._clear_annotations()
        if not self.selected_book_id:
            return

        themes = get_themes_for_book(self.selected_book_id)
        anns = get_annotations_for_book(
            self.selected_book_id,
            sort_by=self.sort_mode,
            theme_filter=self.theme_filter,
        )

        count = len(anns)
        filter_label = ""
        if self.theme_filter == "unclassified":
            filter_label = " — Unclassified"
        elif self.theme_filter is not None:
            t = next((t for t in themes if t["id"] == self.theme_filter), None)
            filter_label = f" — {t['name']}" if t else ""
        self.annotation_count_label.configure(
            text=f"{count} annotation{'s' if count != 1 else ''}{filter_label}"
        )

        if not anns:
            self._render_empty_state()
            return

        row_idx = 0
        if self.sort_mode == "page":
            last_page = None
            for ann in anns:
                if ann["page"] != last_page:
                    last_page = ann["page"]
                    self._render_page_header(row_idx, ann["page"])
                    row_idx += 1
                self._render_annotation_card(row_idx, ann, themes)
                row_idx += 1
        else:
            for ann in anns:
                self._render_annotation_card(row_idx, ann, themes)
                row_idx += 1

    def _render_page_header(self, row, page):
        """Editorial page heading: small caps PAGE + large gold numeral + rule."""
        frame = ctk.CTkFrame(self.ann_scroll, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=(22, 6), padx=2)

        ctk.CTkLabel(
            frame, text="PAGE",
            font=FONTS["label"], text_color=self.colors["text_light"],
        ).pack(side="left", padx=(2, 10), pady=(14, 0))

        ctk.CTkLabel(
            frame, text=str(page),
            font=FONTS["page_num"], text_color=self.colors["highlight"],
        ).pack(side="left")

        ctk.CTkFrame(frame, height=1, fg_color=self.colors["divider"]).pack(
            side="left", fill="x", expand=True, padx=(16, 4), pady=(20, 0)
        )

    def _render_annotation_card(self, row, ann, themes):
        card = ctk.CTkFrame(
            self.ann_scroll, fg_color=self.colors["card_bg"],
            corner_radius=10, border_width=0,
        )
        card.grid(row=row, column=0, sticky="ew", pady=5, padx=2)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=ann["note"],
            font=FONTS["body"], text_color=self.colors["text_dark"],
            anchor="w", wraplength=720, justify="left",
        ).grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))
        footer.grid_columnconfigure(2, weight=1)

        ts = ann["created_at"].strftime("%b %d · %I:%M %p") if ann["created_at"] else ""
        ctk.CTkLabel(
            footer, text=ts, font=FONTS["small"], text_color=self.colors["text_light"],
        ).grid(row=0, column=0, sticky="w")

        # Theme reassignment dropdown — pill style; tinted when tagged.
        theme_options = [UNCLASSIFIED] + [t["name"] for t in themes]
        theme_map = {t["name"]: t["id"] for t in themes}
        current_theme = ann["theme_name"] if ann["theme_name"] else UNCLASSIFIED
        is_tagged = bool(ann["theme_name"])

        theme_menu = ctk.CTkOptionMenu(
            footer,
            values=theme_options,
            command=lambda val, aid=ann["id"]: self._on_reassign_theme(aid, val, theme_map),
            width=140, height=24, font=FONTS["small"], corner_radius=12,
            fg_color=self.colors["accent_soft"] if is_tagged else self.colors["surface_alt"],
            text_color=self.colors["accent"] if is_tagged else self.colors["text_mid"],
            button_color=self.colors["accent_soft"] if is_tagged else self.colors["surface_alt"],
            button_hover_color=self.colors["hover_soft"],
            dropdown_font=FONTS["small"],
            dropdown_fg_color=self.colors["card_bg"],
            dropdown_text_color=self.colors["text_dark"],
            dropdown_hover_color=self.colors["hover_soft"],
        )
        theme_menu.set(current_theme)
        theme_menu.grid(row=0, column=1, padx=(14, 0), sticky="w")

        ctk.CTkButton(
            footer, text="×", width=26, height=22,
            font=FONTS["btn_bold"],
            fg_color="transparent", hover_color=self.colors["danger_soft"],
            text_color=self.colors["text_light"],
            corner_radius=4,
            command=lambda aid=ann["id"]: self._delete_annotation(aid),
        ).grid(row=0, column=3, sticky="e")

    def _on_reassign_theme(self, ann_id, value, theme_map):
        theme_id = theme_map.get(value) if value != UNCLASSIFIED else None
        update_annotation_theme(ann_id, theme_id)
        self._load_annotations()

    def _clear_annotations(self):
        for widget in self.ann_scroll.winfo_children():
            widget.destroy()

    def _delete_annotation(self, ann_id):
        delete_annotation(ann_id)
        self._load_annotations()

    def _process_transcript(self, transcript: str):
        result = parse_annotation(transcript)
        if result:
            theme_id = None
            parsed_theme = result.get("theme")
            if parsed_theme:
                themes = get_themes_for_book(self.selected_book_id)
                match = next(
                    (t for t in themes if t["name"].lower() == parsed_theme.lower()),
                    None,
                )
                if match:
                    theme_id = match["id"]
                else:
                    self._set_status(
                        f'⚠ Theme "{parsed_theme}" not found — saved as Unclassified. Add it in the themes bar first.',
                        color=self.colors["danger"], duration=5000,
                    )
            self._save_annotation(result["page"], result["note"], theme_id)
        else:
            self._set_status(
                f'⚠ Couldn\'t find a page number in: "{transcript[:60]}"  '
                '· Try: "Page 42, your note"',
                color=self.colors["danger"], duration=5000,
            )

    def _save_annotation(self, page: int, note: str, theme_id=None):
        if not self.selected_book_id:
            self._set_status("⚠ Please select a book first.", color=self.colors["danger"])
            return
        add_annotation(self.selected_book_id, page, note, theme_id=theme_id)
        self._load_annotations()
        self._set_status(
            f"✓ Saved — Page {page}: {note[:50]}{'…' if len(note) > 50 else ''}",
            color=self.colors["success"], duration=3000,
        )

    # ── Sort ───────────────────────────────────────────────────────────────────

    def _on_sort_change(self, value):
        self.sort_mode = {"Page": "page", "Newest": "newest", "Oldest": "oldest"}[value]
        self._load_annotations()

    # ── Voice ──────────────────────────────────────────────────────────────────

    def _toggle_voice(self):
        if self.recorder.is_recording:
            return
        if not self.selected_book_id:
            self._set_status("⚠ Please select a book before recording.", color=self.colors["danger"])
            return
        self._start_recording()

    def _start_recording(self):
        self.mic_btn.configure(fg_color=self.colors["mic_active"], text="⏹")
        self._set_status("🔴 Listening… speak your annotation now", color=self.colors["mic_active"])

        self.recorder.record_and_transcribe(
            on_result=self._on_voice_result,
            on_error=self._on_voice_error,
            on_start=None,
        )

    def _on_voice_result(self, transcript: str):
        self.after(0, lambda: self._handle_voice_result(transcript))

    def _handle_voice_result(self, transcript: str):
        self.mic_btn.configure(fg_color=self.colors["mic_idle"], text="🎤")
        self._set_status(f'Heard: "{transcript}"', color=self.colors["text_mid"], duration=2000)
        self.after(300, lambda: self._process_transcript(transcript))

    def _on_voice_error(self, message: str):
        self.after(0, lambda: self._handle_voice_error(message))

    def _handle_voice_error(self, message: str):
        self.mic_btn.configure(fg_color=self.colors["mic_idle"], text="🎤")
        self._set_status(f"⚠ {message}", color=self.colors["danger"], duration=4000)

    # ── Manual Input ───────────────────────────────────────────────────────────

    def _submit_manual(self):
        text = self.manual_entry.get().strip()
        if not text:
            return
        self.manual_entry.delete(0, "end")
        self._process_transcript(text)

    # ── Status Bar ─────────────────────────────────────────────────────────────

    def _set_status(self, message: str, color: str = None, duration: int = None):
        self.status_label.configure(
            text=message,
            text_color=color or self.colors["text_mid"],
        )
        if self._status_timer:
            self.after_cancel(self._status_timer)
            self._status_timer = None
        if duration:
            self._status_timer = self.after(
                duration,
                lambda: self.status_label.configure(
                    text='Speak or type — try “page 42, theme symbolism, the green light”',
                    text_color=self.colors["text_light"],
                ),
            )


def main():
    app = VocalAnnotateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

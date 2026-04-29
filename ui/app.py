"""
VocalAnnotate - Main Application
A voice-first annotation companion for students reading physical books.
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
        self.geometry("1100x720")
        self.minsize(900, 600)

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
            self, width=240, corner_radius=0,
            fg_color=self.colors["sidebar_bg"],
            border_width=1, border_color=self.colors["border"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(3, weight=1)

        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=16, pady=(20, 4), sticky="ew")

        ctk.CTkLabel(
            title_frame, text="🎙 VocalAnnotate",
            font=("Georgia", 16, "bold"),
            text_color=self.colors["accent"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="voice annotation companion",
            font=FONTS["small"], text_color=self.colors["text_light"]
        ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.colors["border"]).grid(
            row=1, column=0, sticky="ew", padx=12, pady=8
        )

        add_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        add_frame.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            add_frame, text="MY BOOKS", font=FONTS["label"],
            text_color=self.colors["text_light"]
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.book_entry = ctk.CTkEntry(
            add_frame, placeholder_text="New book title...",
            font=FONTS["small"], height=32,
            fg_color=self.colors["card_bg"], border_color=self.colors["border"],
            text_color=self.colors["text_dark"]
        )
        self.book_entry.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.book_entry.bind("<Return>", lambda e: self._add_book())

        ctk.CTkButton(
            add_frame, text="+", width=32, height=32,
            font=("Georgia", 18, "bold"),
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            command=self._add_book
        ).grid(row=1, column=1)

        self.book_list_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=self.colors["border"]
        )
        self.book_list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=4)

    def _build_main_panel(self):
        self.main = ctk.CTkFrame(self, fg_color=self.colors["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main.grid_rowconfigure(2, weight=1)  # ann_scroll is row 2
        self.main.grid_columnconfigure(0, weight=1)

        # Header (row 0)
        self.header_frame = ctk.CTkFrame(
            self.main, fg_color=self.colors["card_bg"], corner_radius=0,
            border_width=1, border_color=self.colors["border"]
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.book_title_label = ctk.CTkLabel(
            self.header_frame, text="Select or create a book to begin",
            font=FONTS["title"], text_color=self.colors["text_dark"], anchor="w"
        )
        self.book_title_label.grid(row=0, column=0, padx=24, pady=(16, 2), sticky="w")

        self.annotation_count_label = ctk.CTkLabel(
            self.header_frame, text="",
            font=FONTS["small"], text_color=self.colors["text_light"], anchor="w"
        )
        self.annotation_count_label.grid(row=1, column=0, padx=24, pady=(0, 14), sticky="w")

        # Sort segmented button (top-right of header)
        self.sort_btn = ctk.CTkSegmentedButton(
            self.header_frame,
            values=["Page", "Newest", "Oldest"],
            command=self._on_sort_change,
            font=FONTS["small"],
            selected_color=self.colors["accent"],
            selected_hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            height=30,
        )
        self.sort_btn.set({"page": "Page", "newest": "Newest", "oldest": "Oldest"}[self.sort_mode])
        self.sort_btn.grid(row=0, column=1, rowspan=2, padx=(8, 8), pady=14, sticky="e")

        # Dark/light toggle (top-right corner)
        toggle_text = "☾" if self.appearance_mode == "light" else "☀"
        self.theme_toggle_btn = ctk.CTkButton(
            self.header_frame, text=toggle_text,
            width=36, height=30, corner_radius=15,
            font=("Georgia", 16, "bold"),
            fg_color="transparent", hover_color=self.colors["hover_soft"],
            text_color=self.colors["accent"],
            border_width=1, border_color=self.colors["border"],
            command=self._toggle_appearance,
        )
        self.theme_toggle_btn.grid(row=0, column=2, rowspan=2, padx=(0, 20), pady=14, sticky="e")

        # Themes bar (row 1) — built but hidden until a book is selected
        self._build_themes_bar()

        # Annotation area (row 2)
        self.ann_scroll = ctk.CTkScrollableFrame(
            self.main, fg_color=self.colors["bg"],
            scrollbar_button_color=self.colors["border"]
        )
        self.ann_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=12)
        self.ann_scroll.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self.ann_scroll,
            text="No annotations yet.\nSpeak or type your first note below.",
            font=FONTS["body"], text_color=self.colors["text_light"]
        )
        self._empty_label.grid(row=0, column=0, pady=60)

        # Bottom input bar (row 3)
        self._build_input_bar()

    def _build_themes_bar(self):
        self.themes_bar = ctk.CTkFrame(
            self.main, fg_color=self.colors["sidebar_bg"],
            border_width=1, border_color=self.colors["border"],
            corner_radius=0, height=44,
        )
        # Not gridded until a book is selected

    def _build_input_bar(self):
        self.input_bar = ctk.CTkFrame(
            self.main, fg_color=self.colors["card_bg"], corner_radius=12,
            border_width=1, border_color=self.colors["border"]
        )
        self.input_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.input_bar.grid_columnconfigure(1, weight=1)

        self.mic_btn = ctk.CTkButton(
            self.input_bar, text="🎤", width=52, height=52,
            font=FONTS["big_mic"],
            fg_color=self.colors["mic_idle"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            corner_radius=26,
            command=self._toggle_voice
        )
        self.mic_btn.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=12)

        self.status_label = ctk.CTkLabel(
            self.input_bar,
            text="Click 🎤 to record  ·  or type below:  page 42, your note",
            font=FONTS["small"], text_color=self.colors["text_light"], anchor="w"
        )
        self.status_label.grid(row=0, column=1, sticky="ew", padx=4, pady=(10, 2))

        manual_frame = ctk.CTkFrame(self.input_bar, fg_color="transparent")
        manual_frame.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 10))
        manual_frame.grid_columnconfigure(0, weight=1)

        self.manual_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text='e.g. "Page 47, theme patriarchy, symbolism of green light"',
            font=FONTS["body"], height=36,
            fg_color=self.colors["bg"], border_color=self.colors["border"],
            text_color=self.colors["text_dark"]
        )
        self.manual_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.manual_entry.bind("<Return>", lambda e: self._submit_manual())

        ctk.CTkButton(
            manual_frame, text="Save", width=70, height=36,
            font=FONTS["small"],
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            command=self._submit_manual
        ).grid(row=0, column=1)

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
                self.book_list_frame, text="No books yet.\nAdd one above.",
                font=FONTS["small"], text_color=self.colors["text_light"]
            ).pack(pady=20)

    def _render_book_row(self, book_id, title, cover_path):
        is_selected = (book_id == self.selected_book_id)
        row_bg = self.colors["secondary"] if is_selected else "transparent"
        txt_color = self.colors["on_secondary"] if is_selected else self.colors["text_dark"]
        hover = self.colors["hover_soft"] if not is_selected else self.colors["secondary"]

        row = ctk.CTkFrame(
            self.book_list_frame, fg_color=row_bg, corner_radius=8
        )
        row.pack(fill="x", pady=2, padx=2)
        row.grid_columnconfigure(1, weight=1)

        thumb = covers.load_thumbnail(cover_path, size=28) if cover_path else None
        if thumb is not None:
            label_text = f"  {title[:24]}{'…' if len(title) > 24 else ''}"
            btn = ctk.CTkButton(
                row, text=label_text, image=thumb, compound="left",
                font=FONTS["small"], anchor="w",
                fg_color="transparent", hover_color=hover,
                text_color=txt_color,
                height=40, corner_radius=8,
                command=lambda bid=book_id, t=title: self._select_book(bid, t)
            )
        else:
            btn = ctk.CTkButton(
                row, text=f"📖  {title[:26]}{'…' if len(title) > 26 else ''}",
                font=FONTS["small"], anchor="w",
                fg_color="transparent", hover_color=hover,
                text_color=txt_color,
                height=40, corner_radius=8,
                command=lambda bid=book_id, t=title: self._select_book(bid, t)
            )
        btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=2)

        # Hover-revealed actions: cover-edit + delete (small, low-visual-weight)
        cover_btn = ctk.CTkButton(
            row, text="🖼", width=24, height=24,
            font=("Georgia", 11),
            fg_color="transparent", hover_color=hover,
            text_color=txt_color,
            command=lambda bid=book_id: self._set_cover(bid)
        )
        cover_btn.grid(row=0, column=2, padx=(0, 2))

        del_btn = ctk.CTkButton(
            row, text="×", width=24, height=24,
            font=("Georgia", 14, "bold"),
            fg_color="transparent", hover_color=self.colors["danger_soft"],
            text_color=txt_color,
            command=lambda bid=book_id: self._delete_book(bid)
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

    # ── Themes Bar (compact single-row design) ─────────────────────────────────

    def _refresh_themes_bar(self):
        for w in self.themes_bar.winfo_children():
            w.destroy()

        if not self.selected_book_id:
            self.themes_bar.grid_remove()
            return

        self.themes_bar.grid(row=1, column=0, sticky="ew")

        themes = get_themes_for_book(self.selected_book_id)
        theme_names = [t["name"] for t in themes]
        self._theme_name_to_id = {t["name"]: t["id"] for t in themes}

        ctk.CTkLabel(
            self.themes_bar, text="THEMES",
            font=FONTS["label"], text_color=self.colors["text_light"]
        ).pack(side="left", padx=(16, 8), pady=10)

        # Filter dropdown (replaces the row of chips)
        filter_values = [ALL_FILTER, UNCLASSIFIED] + theme_names
        current = self._current_filter_label(themes)
        is_filtered = self.theme_filter is not None
        self._filter_menu = ctk.CTkOptionMenu(
            self.themes_bar,
            values=filter_values,
            command=self._on_filter_select,
            font=FONTS["small"],
            dropdown_font=FONTS["small"],
            fg_color=self.colors["secondary"] if is_filtered else self.colors["accent"],
            text_color=self.colors["on_secondary"] if is_filtered else self.colors["on_accent"],
            button_color=self.colors["accent_hover"],
            button_hover_color=self.colors["accent_hover"],
            dropdown_fg_color=self.colors["card_bg"],
            dropdown_text_color=self.colors["text_dark"],
            dropdown_hover_color=self.colors["hover_soft"],
            width=160, height=28, corner_radius=14,
        )
        self._filter_menu.set(current)
        self._filter_menu.pack(side="left", padx=(0, 8), pady=8)

        # Inline "+ new theme" entry
        self._theme_entry = ctk.CTkEntry(
            self.themes_bar, placeholder_text="New theme…",
            font=FONTS["small"], height=28, width=140,
            fg_color=self.colors["card_bg"], border_color=self.colors["border"],
            text_color=self.colors["text_dark"]
        )
        self._theme_entry.pack(side="left", padx=(0, 4), pady=8)
        self._theme_entry.bind("<Return>", lambda e: self._add_theme())

        ctk.CTkButton(
            self.themes_bar, text="+", width=28, height=28,
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"],
            font=("Georgia", 16, "bold"),
            command=self._add_theme
        ).pack(side="left", pady=8)

        # Manage themes (opens modal for delete / overflow)
        ctk.CTkButton(
            self.themes_bar, text="Manage…",
            width=80, height=28, corner_radius=14,
            font=FONTS["small"],
            fg_color="transparent", hover_color=self.colors["hover_soft"],
            text_color=self.colors["text_mid"],
            border_width=1, border_color=self.colors["border"],
            command=self._open_manage_themes
        ).pack(side="right", padx=(8, 16), pady=8)

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
                color=self.colors["danger"], duration=3000
            )

    def _open_manage_themes(self):
        themes = get_themes_for_book(self.selected_book_id)

        modal = ctk.CTkToplevel(self)
        modal.title("Manage themes")
        modal.geometry("360x420")
        modal.configure(fg_color=self.colors["bg"])
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal, text=f"Themes for “{self.selected_book_title}”",
            font=FONTS["head"], text_color=self.colors["text_dark"]
        ).pack(pady=(16, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            modal,
            text="Deleting a theme keeps its annotations — they become Unclassified.",
            font=FONTS["small"], text_color=self.colors["text_light"],
            wraplength=320, justify="left",
        ).pack(pady=(0, 12), padx=20, anchor="w")

        scroll = ctk.CTkScrollableFrame(
            modal, fg_color=self.colors["card_bg"],
            scrollbar_button_color=self.colors["border"],
            border_width=1, border_color=self.colors["border"],
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        scroll.grid_columnconfigure(0, weight=1)

        if not themes:
            ctk.CTkLabel(
                scroll, text="No themes yet.",
                font=FONTS["body"], text_color=self.colors["text_light"]
            ).grid(row=0, column=0, pady=20)

        for i, t in enumerate(themes):
            ctk.CTkLabel(
                scroll, text=t["name"], anchor="w",
                font=FONTS["body"], text_color=self.colors["text_dark"]
            ).grid(row=i, column=0, sticky="ew", padx=12, pady=6)

            ctk.CTkButton(
                scroll, text="Delete", width=70, height=26,
                font=FONTS["small"],
                fg_color="transparent", hover_color=self.colors["danger_soft"],
                text_color=self.colors["danger"],
                border_width=1, border_color=self.colors["danger"],
                corner_radius=6,
                command=lambda tid=t["id"], tn=t["name"], m=modal: self._delete_theme_from_modal(tid, tn, m)
            ).grid(row=i, column=1, padx=(0, 12), pady=6)

        ctk.CTkButton(
            modal, text="Done", height=32, corner_radius=8,
            fg_color=self.colors["accent"], hover_color=self.colors["accent_hover"],
            text_color=self.colors["on_accent"], font=FONTS["small"],
            command=modal.destroy,
        ).pack(pady=(0, 16), padx=20, fill="x")

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

    def _load_annotations(self):
        self._clear_annotations()
        if not self.selected_book_id:
            return

        themes = get_themes_for_book(self.selected_book_id)
        anns = get_annotations_for_book(
            self.selected_book_id,
            sort_by=self.sort_mode,
            theme_filter=self.theme_filter
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
            self._empty_label = ctk.CTkLabel(
                self.ann_scroll,
                text="No annotations yet.\nSpeak or type your first note below.",
                font=FONTS["body"], text_color=self.colors["text_light"]
            )
            self._empty_label.grid(row=0, column=0, pady=60)
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
        frame = ctk.CTkFrame(self.ann_scroll, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=(14, 4), padx=4)

        ctk.CTkLabel(
            frame,
            text=f"  Page {page}  ",
            font=("Georgia", 11, "bold"),
            text_color=self.colors["text_dark"],
            fg_color=self.colors["page_badge"],
            corner_radius=10,
            width=70, height=22
        ).pack(side="left")

        line = ctk.CTkFrame(frame, height=1, fg_color=self.colors["border"])
        line.pack(side="left", fill="x", expand=True, padx=8, pady=11)

    def _render_annotation_card(self, row, ann, themes):
        card = ctk.CTkFrame(
            self.ann_scroll, fg_color=self.colors["card_bg"],
            corner_radius=10, border_width=1, border_color=self.colors["border"]
        )
        card.grid(row=row, column=0, sticky="ew", pady=4, padx=4)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=ann["note"],
            font=FONTS["body"], text_color=self.colors["text_dark"],
            anchor="w", wraplength=600, justify="left"
        ).grid(row=0, column=0, padx=16, pady=(12, 8), sticky="ew")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)

        ts = ann["created_at"].strftime("%b %d, %I:%M %p") if ann["created_at"] else ""
        ctk.CTkLabel(
            footer, text=ts, font=FONTS["small"], text_color=self.colors["text_light"]
        ).grid(row=0, column=0, sticky="w")

        # Theme reassignment dropdown
        theme_options = [UNCLASSIFIED] + [t["name"] for t in themes]
        theme_map = {t["name"]: t["id"] for t in themes}
        current_theme = ann["theme_name"] if ann["theme_name"] else UNCLASSIFIED
        is_tagged = bool(ann["theme_name"])

        theme_menu = ctk.CTkOptionMenu(
            footer,
            values=theme_options,
            command=lambda val, aid=ann["id"]: self._on_reassign_theme(aid, val, theme_map),
            width=140, height=24, font=FONTS["small"],
            fg_color=self.colors["secondary"] if is_tagged else self.colors["border"],
            text_color=self.colors["on_secondary"] if is_tagged else self.colors["text_mid"],
            button_color=self.colors["accent_hover"] if is_tagged else self.colors["text_light"],
            button_hover_color=self.colors["accent_hover"],
            dropdown_font=FONTS["small"],
            dropdown_fg_color=self.colors["card_bg"],
            dropdown_text_color=self.colors["text_dark"],
            dropdown_hover_color=self.colors["hover_soft"],
        )
        theme_menu.set(current_theme)
        theme_menu.grid(row=0, column=1, padx=(4, 6))

        ctk.CTkButton(
            footer, text="Delete", width=56, height=22,
            font=("Georgia", 10),
            fg_color="transparent", hover_color=self.colors["danger_soft"],
            text_color=self.colors["danger"], border_width=1,
            border_color=self.colors["danger"], corner_radius=4,
            command=lambda aid=ann["id"]: self._delete_annotation(aid)
        ).grid(row=0, column=2)

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
                    None
                )
                if match:
                    theme_id = match["id"]
                else:
                    self._set_status(
                        f'⚠ Theme "{parsed_theme}" not found — saved as Unclassified. Add it in the themes bar first.',
                        color=self.colors["danger"], duration=5000
                    )
            self._save_annotation(result["page"], result["note"], theme_id)
        else:
            self._set_status(
                f'⚠ Couldn\'t find a page number in: "{transcript[:60]}"  '
                '· Try: "Page 42, your note"',
                color=self.colors["danger"], duration=5000
            )

    def _save_annotation(self, page: int, note: str, theme_id=None):
        if not self.selected_book_id:
            self._set_status("⚠ Please select a book first.", color=self.colors["danger"])
            return
        add_annotation(self.selected_book_id, page, note, theme_id=theme_id)
        self._load_annotations()
        self._set_status(
            f"✓ Saved — Page {page}: {note[:50]}{'…' if len(note) > 50 else ''}",
            color=self.colors["success"], duration=3000
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
            on_start=None
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
            text_color=color or self.colors["text_mid"]
        )
        if self._status_timer:
            self.after_cancel(self._status_timer)
            self._status_timer = None
        if duration:
            self._status_timer = self.after(
                duration,
                lambda: self.status_label.configure(
                    text="Click 🎤 to record  ·  or type below:  page 42, your note",
                    text_color=self.colors["text_light"]
                )
            )


def main():
    app = VocalAnnotateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

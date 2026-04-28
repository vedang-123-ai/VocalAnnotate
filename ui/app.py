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
)
from voice.parser import parse_annotation
from voice.recorder import VoiceRecorder

# ─── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg":          "#F5F0E8",
    "sidebar_bg":  "#EDE7D9",
    "card_bg":     "#FEFCF7",
    "accent":      "#2C4A7C",
    "accent_hover":"#1E3560",
    "text_dark":   "#1C1C1C",
    "text_mid":    "#555555",
    "text_light":  "#888888",
    "border":      "#D8D0C4",
    "success":     "#2E7D52",
    "danger":      "#C0392B",
    "mic_idle":    "#2C4A7C",
    "mic_active":  "#C0392B",
    "page_badge":  "#2C4A7C",
}

FONT_TITLE  = ("Georgia", 20, "bold")
FONT_HEAD   = ("Georgia", 15, "bold")
FONT_BODY   = ("Georgia", 13)
FONT_SMALL  = ("Georgia", 11)
FONT_MONO   = ("Courier", 12)
FONT_BIG_MIC= ("Georgia", 28)


class VocalAnnotateApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VocalAnnotate")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg"])

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
            fg_color=COLORS["sidebar_bg"],
            border_width=1, border_color=COLORS["border"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(3, weight=1)

        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=16, pady=(20, 4), sticky="ew")

        ctk.CTkLabel(
            title_frame, text="🎙 VocalAnnotate",
            font=("Georgia", 16, "bold"),
            text_color=COLORS["accent"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_frame, text="voice annotation companion",
            font=FONT_SMALL, text_color=COLORS["text_light"]
        ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["border"]).grid(
            row=1, column=0, sticky="ew", padx=12, pady=8
        )

        add_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        add_frame.grid(row=2, column=0, padx=12, pady=(0, 8), sticky="ew")
        add_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(add_frame, text="MY BOOKS", font=("Georgia", 10, "bold"),
                     text_color=COLORS["text_light"]).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.book_entry = ctk.CTkEntry(
            add_frame, placeholder_text="New book title...",
            font=FONT_SMALL, height=32,
            fg_color=COLORS["card_bg"], border_color=COLORS["border"],
            text_color=COLORS["text_dark"]
        )
        self.book_entry.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.book_entry.bind("<Return>", lambda e: self._add_book())

        ctk.CTkButton(
            add_frame, text="+", width=32, height=32,
            font=("Georgia", 18, "bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._add_book
        ).grid(row=1, column=1)

        self.book_list_frame = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=COLORS["border"]
        )
        self.book_list_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=4)

    def _build_main_panel(self):
        self.main = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main.grid_rowconfigure(2, weight=1)  # ann_scroll is row 2
        self.main.grid_columnconfigure(0, weight=1)

        # Header (row 0)
        self.header_frame = ctk.CTkFrame(
            self.main, fg_color=COLORS["card_bg"], corner_radius=0,
            border_width=1, border_color=COLORS["border"]
        )
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.book_title_label = ctk.CTkLabel(
            self.header_frame, text="Select or create a book to begin",
            font=FONT_TITLE, text_color=COLORS["text_dark"], anchor="w"
        )
        self.book_title_label.grid(row=0, column=0, padx=24, pady=(16, 2), sticky="w")

        self.annotation_count_label = ctk.CTkLabel(
            self.header_frame, text="",
            font=FONT_SMALL, text_color=COLORS["text_light"], anchor="w"
        )
        self.annotation_count_label.grid(row=1, column=0, padx=24, pady=(0, 14), sticky="w")

        # Sort segmented button (top-right of header)
        self.sort_btn = ctk.CTkSegmentedButton(
            self.header_frame,
            values=["Page", "Newest", "Oldest"],
            command=self._on_sort_change,
            font=FONT_SMALL,
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            height=30,
        )
        self.sort_btn.set("Page")
        self.sort_btn.grid(row=0, column=1, rowspan=2, padx=(8, 20), pady=14, sticky="e")

        # Themes bar (row 1) — built but hidden until a book is selected
        self._build_themes_bar()

        # Annotation area (row 2)
        self.ann_scroll = ctk.CTkScrollableFrame(
            self.main, fg_color=COLORS["bg"],
            scrollbar_button_color=COLORS["border"]
        )
        self.ann_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=12)
        self.ann_scroll.grid_columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self.ann_scroll,
            text="No annotations yet.\nSpeak or type your first note below.",
            font=FONT_BODY, text_color=COLORS["text_light"]
        )
        self._empty_label.grid(row=0, column=0, pady=60)

        # Bottom input bar (row 3)
        self._build_input_bar()

    def _build_themes_bar(self):
        self.themes_bar = ctk.CTkFrame(
            self.main, fg_color=COLORS["sidebar_bg"],
            border_width=1, border_color=COLORS["border"],
            corner_radius=0
        )
        # Not gridded until a book is selected

    def _build_input_bar(self):
        self.input_bar = ctk.CTkFrame(
            self.main, fg_color=COLORS["card_bg"], corner_radius=12,
            border_width=1, border_color=COLORS["border"]
        )
        self.input_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.input_bar.grid_columnconfigure(1, weight=1)

        self.mic_btn = ctk.CTkButton(
            self.input_bar, text="🎤", width=52, height=52,
            font=FONT_BIG_MIC,
            fg_color=COLORS["mic_idle"], hover_color=COLORS["accent_hover"],
            corner_radius=26,
            command=self._toggle_voice
        )
        self.mic_btn.grid(row=0, column=0, rowspan=2, padx=(14, 10), pady=12)

        self.status_label = ctk.CTkLabel(
            self.input_bar,
            text="Click 🎤 to record  ·  or type below:  page 42, your note",
            font=FONT_SMALL, text_color=COLORS["text_light"], anchor="w"
        )
        self.status_label.grid(row=0, column=1, sticky="ew", padx=4, pady=(10, 2))

        manual_frame = ctk.CTkFrame(self.input_bar, fg_color="transparent")
        manual_frame.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 10))
        manual_frame.grid_columnconfigure(0, weight=1)

        self.manual_entry = ctk.CTkEntry(
            manual_frame,
            placeholder_text='e.g. "Page 47, theme patriarchy, symbolism of green light"',
            font=FONT_BODY, height=36,
            fg_color=COLORS["bg"], border_color=COLORS["border"],
            text_color=COLORS["text_dark"]
        )
        self.manual_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.manual_entry.bind("<Return>", lambda e: self._submit_manual())

        ctk.CTkButton(
            manual_frame, text="Save", width=70, height=36,
            font=FONT_SMALL,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._submit_manual
        ).grid(row=0, column=1)

    # ── Book Logic ─────────────────────────────────────────────────────────────

    def _load_books(self):
        for widget in self.book_list_frame.winfo_children():
            widget.destroy()

        books = get_all_books()
        for b in books:
            self._render_book_row(b["id"], b["title"])

        if not books:
            ctk.CTkLabel(
                self.book_list_frame, text="No books yet.\nAdd one above.",
                font=FONT_SMALL, text_color=COLORS["text_light"]
            ).pack(pady=20)

    def _render_book_row(self, book_id, title):
        row = ctk.CTkFrame(
            self.book_list_frame, fg_color="transparent", corner_radius=6
        )
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=1)

        is_selected = (book_id == self.selected_book_id)
        btn_color = COLORS["accent"] if is_selected else "transparent"
        txt_color = "#FFFFFF" if is_selected else COLORS["text_dark"]

        btn = ctk.CTkButton(
            row, text=f"📖  {title[:28]}{'…' if len(title) > 28 else ''}",
            font=FONT_SMALL, anchor="w",
            fg_color=btn_color, hover_color=COLORS["accent"],
            text_color=txt_color,
            height=36, corner_radius=6,
            command=lambda bid=book_id, t=title: self._select_book(bid, t)
        )
        btn.grid(row=0, column=0, sticky="ew")

        del_btn = ctk.CTkButton(
            row, text="×", width=28, height=28,
            font=("Georgia", 14, "bold"),
            fg_color="transparent", hover_color="#FFDDDD",
            text_color=COLORS["text_light"],
            command=lambda bid=book_id: self._delete_book(bid)
        )
        del_btn.grid(row=0, column=1, padx=(2, 0))

    def _add_book(self):
        title = self.book_entry.get().strip()
        if not title:
            return
        book = add_book(title)
        self.book_entry.delete(0, "end")
        self._load_books()
        self._select_book(book.id, book.title)

    def _delete_book(self, book_id):
        delete_book(book_id)
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

    # ── Themes Bar ─────────────────────────────────────────────────────────────

    def _refresh_themes_bar(self):
        for w in self.themes_bar.winfo_children():
            w.destroy()

        if not self.selected_book_id:
            self.themes_bar.grid_remove()
            return

        self.themes_bar.grid(row=1, column=0, sticky="ew")

        themes = get_themes_for_book(self.selected_book_id)

        ctk.CTkLabel(
            self.themes_bar, text="THEMES",
            font=("Georgia", 10, "bold"), text_color=COLORS["text_light"]
        ).pack(side="left", padx=(14, 6), pady=10)

        # "All" chip
        is_all = self.theme_filter is None
        ctk.CTkButton(
            self.themes_bar, text="All",
            fg_color=COLORS["accent"] if is_all else COLORS["border"],
            text_color="#FFFFFF" if is_all else COLORS["text_dark"],
            hover_color=COLORS["accent_hover"],
            height=26, width=44, corner_radius=13, font=FONT_SMALL,
            command=lambda: self._set_theme_filter(None)
        ).pack(side="left", padx=3, pady=8)

        # "Unclassified" chip
        is_unclassified = self.theme_filter == "unclassified"
        ctk.CTkButton(
            self.themes_bar, text="Unclassified",
            fg_color=COLORS["accent"] if is_unclassified else COLORS["border"],
            text_color="#FFFFFF" if is_unclassified else COLORS["text_dark"],
            hover_color=COLORS["accent_hover"],
            height=26, corner_radius=13, font=FONT_SMALL,
            command=lambda: self._set_theme_filter("unclassified")
        ).pack(side="left", padx=3, pady=8)

        # One chip per theme
        for t in themes:
            is_active = (self.theme_filter == t["id"])
            chip = ctk.CTkFrame(self.themes_bar, fg_color="transparent")
            chip.pack(side="left", padx=2, pady=8)

            ctk.CTkButton(
                chip, text=t["name"],
                fg_color=COLORS["accent"] if is_active else COLORS["border"],
                text_color="#FFFFFF" if is_active else COLORS["text_dark"],
                hover_color=COLORS["accent_hover"],
                height=26, corner_radius=13, font=FONT_SMALL,
                command=lambda tid=t["id"]: self._set_theme_filter(tid)
            ).pack(side="left")

            ctk.CTkButton(
                chip, text="×", width=20, height=26,
                fg_color="transparent", hover_color="#FFDDDD",
                text_color=COLORS["text_light"], font=("Georgia", 13),
                command=lambda tid=t["id"], tn=t["name"]: self._delete_theme_ui(tid, tn)
            ).pack(side="left")

        # Separator
        ctk.CTkFrame(self.themes_bar, width=1, fg_color=COLORS["border"]).pack(
            side="left", fill="y", padx=10, pady=6
        )

        # Add-theme entry + button
        self._theme_entry = ctk.CTkEntry(
            self.themes_bar, placeholder_text="New theme...",
            font=FONT_SMALL, height=28, width=110,
            fg_color=COLORS["card_bg"], border_color=COLORS["border"],
            text_color=COLORS["text_dark"]
        )
        self._theme_entry.pack(side="left", padx=(0, 4), pady=8)
        self._theme_entry.bind("<Return>", lambda e: self._add_theme())

        ctk.CTkButton(
            self.themes_bar, text="+", width=28, height=28,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=("Georgia", 16, "bold"),
            command=self._add_theme
        ).pack(side="left", pady=8)

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
        except Exception:
            self._set_status(
                f'⚠ Theme "{name}" already exists for this book.',
                color=COLORS["danger"], duration=3000
            )

    def _delete_theme_ui(self, theme_id, theme_name):
        confirmed = tkinter.messagebox.askyesno(
            "Delete Theme",
            f'Delete theme "{theme_name}"?\n\nAnnotations tagged with this theme will become Unclassified.'
        )
        if confirmed:
            delete_theme(theme_id)
            if self.theme_filter == theme_id:
                self.theme_filter = None
            self._refresh_themes_bar()
            self._load_annotations()

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
                font=FONT_BODY, text_color=COLORS["text_light"]
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
        frame.grid(row=row, column=0, sticky="ew", pady=(12, 2), padx=4)

        ctk.CTkLabel(
            frame,
            text=f"  Page {page}  ",
            font=("Georgia", 11, "bold"),
            text_color="#FFFFFF",
            fg_color=COLORS["page_badge"],
            corner_radius=10,
            width=70, height=22
        ).pack(side="left")

        line = ctk.CTkFrame(frame, height=1, fg_color=COLORS["border"])
        line.pack(side="left", fill="x", expand=True, padx=8, pady=11)

    def _render_annotation_card(self, row, ann, themes):
        card = ctk.CTkFrame(
            self.ann_scroll, fg_color=COLORS["card_bg"],
            corner_radius=8, border_width=1, border_color=COLORS["border"]
        )
        card.grid(row=row, column=0, sticky="ew", pady=3, padx=4)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text=ann["note"],
            font=FONT_BODY, text_color=COLORS["text_dark"],
            anchor="w", wraplength=600, justify="left"
        ).grid(row=0, column=0, padx=14, pady=(10, 8), sticky="ew")

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        footer.grid_columnconfigure(0, weight=1)

        ts = ann["created_at"].strftime("%b %d, %I:%M %p") if ann["created_at"] else ""
        ctk.CTkLabel(
            footer, text=ts, font=FONT_SMALL, text_color=COLORS["text_light"]
        ).grid(row=0, column=0, sticky="w")

        # Theme reassignment dropdown
        theme_options = ["Unclassified"] + [t["name"] for t in themes]
        theme_map = {t["name"]: t["id"] for t in themes}
        current_theme = ann["theme_name"] if ann["theme_name"] else "Unclassified"

        theme_menu = ctk.CTkOptionMenu(
            footer,
            values=theme_options,
            command=lambda val, aid=ann["id"]: self._on_reassign_theme(aid, val, theme_map),
            width=140, height=24, font=FONT_SMALL,
            fg_color=COLORS["accent"] if ann["theme_name"] else COLORS["border"],
            text_color="#FFFFFF" if ann["theme_name"] else COLORS["text_mid"],
            button_color=COLORS["accent_hover"] if ann["theme_name"] else COLORS["text_light"],
            button_hover_color=COLORS["accent_hover"],
            dropdown_font=FONT_SMALL,
        )
        theme_menu.set(current_theme)
        theme_menu.grid(row=0, column=1, padx=(4, 6))

        ctk.CTkButton(
            footer, text="Delete", width=56, height=22,
            font=("Georgia", 10),
            fg_color="transparent", hover_color="#FFEEEE",
            text_color=COLORS["danger"], border_width=1,
            border_color=COLORS["danger"], corner_radius=4,
            command=lambda aid=ann["id"]: self._delete_annotation(aid)
        ).grid(row=0, column=2)

    def _on_reassign_theme(self, ann_id, value, theme_map):
        theme_id = theme_map.get(value) if value != "Unclassified" else None
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
                        color=COLORS["danger"], duration=5000
                    )
            self._save_annotation(result["page"], result["note"], theme_id)
        else:
            self._set_status(
                f'⚠ Couldn\'t find a page number in: "{transcript[:60]}"  '
                '· Try: "Page 42, your note"',
                color=COLORS["danger"], duration=5000
            )

    def _save_annotation(self, page: int, note: str, theme_id=None):
        if not self.selected_book_id:
            self._set_status("⚠ Please select a book first.", color=COLORS["danger"])
            return
        add_annotation(self.selected_book_id, page, note, theme_id=theme_id)
        self._load_annotations()
        self._set_status(
            f"✓ Saved — Page {page}: {note[:50]}{'…' if len(note) > 50 else ''}",
            color=COLORS["success"], duration=3000
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
            self._set_status("⚠ Please select a book before recording.", color=COLORS["danger"])
            return
        self._start_recording()

    def _start_recording(self):
        self.mic_btn.configure(fg_color=COLORS["mic_active"], text="⏹")
        self._set_status("🔴 Listening… speak your annotation now", color=COLORS["mic_active"])

        self.recorder.record_and_transcribe(
            on_result=self._on_voice_result,
            on_error=self._on_voice_error,
            on_start=None
        )

    def _on_voice_result(self, transcript: str):
        self.after(0, lambda: self._handle_voice_result(transcript))

    def _handle_voice_result(self, transcript: str):
        self.mic_btn.configure(fg_color=COLORS["mic_idle"], text="🎤")
        self._set_status(f'Heard: "{transcript}"', color=COLORS["text_mid"], duration=2000)
        self.after(300, lambda: self._process_transcript(transcript))

    def _on_voice_error(self, message: str):
        self.after(0, lambda: self._handle_voice_error(message))

    def _handle_voice_error(self, message: str):
        self.mic_btn.configure(fg_color=COLORS["mic_idle"], text="🎤")
        self._set_status(f"⚠ {message}", color=COLORS["danger"], duration=4000)

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
            text_color=color or COLORS["text_mid"]
        )
        if self._status_timer:
            self.after_cancel(self._status_timer)
            self._status_timer = None
        if duration:
            self._status_timer = self.after(
                duration,
                lambda: self.status_label.configure(
                    text="Click 🎤 to record  ·  or type below:  page 42, your note",
                    text_color=COLORS["text_light"]
                )
            )


def main():
    app = VocalAnnotateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

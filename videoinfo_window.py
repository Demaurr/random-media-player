import os
from pprint import pprint
import tkinter as tk
from typing import Optional

from custom_dialogbox import MultiFieldDialog
from custom_messagebox import showwarning, showinfo, showerror
from static_methods import convert_bytes


class VideoInfoWindow:
    """
    Info-style window that displays notes, description, categories,
    associations and annotations for a single video file.

    Usage:
        win = VideoInfoWindow(parent, file_path,
                              notes_manager=nm,
                              description_manager=dm,
                              category_manager=cm,
                              associations_manager=am,
                              annotations_manager=annm,
                              fingerprint_manager=fm)
        win.show()   # modal; returns when closed
    """

    def __init__(
        self,
        parent: tk.Toplevel,
        file_path: str,
        *,
        notes_manager=None,
        description_manager=None,
        category_manager=None,
        associations_manager=None,
        annotations_manager=None,
        fingerprint_manager=None,
        stats_manager=None,
        width: int = 420,
        max_height: int = 1000,
    ):
        self.parent = parent
        self.file_path = file_path
        self.notes_manager = notes_manager
        self.description_manager = description_manager
        self.category_manager = category_manager
        self.associations_manager = associations_manager
        self.annotations_manager = annotations_manager
        self.stats_manager = stats_manager

        # prefer explicitly passed fingerprint manager, fallback to parent's if available
        self.fingerprint_manager = fingerprint_manager or getattr(parent, "fingerprint_manager", None)

        self.width = width
        self.max_height = max_height

        self.dialog: Optional[MultiFieldDialog] = None

    def _gather(self):
        try:
            via_fp = self._gather_via_fingerprint()
            if via_fp:
                return via_fp
        except Exception as e:
            print(f"Error gathering via fingerprint for {self.file_path}: {e}")
            pass

        try:
            note = {}
            if self.notes_manager:
                note = self.notes_manager.get_note(self.file_path) or {}
            note_text = note.get("note", "") if isinstance(note, dict) else ""
        except Exception:
            note_text = ""

        try:
            desc = ""
            if self.description_manager:
                desc = self.description_manager.get_description(self.file_path) or ""
        except Exception:
            desc = ""

        try:
            cats = []
            if self.category_manager:
                cats = self.category_manager.get_categories_of_files(self.file_path) or []
        except Exception:
            cats = []

        try:
            assocs = []
            if self.associations_manager:
                assocs = self.associations_manager.get_associations(self.file_path) or []
        except Exception:
            assocs = []

        # Annotations
        try:
            annotations = []
            if self.annotations_manager:
                annotations = self.annotations_manager.get_annotations_for_file(self.file_path) or []
        except Exception:
            annotations = []

        # Provide the extended fingerprint-related keys with sensible "unknown"/empty defaults
        return {
            "note_text": note_text,
            "description": desc,
            "categories": cats,
            "associations": assocs,
            "annotations": annotations,
            "fingerprint": "unknown",
            "paths": [],
            "duplicates": [],
            "available_duplicates": [],
            "is_duplicate": False,
            "total_paths": 0,
            "available_paths_count": 0,
            "missing_paths_count": 0,
            "stats": {},
            "snippets": [],
            "watch_history": [],
        }

    def _gather_via_fingerprint(self):
        """
        Gather info for the current file via `MediaFingerprintManager.get_fingerprint_info`.
        Uses managers from self (if provided) or falls back to the parent attributes.
        Returns a dict matching `_gather()`'s output keys, or None on failure.
        """
        if not self.fingerprint_manager:
            return None

        # Resolve fingerprint hash (prefer parent's cached fingerprint)
        index_hash = None
        try:
            index_hash = getattr(self.parent, "current_fingerprint", None)
        except Exception:
            index_hash = None

        if not index_hash:
            try:
                index_hash = self.fingerprint_manager.get_index_hash_by_path(self.file_path)
            except Exception:
                index_hash = None

        if not index_hash:
            return None

        # Resolve manager objects (prefer ones passed to this window, else parent attributes)
        stats_mgr = self.stats_manager or getattr(self.parent, "stats_manager", None)
        snippets_mgr = getattr(self.parent, "snippets_manager", None)
        notes_mgr = self.notes_manager or getattr(self.parent, "notes_manager", None)
        category_mgr = self.category_manager or getattr(self.parent, "category_manager", None)
        # watch_mgr = getattr(self, "watch_history_manager", None) or getattr(self.parent, "watch_history_logger", None) or getattr(self.parent, "watch_history_manager", None)
        assoc_mgr = self.associations_manager or getattr(self.parent, "associations_manager", None)
        ann_mgr = self.annotations_manager or getattr(self.parent, "annotations_manager", None)

        try:
            fp_info = self.fingerprint_manager.get_fingerprint_info(
                index_hash,
                stats_mgr,
                snippets_manager=snippets_mgr,
                notes_manager=notes_mgr,
                category_manager=category_mgr,
                watch_history_manager=None,
                association_manager=assoc_mgr,
                annotations_manager=ann_mgr,
                include_all=True,
            )
        except Exception as e:
            print(f"Error gathering fingerprint info for {self.file_path}: {e}")
            return None

        if not fp_info or not isinstance(fp_info, dict):
            return None

        # Normalize output to the same  as _gather()
        try:
            description = fp_info.get("description") or ""
            if not description and isinstance(fp_info.get("fingerprint"), dict):
                description = fp_info["fingerprint"].get("description", "") or ""
            if not description:
                description = self.description_manager.get_description(self.file_path) if self.description_manager else ""

            categories = fp_info.get("categories") or fp_info.get("category") or []
            associations = fp_info.get("associations") or fp_info.get("assocs") or []
            annotations = fp_info.get("annotations") or []

            # notes normalization
            note_text = ""
            notes_raw = fp_info.get("notes") or fp_info.get("note") or []
            if isinstance(notes_raw, str):
                note_text = notes_raw
            elif isinstance(notes_raw, dict):
                note_text = notes_raw.get("note", "") or ""
            elif isinstance(notes_raw, list) and notes_raw:
                first = notes_raw[0]
                if isinstance(first, dict):
                    note_text = first.get("note", "") or ""
                elif isinstance(first, str):
                    note_text = first

            fingerprint = fp_info.get("fingerprint") or {}
            paths = fp_info.get("paths") or []
            duplicates = fp_info.get("duplicates") or []
            available_duplicates = fp_info.get("available_duplicates") or []
            is_duplicate = bool(fp_info.get("is_duplicate", False))
            total_paths = int(fp_info.get("total_paths", len(duplicates) if duplicates else len(paths) if paths else 0))
            available_paths_count = int(fp_info.get("available_paths_count", 0))
            missing_paths_count = int(fp_info.get("missing_paths_count", max(0, total_paths - available_paths_count)))
            stats = fp_info.get("stats") or {}
            snippets = fp_info.get("snippets") or []
            watch_history = fp_info.get("watch_history") or []

            return {
                "note_text": note_text,
                "description": description,
                "categories": categories,
                "associations": associations,
                "annotations": annotations,
                "fingerprint": fingerprint,
                "paths": paths,
                "duplicates": duplicates,
                "available_duplicates": available_duplicates,
                "is_duplicate": is_duplicate,
                "total_paths": total_paths,
                "available_paths_count": available_paths_count,
                "missing_paths_count": missing_paths_count,
                "stats": stats,
                "snippets": snippets,
                "watch_history": watch_history,
            }
        except Exception as e:
            print(f"Error normalizing fingerprint info for {self.file_path}: {e}")
            return None

    def _build_dialog(self):
        info = self._gather()
        # pprint(info)

        parent_h = self.parent.winfo_height() if self.parent.winfo_exists() else 600
        dlg_height = min(self.max_height, max(400, parent_h - 20))

        dialog = MultiFieldDialog(self.parent, title="Video Info", window_width=self.width, window_height=dlg_height, window_position="parent_right")
        dialog.window_height = dlg_height  # for positioning helper

        index_hash = None
        try:
            index_hash = getattr(self.parent, "current_fingerprint", None)
        except Exception:
            index_hash = None

        if not index_hash and self.fingerprint_manager:
            try:
                index_hash = self.fingerprint_manager.get_index_hash_by_path(self.file_path)
            except Exception:
                index_hash = None

        hash_text = index_hash if index_hash else "(not indexed)"
        dialog.add_info(f"Index hash: {hash_text}", fg=dialog.theme["muted"], font_size=8, italic=True, align="center")

        fp = info.get("fingerprint") or {}
        paths = info.get("paths") or []
        duplicates = info.get("duplicates") or []
        stats = info.get("stats") or {}
        snippets = info.get("snippets") or []
        watch_history = info.get("watch_history") or []

        # Compact summary row: name / duration / partial hash
        try:
            fp_duration = fp.get("duration") if isinstance(fp, dict) else ""
            fp_partial = fp.get("partial_hash") if isinstance(fp, dict) else ""
        except Exception:
            fp_duration = fp_partial = ""

        if fp_duration or fp_partial:
            summary_parts = []
            if fp_duration:
                summary_parts.append(f"Duration: {fp_duration}")
            if fp_partial:
                summary_parts.append(f"Partial: {fp_partial}")
            dialog.add_info(" | ".join(summary_parts), fg=dialog.theme["muted"], font_size=9, italic=False, align="left")
        else:
            dialog.add_info("Fingerprint details: (none)", fg="#AAAAAA", font_size=9, italic=True, align="left")

        dialog.add_readonly_field("path", "Path", self.file_path, field_font_size=9, input_padx=4, input_pady=2)

        try:
            size_bytes = None
            if self.fingerprint_manager:
                size_bytes = self.fingerprint_manager.get_size_by_path(self.file_path)
            if size_bytes is None:
                size_bytes = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else None
            size_text = convert_bytes(size_bytes) if size_bytes is not None else "Unknown size"
        except Exception:
            size_text = "Unknown size"

        dialog.add_info(f"Size: {size_text}", fg="#9FB86E", font_size=9, italic=False, align="right")

        cats = info["categories"] or []
        parent = dialog._get_active_container()
        cat_frame = tk.Frame(parent, bg=dialog.main_bg)
        cat_frame.pack(fill="x", pady=(4, 6))

        label = tk.Label(
            cat_frame,
            text="Categories:" if not cats else "",
            fg=dialog.theme["muted"],
            bg=dialog.main_bg,
            font=("Segoe UI", 10),
            anchor="w"
        )
        label.pack(side="left", padx=(0, 8))

        if cats:
            for c in sorted(cats):
                badge = tk.Label(
                    cat_frame,
                    text=c,
                    fg=dialog.theme["accent"],
                    bg=dialog.theme["section_bg"],
                    font=("Segoe UI", 10, "bold"),
                    padx=8,
                    pady=2
                )
                badge.pack(side="left", padx=(0, 6))
        else:
            none_lbl = tk.Label(
                cat_frame,
                text="(none)",
                fg="#AAAAAA",
                bg=dialog.main_bg,
                font=("Segoe UI", 10, "italic")
            )
            none_lbl.pack(side="left")

        # Description: editable smart text (double-click to edit)
        desc_text = info["description"] or ""

        def _on_save_description(new_text):
            try:
                # determine size again (use fingerprint manager preferred)
                size_val = None
                if self.fingerprint_manager:
                    try:
                        size_val = self.fingerprint_manager.get_size_by_path(self.file_path)
                    except Exception:
                        size_val = None
                if size_val is None:
                    try:
                        size_val = os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0
                    except Exception:
                        size_val = 0

                if not self.description_manager:
                    showwarning(self.parent, "No Description Manager", "Description manager not available; cannot save.")
                    return

                # persist via description_manager using path, size and text
                self.description_manager.set_description(self.file_path, size_val or 0, new_text)

                # visual feedback
                try:
                    if hasattr(self.parent, "show_marquee"):
                        self.parent.show_marquee("Description saved")
                    else:
                        showinfo(self.parent, "Saved", "Description updated.")
                except Exception:
                    pass

            except Exception as e:
                showerror(self.parent, "Save Error", f"Could not save description:\n{e}")

        dialog.add_smart_text("description", "Description", default=desc_text, multiline=True, on_save=_on_save_description, display_font=("Segoe UI", 11, "italic"))

        # small spacer
        dialog.add_info(" ", fg="#000000", font_size=3, italic=False, align="left")

        # Notes block
        if info["note_text"]:
            # dialog.add_info("Notes", fg="#FFFFFF", font_size=11, italic=False, align="left")
            dialog.add_readonly_field("notes", "Notes", info["note_text"], field_font_size=10, input_padx=6, input_pady=6)
        else:
            dialog.add_info("Notes", fg="#FFFFFF", font_size=11, italic=False, align="left")
            dialog.add_info("(no notes)", fg="#AAAAAA", font_size=10, italic=True, align="left")

        # Associations (table) - compact; rows are dicts keyed by column ids
        if info["associations"]:
            rows = []
            for a in info["associations"]:
                atype = a.get("association_type") or ""
                role = a.get("role", "")
                tgt = ""
                if isinstance(a.get("target"), dict):
                    tgt = a["target"].get("file", "") or ""
                else:
                    tgt = a.get("target_file", "") or a.get("target", "")
                rows.append({
                    "type": atype,
                    "role": role,
                    "target": os.path.basename(tgt) or tgt
                })
            cols = [("type", "Type", 80), ("role", "Role", 60), ("target", "Target", 260)]
            dialog.add_section(f"Associations ({len(rows)})")
            dialog.add_table(
                name="associations",
                title="",
                columns=cols,
                rows=rows,
                selectable=False,
                multi_select=False,
                sortable=False,
                height=min(6, len(rows))
            )
            dialog.end_section()
        else:
            dialog.add_info("No associations found.", fg="#AAAAAA", font_size=9, italic=True, align="left")

        # Annotations (table)
        if info["annotations"]:
            ann_rows = []
            fmt = getattr(self.parent, "_format_time", None)
            for ann in info["annotations"]:
                ts = ann.get("timestamp_seconds", 0)
                ts_str = fmt(ts) if callable(fmt) else f"{ts:.2f}s"
                ann_rows.append({
                    "time": ts_str,
                    "text": ann.get("annotation_text", "")[:400]
                })
            ann_cols = [("time", "Time", 80), ("text", "Annotation", 320)]
            dialog.add_section("Annotations")
            dialog.add_table(
                name="annotations",
                title="",
                columns=ann_cols,
                rows=ann_rows,
                selectable=False,
                multi_select=False,
                sortable=True,
                height=min(8, len(ann_rows))
            )
            dialog.end_section()
        else:
            dialog.add_info("No annotations.", fg="#AAAAAA", font_size=9, italic=True, align="left")

        # Paths table (all paths associated with this fingerprint)
        if paths:
            path_rows = []
            for p in paths:
                # p may be string or dict depending on get_fingerprint_info output
                if isinstance(p, dict):
                    p_path = p.get("file_path") or p.get("file") or p.get("path") or ""
                    added_at = p.get("added_at") or ""
                else:
                    p_path = p
                    added_at = ""
                path_rows.append({"path": os.path.dirname(p_path) or p_path, "full": p_path, "added": added_at, "exists": os.path.exists(p_path) if p_path else False})
            dialog.add_section(f"Associated paths ({len(path_rows)})")
            dialog.add_table(
                name="fp_paths",
                title=f"",
                columns=[("path", "Path", 260), ("added", "Added", 120), ("exists", "Exists", 60)],
                rows=path_rows,
                selectable=False,
                multi_select=False,
                sortable=True,
                height=min(6, len(path_rows))
            )
            dialog.end_section()

        # Duplicates / available duplicates quick line
        if duplicates:
            dialog.add_info(f"Duplicates: {len(duplicates)}", fg=dialog.theme["accent"], font_size=9, italic=False, align="left")
        if info.get("available_duplicates"):
            dialog.add_info(f"Available duplicates: {len(info.get('available_duplicates'))}", fg="#9FB86E", font_size=9, italic=False, align="left")

        # Stats summary (render small key:value list)
        if stats:
            stat_parts = []
            for k, v in stats.items():
                # keep it compact, show only a few keys typically present
                if k.lower() in ("views", "total_watch_time", "last_watched", "total_watched_seconds"):
                    stat_parts.append(f"{k}: {v}")
            if stat_parts:
                dialog.add_info(" • ".join(stat_parts), fg=dialog.theme["muted"], font_size=9, italic=False, align="left")

        # Snippets (short list)
        if snippets:
            dialog.add_section(" ")
            dialog.add_info("Snippets:", fg="#FFFFFF", font_size=10, italic=False, align="left")
            for s in snippets[:6]:
                if isinstance(s, dict):
                    text = s.get("text") or s.get("snippet_text") or str(s)
                else:
                    text = str(s)
                dialog.add_info("— " + (text[:160].replace("\n", " ") if text else "(empty)"), fg="#CCCCCC", font_size=9, italic=True, align="left")
            dialog.end_section()

        # Watch history table (generic handling if it's a list of dicts)
        # if watch_history and isinstance(watch_history, list) and isinstance(watch_history[0], dict):
        #     wh_rows = []
        #     wh_cols = []
        #     first = watch_history[0]
        #     for key in first.keys():
        #         wh_cols.append((key, key.capitalize(), 120))
        #     for entry in watch_history:
        #         row = {k: (str(v)[:120] if v is not None else "") for k, v in entry.items()}
        #         wh_rows.append(row)
            # dialog.add_section("Watch History")
            # dialog.add_table(
            #     name="",
            #     title=f"Watch history ({len(wh_rows)})",
            #     columns=wh_cols,
            #     rows=wh_rows,
            #     selectable=False,
            #     multi_select=False,
            #     sortable=True,
            #     height=min(6, len(wh_rows)),
            #     hidden_columns=["Fingerprint"]
            # )
            # dialog.end_section()

        self.dialog = dialog

    def _position_right_of_parent(self):
        # place the dialog on the right edge of the parent window
        if not self.dialog:
            return
        self.parent.update_idletasks()
        px, py = self.parent.winfo_x(), self.parent.winfo_y()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        x = px + pw - self.width
        y = py + 30
        dlg_h = getattr(self.dialog, "window_height", min(self.max_height, max(300, ph - 40)))
        self.dialog.geometry(f"{self.width}x{dlg_h}+{x}+{y}")

    def show(self):
        if not self.file_path:
            showwarning(self.parent, "No file", "No current video to show info for.")
            return

        # Build and display modal dialog
        self._build_dialog()
        # self._position_right_of_parent()
        self.dialog.focus_force()
        self.dialog.wait_window()
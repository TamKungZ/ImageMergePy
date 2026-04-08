import os
import re
import sys
import shutil
import hashlib
import threading
import uuid
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

APP_TITLE = "Media Merge / Dedupe Tool"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mts"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

MODE_MOVE = "move"
MODE_COPY_DELETE = "copy_delete"
MODE_COPY_KEEP = "copy_keep"

FONT_FILES = [
    Path("assets/Kanit/Kanit-Regular.ttf"),
    Path("assets/Kanit/Kanit-Italic.ttf"),
    Path("assets/Kanit/Kanit-Bold.ttf"),
]

UUID_LIKE_RE = re.compile(
    r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?: \(\d+\))?$"
)
HEX_HASH_RE = re.compile(r"^[0-9a-fA-F]{24,}(?: \(\d+\))?$")
IMG_NUMBER_RE = re.compile(r"^(IMG)[ _-]?(\d+)(?:\s*\(\d+\))?$", re.IGNORECASE)
PREFIX_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def resource_path(relative_path: str | Path) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / Path(relative_path)


def register_windows_font(font_path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        FR_PRIVATE = 0x10
        result = ctypes.windll.gdi32.AddFontResourceExW(str(font_path), FR_PRIVATE, 0)
        if result > 0:
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
            return True
    except Exception:
        pass
    return False


def setup_app_fonts() -> str:
    for relative_font in FONT_FILES:
        font_path = resource_path(relative_font)
        if font_path.exists() and register_windows_font(font_path):
            return "Kanit"
    return "Segoe UI"


def normalize_prefix(prefix: str) -> str:
    prefix = prefix.strip()
    if not prefix:
        return ""
    prefix = prefix.replace(" ", "-")
    prefix = PREFIX_ALLOWED_RE.sub("-", prefix)
    prefix = re.sub(r"-+", "-", prefix).strip("-_")
    return prefix.lower()


def build_output_name(index: int, ext: str, prefix: str = "") -> str:
    prefix = normalize_prefix(prefix)
    if prefix:
        return f"{prefix}-{index:04d}{ext.lower()}"
    return f"{index:04d}{ext.lower()}"


def split_existing_prefix_and_number(path: Path) -> tuple[str, int]:
    stem = path.stem
    m = re.match(r"^(?:(.+?)-)?(\d+)$", stem)
    if m:
        prefix = normalize_prefix(m.group(1) or "")
        return prefix, int(m.group(2))
    m2 = re.match(r"^(\d+)", stem)
    if m2:
        return "", int(m2.group(1))
    return "", 99999999


def dedupe_key(file_hash: str, ext: str) -> tuple[str, str]:
    return file_hash, ext.lower()


class Logger:
    def __init__(self, widget: tk.Text):
        self.widget = widget

    def write(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert("end", text + "\n")
        self.widget.see("end")
        self.widget.configure(state="disabled")
        self.widget.update_idletasks()

    def clear(self):
        self.widget.configure(state="normal")
        self.widget.delete("1.0", "end")
        self.widget.configure(state="disabled")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def classify_source_name(path: Path) -> tuple[str, int | None]:
    stem = path.stem.strip()
    img_match = IMG_NUMBER_RE.match(stem)
    if img_match:
        return "img_number", int(img_match.group(2))
    if UUID_LIKE_RE.match(stem) or HEX_HASH_RE.match(stem):
        return "time_only", None
    return "default", None


def source_sort_key(item):
    file_path, ctime, _prefix = item
    stem_lower = file_path.stem.lower()
    ext_lower = file_path.suffix.lower()
    group_type, value = classify_source_name(file_path)

    if group_type == "img_number":
        return (0, int(value), ctime, stem_lower, ext_lower)
    if group_type == "time_only":
        return (1, ctime, stem_lower, ext_lower)
    return (2, ctime, stem_lower, ext_lower)


def is_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MEDIA_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def iter_media_files(root_dir: Path):
    for root, _, filenames in os.walk(root_dir):
        for name in filenames:
            p = Path(root) / name
            if p.suffix.lower() in MEDIA_EXTS:
                yield p


def organize_output(output_dir: Path, logger: Logger | None = None):
    media_files = [p for p in output_dir.iterdir() if is_media_file(p)]

    image_files = sorted(
        [p for p in media_files if is_image(p)],
        key=lambda p: split_existing_prefix_and_number(p)[1],
    )
    video_files = sorted(
        [p for p in media_files if is_video(p)],
        key=lambda p: split_existing_prefix_and_number(p)[1],
    )
    ordered_files = image_files + video_files

    temp_files: list[tuple[Path, str]] = []
    for file_path in ordered_files:
        prefix, _ = split_existing_prefix_and_number(file_path)
        temp_name = f"__temp__{uuid.uuid4().hex}{file_path.suffix.lower()}"
        temp_path = output_dir / temp_name
        file_path.rename(temp_path)
        temp_files.append((temp_path, prefix))

    renamed_files: list[Path] = []
    for idx, (temp_path, prefix) in enumerate(temp_files, start=1):
        new_path = output_dir / build_output_name(idx, temp_path.suffix, prefix)
        temp_path.rename(new_path)
        renamed_files.append(new_path)

    if logger:
        logger.write(f"จัดระเบียบ output เสร็จ {len(renamed_files)} ไฟล์ (รูปก่อน วิดีโอท้ายสุด)")

    return renamed_files


def collect_source_media(input_dir_configs: list[dict]):
    image_files = []
    video_files = []

    for cfg in input_dir_configs:
        src: Path = cfg["path"]
        prefix: str = cfg.get("prefix", "")
        for file_path in iter_media_files(src):
            try:
                ctime = os.path.getctime(file_path)
            except OSError:
                ctime = 0
            item = (file_path, ctime, prefix)
            if is_image(file_path):
                image_files.append(item)
            elif is_video(file_path):
                video_files.append(item)

    image_files.sort(key=source_sort_key)
    video_files.sort(key=source_sort_key)
    return image_files + video_files


def safe_delete_file(path: Path, logger: Logger | None = None):
    try:
        if path.exists():
            path.unlink()
            if logger:
                logger.write(f"ลบต้นฉบับ: {path}")
    except Exception as e:
        if logger:
            logger.write(f"ลบไม่ได้: {path} -> {e}")


def process_media(
    input_dir_configs: list[dict],
    output_dir: Path,
    mode: str,
    clear_output_first: bool,
    logger: Logger,
):
    if not input_dir_configs:
        raise ValueError("ยังไม่ได้เลือก input folder")

    input_paths = [cfg["path"] for cfg in input_dir_configs]
    if output_dir in input_paths:
        raise ValueError("output folder ห้ามซ้ำกับ input folder")

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.write("เริ่มทำงาน...")
    logger.write(f"โหมด: {mode}")
    logger.write(f"Output: {output_dir}")
    for cfg in input_dir_configs:
        logger.write(f"Input: {cfg['path']} | prefix: {normalize_prefix(cfg.get('prefix', '')) or '-'}")

    if clear_output_first:
        logger.write("กำลังล้างไฟล์ media เดิมใน output...")
        removed = 0
        for p in list(output_dir.iterdir()):
            if is_media_file(p):
                p.unlink()
                removed += 1
        logger.write(f"ล้าง output media เดิมแล้ว {removed} ไฟล์")

    existing_output_files = organize_output(output_dir, logger=logger)
    existing_hashes: dict[tuple[str, str], Path] = {}
    for file_path in existing_output_files:
        try:
            file_hash = sha256_file(file_path)
            existing_hashes[dedupe_key(file_hash, file_path.suffix)] = file_path
        except Exception as e:
            logger.write(f"ข้ามไฟล์ output ที่อ่านไม่ได้: {file_path} -> {e}")

    source_items = collect_source_media(input_dir_configs)
    logger.write(f"พบ media ใน input ทั้งหมด {len(source_items)} ไฟล์")

    added = 0
    skipped = 0
    moved = 0
    copied = 0
    deleted_sources = 0
    failed = 0
    current_index = len(existing_output_files)

    for file_path, _ctime, prefix in source_items:
        try:
            file_hash = sha256_file(file_path)
        except Exception as e:
            failed += 1
            logger.write(f"อ่าน hash ไม่ได้: {file_path} -> {e}")
            continue

        ext = file_path.suffix.lower()
        file_key = dedupe_key(file_hash, ext)

        if file_key in existing_hashes:
            skipped += 1
            logger.write(f"ซ้ำ ข้าม: {file_path}")
            if mode in {MODE_MOVE, MODE_COPY_DELETE}:
                safe_delete_file(file_path, logger)
                deleted_sources += 1
            continue

        current_index += 1
        dest_path = output_dir / build_output_name(current_index, ext, prefix)

        try:
            if mode == MODE_MOVE:
                shutil.move(str(file_path), str(dest_path))
                moved += 1
                logger.write(f"ย้าย: {file_path} -> {dest_path.name}")
            elif mode == MODE_COPY_DELETE:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(f"คัดลอก: {file_path} -> {dest_path.name}")
                safe_delete_file(file_path, logger)
                deleted_sources += 1
            elif mode == MODE_COPY_KEEP:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(f"คัดลอก: {file_path} -> {dest_path.name}")
            else:
                raise ValueError(f"ไม่รู้จักโหมด: {mode}")

            existing_hashes[file_key] = dest_path
            added += 1
        except Exception as e:
            failed += 1
            logger.write(f"ทำไม่สำเร็จ: {file_path} -> {e}")

    final_files = organize_output(output_dir, logger=logger)

    logger.write("=" * 50)
    logger.write(f"เพิ่มใหม่: {added}")
    logger.write(f"ซ้ำข้ามไป: {skipped}")
    logger.write(f"ย้าย: {moved}")
    logger.write(f"คัดลอก: {copied}")
    logger.write(f"ลบต้นฉบับ: {deleted_sources}")
    logger.write(f"ผิดพลาด: {failed}")
    logger.write(f"รวม output ตอนนี้: {len(final_files)} ไฟล์")
    logger.write("เสร็จแล้ว 🎉")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x760")
        self.minsize(980, 680)

        self.input_entries: list[dict] = []
        self.output_dir_var = tk.StringVar()
        self.mode_var = tk.StringVar(value=MODE_COPY_KEEP)
        self.clear_output_var = tk.BooleanVar(value=False)
        self.is_running = False
        self.font_family = setup_app_fonts()

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        default_font = (self.font_family, 10)
        style.configure(".", font=default_font)
        style.configure("TLabelframe.Label", font=(self.font_family, 10, "bold"))
        style.configure("Title.TLabel", font=(self.font_family, 15, "bold"))

        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Media Merge / Dedupe Tool", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(
            outer,
            text=(
                "รวมไฟล์จากหลายโฟลเดอร์, กันไฟล์ซ้ำด้วย SHA-256 + นามสกุลไฟล์, จัดชื่อเป็นเลขเรียง, "
                "วางรูปไว้ก่อน วิดีโอไว้ท้ายสุด, จัดลำดับพิเศษสำหรับชื่อไฟล์บางแบบ และตั้ง prefix แยกต่อโฟลเดอร์ได้"
            ),
            wraplength=980,
        ).pack(anchor="w", pady=(0, 10))

        input_frame = ttk.LabelFrame(outer, text="Input folders + prefix", padding=10)
        input_frame.pack(fill="both", pady=(0, 10))

        input_btn_row = ttk.Frame(input_frame)
        input_btn_row.pack(fill="x", pady=(0, 8))
        ttk.Button(input_btn_row, text="เพิ่มโฟลเดอร์", command=self.add_input_folder).pack(side="left")
        ttk.Button(input_btn_row, text="แก้ prefix", command=self.edit_selected_prefix).pack(side="left", padx=6)
        ttk.Button(input_btn_row, text="ลบที่เลือก", command=self.remove_selected_input).pack(side="left", padx=6)
        ttk.Button(input_btn_row, text="ล้างทั้งหมด", command=self.clear_inputs).pack(side="left")

        columns = ("folder", "prefix")
        self.input_tree = ttk.Treeview(input_frame, columns=columns, show="headings", height=8)
        self.input_tree.heading("folder", text="Folder")
        self.input_tree.heading("prefix", text="Prefix")
        self.input_tree.column("folder", width=760, anchor="w")
        self.input_tree.column("prefix", width=180, anchor="w")
        self.input_tree.pack(fill="x", expand=False)
        self.input_tree.bind("<Double-1>", self._on_tree_double_click)

        output_frame = ttk.LabelFrame(outer, text="Output folder", padding=10)
        output_frame.pack(fill="x", pady=(0, 10))
        output_row = ttk.Frame(output_frame)
        output_row.pack(fill="x")
        ttk.Entry(output_row, textvariable=self.output_dir_var).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="เลือก output", command=self.choose_output_folder).pack(side="left", padx=(8, 0))

        mode_frame = ttk.LabelFrame(outer, text="Mode", padding=10)
        mode_frame.pack(fill="x", pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="คัดลอกอย่างเดียว (ไม่ลบ input)", variable=self.mode_var, value=MODE_COPY_KEEP).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="คัดลอกแล้วลบต้นฉบับใน input", variable=self.mode_var, value=MODE_COPY_DELETE).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="ย้ายไฟล์จาก input ไป output", variable=self.mode_var, value=MODE_MOVE).pack(anchor="w")
        ttk.Checkbutton(mode_frame, text="ล้างไฟล์ media เดิมใน output ก่อนเริ่ม", variable=self.clear_output_var).pack(anchor="w", pady=(8, 0))

        ttk.Label(
            mode_frame,
            text=(
                "หมายเหตุ: ไฟล์ซ้ำจะถูกข้ามเมื่อ hash ของไฟล์จริงและนามสกุลตรงกัน\n"
                "ไฟล์ชื่อแนว IMG_0072 จะเรียงตามเลข แล้วใช้เวลาเป็นตัวตัดสินเมื่อเลขชนกัน\n"
                "ไฟล์ชื่อแนว UUID / hash ยาว ๆ จะเรียงตามเวลาโดยตรง\n"
                "ไฟล์อื่น ๆ ยังใช้การเรียงแบบเดิมตามเวลา\n"
                "prefix ถูกตั้งแยกตามแต่ละ input folder และชื่อไฟล์จะออกแบบ full-0001.jpg"
            ),
            wraplength=980,
        ).pack(anchor="w", pady=(8, 0))

        action_row = ttk.Frame(outer)
        action_row.pack(fill="x", pady=(0, 10))
        self.start_btn = ttk.Button(action_row, text="เริ่ม", command=self.start_process)
        self.start_btn.pack(side="left")

        log_frame = ttk.LabelFrame(outer, text="Log", padding=10)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(log_frame, wrap="word", state="disabled", font=(self.font_family, 10))
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.logger = Logger(self.log_text)

    def prompt_prefix(self, initial: str = "") -> str | None:
        value = simpledialog.askstring(
            APP_TITLE,
            "ตั้ง prefix สำหรับโฟลเดอร์นี้\nปล่อยว่างได้ เช่น full, short, ref",
            initialvalue=initial,
            parent=self,
        )
        if value is None:
            return None
        return normalize_prefix(value)

    def add_input_folder(self):
        folder = filedialog.askdirectory(title="เลือก input folder")
        if not folder:
            return
        path = Path(folder)
        if any(entry["path"] == path for entry in self.input_entries):
            messagebox.showinfo(APP_TITLE, "โฟลเดอร์นี้ถูกเพิ่มแล้ว")
            return
        prefix = self.prompt_prefix(path.name)  # default from folder name
        if prefix is None:
            return
        entry = {"path": path, "prefix": prefix}
        self.input_entries.append(entry)
        self.input_tree.insert("", "end", iid=str(path), values=(str(path), prefix or "-"))

    def _get_selected_paths(self) -> list[str]:
        return list(self.input_tree.selection())

    def edit_selected_prefix(self):
        selected = self._get_selected_paths()
        if not selected:
            messagebox.showwarning(APP_TITLE, "กรุณาเลือกโฟลเดอร์ก่อน")
            return
        if len(selected) > 1:
            messagebox.showwarning(APP_TITLE, "แก้ prefix ได้ครั้งละ 1 โฟลเดอร์")
            return
        sel = selected[0]
        for entry in self.input_entries:
            if str(entry["path"]) == sel:
                new_prefix = self.prompt_prefix(entry.get("prefix", ""))
                if new_prefix is None:
                    return
                entry["prefix"] = new_prefix
                self.input_tree.item(sel, values=(str(entry["path"]), new_prefix or "-"))
                return

    def _on_tree_double_click(self, _event):
        self.edit_selected_prefix()

    def remove_selected_input(self):
        selected = self._get_selected_paths()
        if not selected:
            return
        selected_set = set(selected)
        self.input_entries = [e for e in self.input_entries if str(e["path"]) not in selected_set]
        for iid in selected:
            self.input_tree.delete(iid)

    def clear_inputs(self):
        self.input_entries.clear()
        for iid in self.input_tree.get_children():
            self.input_tree.delete(iid)

    def choose_output_folder(self):
        folder = filedialog.askdirectory(title="เลือก output folder")
        if folder:
            self.output_dir_var.set(folder)

    def start_process(self):
        if self.is_running:
            return

        input_configs = [{"path": e["path"], "prefix": e.get("prefix", "")} for e in self.input_entries]
        output_dir_text = self.output_dir_var.get().strip()
        mode = self.mode_var.get()
        clear_output_first = self.clear_output_var.get()

        if not input_configs:
            messagebox.showwarning(APP_TITLE, "กรุณาเลือก input folder อย่างน้อย 1 โฟลเดอร์")
            return
        if not output_dir_text:
            messagebox.showwarning(APP_TITLE, "กรุณาเลือก output folder")
            return

        output_dir = Path(output_dir_text)
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.logger.clear()

        worker = threading.Thread(
            target=self._run_process,
            args=(input_configs, output_dir, mode, clear_output_first),
            daemon=True,
        )
        worker.start()

    def _run_process(self, input_configs, output_dir, mode, clear_output_first):
        try:
            process_media(input_configs, output_dir, mode, clear_output_first, self.logger)
            self.after(0, lambda: messagebox.showinfo(APP_TITLE, "ทำเสร็จแล้ว"))
        except Exception as e:
            self.logger.write(f"ERROR: {e}")
            self.after(0, lambda: messagebox.showerror(APP_TITLE, str(e)))
        finally:
            self.is_running = False
            self.after(0, lambda: self.start_btn.configure(state="normal"))


if __name__ == "__main__":
    app = App()
    app.mainloop()

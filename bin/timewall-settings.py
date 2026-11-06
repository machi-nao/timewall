#!/usr/bin/env python3
import json, os, re, subprocess, sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon, QImageReader, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QFormLayout)

HOME = Path.home()
CFG = HOME / ".config/timewall.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MODE_KEYS = ["off", "static", "slideshow", "schedule", "sunpath"]
FOLDER_MODES = ("slideshow", "schedule", "sunpath")
try:  # SUN5
    QPushButton
except NameError:
    try:
        from PyQt6.QtWidgets import QPushButton
    except ImportError:
        from PySide6.QtWidgets import QPushButton
SUN5_DIRS = ["1_before_sunrise", "2_sunrise", "3_day", "4_sunset", "5_after_sunset"]

def sun5_sections(folder):
    base = Path(folder).expanduser()
    if not folder or not any((base / n).is_dir() for n in SUN5_DIRS):
        return None
    return [list_images(str(base / n)) if (base / n).is_dir() else [] for n in SUN5_DIRS]
MAX_DESK = 8
THUMB = QSize(120, 68)

def auto_slideshow_images(base):  # SLIDESRC
    b = Path(base).expanduser()
    out, seen = [], set()
    for folder in [b] + [b / n for n in SUN5_DIRS]:
        for f in list_images(str(folder)):
            try:
                key = (f.name.lower(), f.stat().st_size)
            except OSError:
                continue
            if key not in seen:
                seen.add(key)
                out.append(f)
    return out

# ---------- 言語辞書(言語を足すときは、en をコピーして翻訳する)----------
STR = {
    "ja": {
        "name": "日本語",
        "title": "TimeWall 壁紙設定",
        "g_settings": "全体の設定",
        "location": "場所",
        "loc_ph": "auto / 都市名 / 緯度,経度",
        "desk_count": "デスクトップ数(1〜8)",
        "change_count": "数を変更",
        "hello": "helloの壁紙と連動する",
        "paused": "timewallの自動切り替えを一時停止する(Aerialは動作します)",
        "language": "言語",
        "lang_auto": "自動(システムに合わせる)",
        "tab": "デスクトップ {n}",
        "apply": "保存して適用",
        "close": "閉じる",
        "mode": "モード",
        "mode_off": "停止(壁紙に触らない)",
        "mode_static": "固定(1枚)",
        "mode_slideshow": "スライドショー",
        "mode_schedule": "時刻指定(最大100枚)",
        "mode_sunpath": "日の出・日の入り連動(最大100枚)",
        "folder": "画像フォルダ",
        "pick": "選ぶ",
        "open_folder": "フォルダを開く",
        "image": "固定する画像",
        "interval": "切り替え間隔",
        "min_suffix": " 分",
        "times": "切り替え時刻",
        "times_ph": "例: 06:00, 10:00, 16:00, 19:00(画像と同じ数まで)",
        "fade": "なめらかに混ぜる(フェード)",
        "day_count": "日中用の枚数",
        "twilight": "日の出・日の入りの幅(前後)",
        "sun5_make": "5区間のフォルダを作る",
        "sun5_nofolder": "先に画像フォルダを選んでください",
        "sun5_info": "5区間方式 → {c}(空の区間は前の画像を続けます)",
        "sun5_n0": "日の出前", "sun5_n1": "日の出", "sun5_n2": "日中", "sun5_n3": "日の入り", "sun5_n4": "日没後",
        "sun5_unit": "{n}枚",
        "src_label": "画像の元",
        "src_auto": "自動(他のモードと同じ画像)",
        "src_manual": "手動(専用フォルダの画像)",
        "src_info_auto": "自動: {n}枚(フォルダ直下と5つのサブフォルダ)",
        "day_auto": "自動(昼夜の長さで決める)",
        "info_folder": "フォルダ内の画像: {n}枚(ファイル名の順に使います)",
        "info_over12": " ※使われるのは先頭の100枚までです",
        "info_off": "このデスクトップの壁紙には触りません",
        "preview": "動きを確認する(2秒ごと・2周)",
        "prev_stop": "確認を止める",
        "prev_run": "確認中… {i}/{n}",
        "prev_none": "確認できる画像がありません",
        "prev_one": "画像が1枚だけなので、動きはありません",
        "dlg_folder": "画像フォルダを選ぶ",
        "dlg_image": "固定する画像を選ぶ",
        "img_filter": "画像 (*.jpg *.jpeg *.png *.webp)",
        "err_image": "デスクトップ{n}: 固定する画像を選んでください",
        "err_times_count": "デスクトップ{n}: 時刻を1〜100個入れてください",
        "err_time_bad": "デスクトップ{n}: 時刻「{t}」が正しくありません",
        "count_done": "デスクトップ数を {n} にしました",
        "count_fail": "デスクトップ数を変更できません",
        "input_check": "入力を確認してください",
        "saved": "保存して適用しました",
        "saved_lang": "保存して適用しました(言語は再起動後に切り替わります)",
        "no_ids": "デスクトップのIDを取得できませんでした",
    },
    "en": {
        "name": "English",
        "title": "TimeWall Wallpaper Settings",
        "g_settings": "General",
        "location": "Location",
        "loc_ph": "auto / city name / lat,lon",
        "desk_count": "Number of desktops (1-8)",
        "change_count": "Change count",
        "hello": "Sync with the hello screen wallpaper",
        "paused": "Pause everything",
        "language": "Language",
        "lang_auto": "Auto (follow the system)",
        "tab": "Desktop {n}",
        "apply": "Save and apply",
        "close": "Close",
        "mode": "Mode",
        "mode_off": "Off (leave the wallpaper alone)",
        "mode_static": "Fixed (one image)",
        "mode_slideshow": "Slideshow",
        "mode_schedule": "Time schedule (up to 100 images)",
        "mode_sunpath": "Sunrise / sunset (up to 100 images)",
        "folder": "Image folder",
        "pick": "Browse",
        "open_folder": "Open folder",
        "image": "Fixed image",
        "interval": "Interval",
        "min_suffix": " min",
        "times": "Switch times",
        "times_ph": "e.g. 06:00, 10:00, 16:00, 19:00 (up to the number of images)",
        "fade": "Cross-fade between images",
        "day_count": "Daytime images",
        "twilight": "Sunrise/sunset width (+/- min)",
        "sun5_make": "Create 5 section folders",
        "sun5_nofolder": "Choose an image folder first",
        "sun5_info": "5-section mode -> {c} (empty sections keep the previous image)",
        "sun5_n0": "Before sunrise", "sun5_n1": "Sunrise", "sun5_n2": "Day", "sun5_n3": "Sunset", "sun5_n4": "After sunset",
        "sun5_unit": "{n} img",
        "src_label": "Image source",
        "src_auto": "Auto (same images as the other modes)",
        "src_manual": "Manual (dedicated folder)",
        "src_info_auto": "Auto: {n} images (folder + 5 sections)",
        "day_auto": "Auto (from day/night length)",
        "info_folder": "Images in folder: {n} (used in file name order)",
        "info_over12": " * only the first 100 are used",
        "info_off": "This desktop's wallpaper is left alone",
        "preview": "Preview the motion (every 2 s, 2 rounds)",
        "prev_stop": "Stop preview",
        "prev_run": "Previewing... {i}/{n}",
        "prev_none": "No images to preview",
        "prev_one": "Only one image, so there is no motion",
        "dlg_folder": "Choose image folder",
        "dlg_image": "Choose a fixed image",
        "img_filter": "Images (*.jpg *.jpeg *.png *.webp)",
        "err_image": "Desktop {n}: please choose a fixed image",
        "err_times_count": "Desktop {n}: enter 1 to 100 times",
        "err_time_bad": 'Desktop {n}: time "{t}" is not valid',
        "count_done": "Desktop count is now {n}",
        "count_fail": "Cannot change the desktop count",
        "input_check": "Please check your input",
        "saved": "Saved and applied",
        "saved_lang": "Saved and applied (the language changes after a restart)",
        "no_ids": "Could not get the desktop IDs",
    },
}


def detect_lang(setting):
    if setting in STR:
        return setting
    raw = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
           or os.environ.get("LANG") or "")
    code = raw[:2].lower()
    return code if code in STR else "en"


LANG = "en"


def t(key, **kw):
    s = STR[LANG].get(key) or STR["en"][key]
    return s.format(**kw) if kw else s

# ---------- Aerial(ロック画面の動画)AERIAL-UI ----------
AT = {
    "ja": {
        "a_header": "Aerial(ロック画面の動画)",
        "c_chime": "このデスクトップでロックチャイムを鳴らす",
        "a_use": "このデスクトップでAerialを使う",
        "a_src": "動画の選び方",
        "a_src_default": "全体の設定に従う",
        "a_src_file": "指定した動画",
        "a_src_random": "ランダム",
        "a_video": "動画",
        "s_tw": "① timewall(基本の壁紙)",
        "s_aerial": "② Aerial(ロック画面の動画)",
        "s_chime": "③ ロックチャイム",
        "s_after": "④ 解除後の壁紙",
        "a_none": "なし(pearOS標準のロック画面)",
        "a_after": "解除後の壁紙",
        "a_after_frame": "Aerialで止めたフレーム",
        "a_after_tw": "timewallの画像",
        "err_video": "Desktop {n}: Aerialの動画を選んでください",
        "g_mode": "Aerial: 全体のデフォルト",
        "g_same": "すべて同じ動画",
        "g_random": "ランダムに選ぶ",
        "g_video": "Aerial: すべて同じ動画",
        "g_inherit": "止めたフレームを、解除後の壁紙にする",
        "no_videos": "(動画がありません: ~/Videos/aerial)",
    },
    "en": {
        "a_header": "Aerial (lock screen video)",
        "c_chime": "Play the lock chime on this desktop",
        "a_use": "Use Aerial on this desktop",
        "a_src": "Video selection",
        "a_src_default": "Follow the global setting",
        "a_src_file": "A specific video",
        "a_src_random": "Random",
        "a_video": "Video",
        "s_tw": "1. timewall (base wallpaper)",
        "s_aerial": "2. Aerial (lock screen video)",
        "s_chime": "3. Lock chime",
        "s_after": "4. Wallpaper after unlock",
        "a_none": "None (pearOS default lock screen)",
        "a_after": "Wallpaper after unlock",
        "a_after_frame": "The frame Aerial stopped on",
        "a_after_tw": "The timewall image",
        "err_video": "Desktop {n}: please choose an Aerial video",
        "g_mode": "Aerial: global default",
        "g_same": "Same video everywhere",
        "g_random": "Pick randomly",
        "g_video": "Aerial: the same video",
        "g_inherit": "Use the frozen frame as the wallpaper after unlock",
        "no_videos": "(no videos in ~/Videos/aerial)",
    },
}


def ta(key, **kw):
    s = AT.get(LANG, AT["en"]).get(key) or AT["en"][key]
    return s.format(**kw) if kw else s


def tilde(p):
    s, h = str(p), str(HOME)
    return "~" + s[len(h):] if s.startswith(h + "/") else s


def aerial_videos():
    d = Path(load().get("aerial", {}).get("dir", "~/Videos/aerial")).expanduser()
    exts = (".mp4", ".webm", ".mkv", ".mov")
    return sorted(p for p in d.iterdir() if p.suffix.lower() in exts) if d.is_dir() else []


def fill_video_combo(combo, current=None):
    vids = [tilde(p) for p in aerial_videos()]
    cur = tilde(Path(current).expanduser()) if current else None
    for v in vids:
        combo.addItem(Path(v).name, v)
    if cur and cur not in vids:
        combo.addItem(Path(cur).name + " (?)", cur)
    if not vids and not cur:
        combo.addItem(ta("no_videos"), "")
    if cur:
        combo.setCurrentIndex(max(0, combo.findData(cur)))


def read_inherit():
    try:
        r = subprocess.run(["kreadconfig6", "--file", "pearos-chimesrc", "--group", "Aerial",
                            "--key", "InheritFrame", "--default", "true"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip().lower() != "false"
    except Exception:
        return True


def write_inherit(on):
    try:
        subprocess.run(["kwriteconfig6", "--file", "pearos-chimesrc", "--group", "Aerial",
                        "--key", "InheritFrame", "true" if on else "false"], timeout=5)
    except Exception:
        pass


# ---------- 設定・KWin(画面に依存しない部分)----------
def load():
    try:
        return json.load(open(CFG))
    except Exception:
        return {"location": "auto", "desktops": {}}


def save(cfg):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(CFG, "w"), ensure_ascii=False, indent=2)


def kwin_count():
    r = subprocess.run(["qdbus6", "org.kde.KWin", "/VirtualDesktopManager",
                        "org.kde.KWin.VirtualDesktopManager.count"],
                       capture_output=True, text=True)
    try:
        return max(1, min(MAX_DESK, int(r.stdout.strip())))
    except ValueError:
        return 5


def set_kwin_count(n):
    base = ["qdbus6", "org.kde.KWin", "/VirtualDesktopManager"]
    for _ in range(MAX_DESK):
        cur = kwin_count()
        if cur == n:
            return
        if cur < n:
            subprocess.run(base + ["org.kde.KWin.VirtualDesktopManager.createDesktop",
                                   str(cur), f"Desktop {cur + 1}"], check=True)
        else:
            r = subprocess.run(["gdbus", "call", "--session", "--dest", "org.kde.KWin",
                                "--object-path", "/VirtualDesktopManager", "--method",
                                "org.freedesktop.DBus.Properties.Get",
                                "org.kde.KWin.VirtualDesktopManager", "desktops"],
                               capture_output=True, text=True, check=True)
            ids = re.findall(r"'([0-9a-fA-F-]{36})'", r.stdout)
            if not ids:
                raise RuntimeError(t("no_ids"))
            subprocess.run(base + ["org.kde.KWin.VirtualDesktopManager.removeDesktop",
                                   ids[-1]], check=True)


def list_images(folder):
    d = Path(folder).expanduser()
    if not d.is_dir():
        return []
    return sorted((f for f in d.iterdir() if f.suffix.lower() in EXTS),
                  key=lambda f: f.name.lower())


def thumb(path):
    r = QImageReader(str(path))
    r.setAutoTransform(True)
    sz = r.size()
    if sz.isValid():
        sz.scale(THUMB, Qt.AspectRatioMode.KeepAspectRatio)
        r.setScaledSize(sz)
    img = r.read()
    return QPixmap.fromImage(img) if not img.isNull() else QPixmap()


LOCK = HOME / ".cache/timewall/preview.lock"
ACTIVE = [None]


def set_wallpaper(path):
    js = ('var img = "file://" + %s;\n'
          'desktops().forEach(function(d) {\n'
          '  if (d.screen < 0) return;\n'
          '  d.wallpaperPlugin = "org.kde.image";\n'
          '  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];\n'
          '  d.writeConfig("Image", img);\n'
          '});\n') % json.dumps(str(path))
    subprocess.run(["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
                    "org.kde.PlasmaShell.evaluateScript", js],
                   capture_output=True)


# ---------- 画面 ----------
class DeskTab(QWidget):
    def __init__(self, n, conf):
        super().__init__()
        self.n = n
        self.orig = conf or {}
        self.rows = {}
        mode = self.orig.get("mode", "off")

        self.mode = QComboBox()
        for k in MODE_KEYS:
            self.mode.addItem(t("mode_" + k), k)
        self.mode.setCurrentIndex(max(0, self.mode.findData(mode)))

        # SLIDEDIR2: separate folders for slideshow and the other modes
        _def_main = f"~/Pictures/wp/desktop{n}"
        _def_slide = f"~/Pictures/wp/desktop{n}-slideshow"
        _main = self.orig.get("dir") or _def_main
        _slide = self.orig.get("slideshow_dir") or _def_slide
        self.dir_store = {"main": _main, "slide": _slide}
        self._last_mode = None
        self.folder = QLineEdit(_slide if self.orig.get("mode") == "slideshow" else _main)
        b_pick = QPushButton(t("pick"))
        b_open = QPushButton(t("open_folder"))
        fw = QWidget()
        fl = QHBoxLayout(fw)
        fl.setContentsMargins(0, 0, 0, 0)
        for w in (self.folder, b_pick, b_open):
            fl.addWidget(w)
        fl.setStretch(0, 1)

        self.image = QLineEdit(self.orig.get("image", ""))
        b_img = QPushButton(t("pick"))
        iw = QWidget()
        il = QHBoxLayout(iw)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(self.image)
        il.addWidget(b_img)
        il.setStretch(0, 1)

        self.minutes = QSpinBox()
        self.minutes.setRange(3, 60)
        self.minutes.setSuffix(t("min_suffix"))
        self.minutes.setValue(int(self.orig.get("minutes", 10)))

        self.times = QLineEdit(", ".join(self.orig.get("times", [])))
        self.times.setPlaceholderText(t("times_ph"))

        self.fade = QCheckBox(t("fade"))
        self.fade.setChecked(bool(self.orig.get("fade", False)))

        self.daycount = QSpinBox()
        self.daycount.setRange(0, 100)
        self.daycount.setSpecialValueText(t("day_auto"))
        self.daycount.setValue(int(self.orig.get("day_count", 0)))
        self.twilight = QSpinBox()  # SUN5
        self.twilight.setRange(0, 120)
        self.twilight.setSuffix(t("min_suffix"))
        self.twilight.setValue(int(self.orig.get("twilight_min", 30)))
        self.sun5btn = QPushButton(t("sun5_make"))
        self.sun5btn.clicked.connect(self.make_sun5)
        self.slidesrc = QComboBox()  # SLIDESRC
        self.slidesrc.addItem(t("src_auto"), "auto")
        self.slidesrc.addItem(t("src_manual"), "manual")
        _si = self.slidesrc.findData(self.orig.get("slideshow_source") or "auto")
        self.slidesrc.setCurrentIndex(max(0, _si))
        self.slidesrc.currentIndexChanged.connect(self.refresh)

        self.info = QLabel()
        self.info.setStyleSheet("color: gray;")
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbs.setMovement(QListWidget.Movement.Static)
        self.thumbs.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.thumbs.setIconSize(THUMB)
        self.thumbs.setWordWrap(True)
        self.thumbs.setMinimumHeight(190)

        self.form = QFormLayout()
        self.form.addRow(QLabel("<b>" + ta("s_tw") + "</b>"))
        self.form.addRow(QLabel(t("mode")), self.mode)
        self._row("slidesrc", t("src_label"), self.slidesrc)
        self._row("folder", t("folder"), fw)
        self._row("image", t("image"), iw)
        self._row("minutes", t("interval"), self.minutes)
        self._row("times", t("times"), self.times)
        self._row("fade", "", self.fade)
        self._row("daycount", t("day_count"), self.daycount)
        self._row("twilight", t("twilight"), self.twilight)
        self._row("sun5btn", "", self.sun5btn)
        # AERIAL-UI2
        ao = self.orig.get("aerial", {}) or {}
        src0 = ao.get("source", "default")
        if ao.get("use") is False:
            src0 = "none"
        elif src0 == "default":
            _g = load().get("aerial", {}) or {}
            src0 = "random" if _g.get("mode", "same") == "random" else "file"
            if src0 == "file" and not ao.get("video"):
                ao = dict(ao, video=_g.get("video"))
        self.a_src = QComboBox()
        self.a_src.addItem(ta("a_src_file"), "file")
        self.a_src.addItem(ta("a_src_random"), "random")
        self.a_src.addItem(ta("a_none"), "none")
        self.a_src.setCurrentIndex(max(0, self.a_src.findData(src0)))
        self.a_video = QComboBox()
        fill_video_combo(self.a_video, ao.get("video"))
        self.a_after = QComboBox()
        self.a_after.addItem(ta("a_after_frame"), "frame")
        self.a_after.addItem(ta("a_after_tw"), "timewall")
        self.a_after.setCurrentIndex(max(0, self.a_after.findData(ao.get("after", "frame"))))
        self.chime = QCheckBox(ta("c_chime"))  # AERIAL-CHIME
        self.chime.setChecked(bool(self.orig.get("chime", True)))
        self.form.addRow(QLabel("<b>" + ta("s_aerial") + "</b>"))
        self.form.addRow(QLabel(ta("a_src")), self.a_src)
        self.form.addRow(QLabel(ta("a_video")), self.a_video)
        self.form.addRow(QLabel("<b>" + ta("s_chime") + "</b>"))
        self.form.addRow("", self.chime)
        self.form.addRow(QLabel("<b>" + ta("s_after") + "</b>"))
        self.form.addRow(QLabel(ta("a_after")), self.a_after)
        self.a_src.currentIndexChanged.connect(self._aerial_toggle)
        self._aerial_toggle()

        lay = QVBoxLayout(self)
        lay.addLayout(self.form)
        lay.addWidget(self.info)
        self.b_prev = QPushButton(t("preview"))
        self.b_prev.clicked.connect(self.toggle_preview)
        pl = QHBoxLayout()
        pl.addWidget(self.b_prev)
        pl.addStretch(1)
        lay.addLayout(pl)
        lay.addWidget(self.thumbs, 1)

        self.mode.currentIndexChanged.connect(self.refresh)
        self.folder.editingFinished.connect(self.refresh)
        self.image.editingFinished.connect(self.refresh)
        b_pick.clicked.connect(self.pick_folder)
        b_open.clicked.connect(self.open_folder)
        b_img.clicked.connect(self.pick_image)
        self.refresh()

    def _aerial_toggle(self, *_):
        s = self.a_src.currentData()
        self.a_video.setEnabled(s == "file")
        self.a_after.setEnabled(s != "none")

    def _row(self, key, text, widget):
        lab = QLabel(text)
        self.form.addRow(lab, widget)
        self.rows[key] = (lab, widget)

    def refresh(self):
        m = self.mode.currentData()
        g = "slide" if m == "slideshow" else "main"  # SLIDEDIR2
        lg = getattr(self, "_last_mode", None)
        if lg is not None:
            lgg = "slide" if lg == "slideshow" else "main"
            if lgg != g:
                self.dir_store[lgg] = self.folder.text().strip()
                self.folder.setText(self.dir_store[g])
        self._last_mode = m
        show = {"folder": (m in FOLDER_MODES) and not (m == "slideshow" and self.slidesrc.currentData() == "auto"), "image": m == "static",
                "minutes": m == "slideshow", "times": m == "schedule",
                "fade": m in ("schedule", "sunpath", "slideshow"), "daycount": m == "sunpath",
                "twilight": m == "sunpath", "sun5btn": m == "sunpath",
                "slidesrc": m == "slideshow"}
        for k, (lab, w) in self.rows.items():
            lab.setVisible(show[k])
            w.setVisible(show[k])
        files = []
        secs = None  # SUN5
        if m == "static" and self.image.text().strip():
            files = [Path(self.image.text().strip()).expanduser()]
        elif m in FOLDER_MODES:
            files = list_images(self.folder.text().strip())
            if m == "sunpath":  # SUN5
                secs = sun5_sections(self.folder.text().strip())
                if secs is not None:
                    files = [f for sec in secs for f in sec]
        if m == "slideshow" and self.slidesrc.currentData() == "auto":  # SLIDESRC
            files = auto_slideshow_images(self.dir_store["main"])
        if m == "sunpath":
            for w in self.rows["daycount"]:
                w.setVisible(secs is None)
        if m in FOLDER_MODES:
            msg = t("info_folder", n=len(files))
            if m == "slideshow" and self.slidesrc.currentData() == "auto":
                msg = t("src_info_auto", n=len(files))
            if secs is not None:
                cnt = " / ".join(t("sun5_n%d" % i) + " " + t("sun5_unit", n=len(sec))
                                 for i, sec in enumerate(secs))
                msg = t("sun5_info", c=cnt)
            elif m in ("schedule", "sunpath") and len(files) > 100:
                msg += t("info_over12")
            self.info.setText(msg)
        elif m == "off":
            self.info.setText(t("info_off"))
        else:
            self.info.setText("")
        self.cur_files = list(files)
        self.thumbs.clear()
        for i, f in enumerate(files[:24]):
            pm = thumb(f) if f.exists() else QPixmap()
            self.thumbs.addItem(QListWidgetItem(QIcon(pm), f"{i + 1}. {f.name}"))
        self.thumbs.setVisible(m != "off")

    def make_sun5(self):  # SUN5
        txt = self.folder.text().strip()
        if not txt:
            self.info.setText(t("sun5_nofolder"))
            return
        base = Path(txt).expanduser()
        for n in SUN5_DIRS:
            (base / n).mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(base)])
        self.refresh()

    def toggle_preview(self):
        if getattr(self, "timer", None) and self.timer.isActive():
            self.stop_preview()
        else:
            self.start_preview()

    def start_preview(self):
        m = self.mode.currentData()
        files = [f for f in getattr(self, "cur_files", []) if f.exists()]
        if m in ("schedule", "sunpath"):
            files = files[:100]
        if m == "off" or not files:
            self.info.setText(t("prev_none"))
            return
        if len(files) == 1:
            self.info.setText(t("prev_one"))
            return
        if ACTIVE[0] is not None and ACTIVE[0] is not self:
            ACTIVE[0].stop_preview()
        ACTIVE[0] = self
        self.seq = files * 2
        self.pos = 0
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        if not hasattr(self, "timer"):
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.preview_step)
        self.b_prev.setText(t("prev_stop"))
        self.preview_step()
        self.timer.start(2000)

    def preview_step(self):
        if self.pos >= len(self.seq):
            self.stop_preview()
            return
        LOCK.touch()
        set_wallpaper(self.seq[self.pos])
        self.info.setText(t("prev_run", i=self.pos + 1, n=len(self.seq)))
        self.pos += 1

    def stop_preview(self):
        if getattr(self, "timer", None):
            self.timer.stop()
        self.b_prev.setText(t("preview"))
        if ACTIVE[0] is self:
            ACTIVE[0] = None
            LOCK.unlink(missing_ok=True)
            subprocess.Popen([str(HOME / ".local/bin/timewall.py"), "--force"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.refresh()

    def pick_folder(self):
        d = QFileDialog.getExistingDirectory(
            self, t("dlg_folder"), str(Path(self.folder.text()).expanduser()))
        if d:
            self.folder.setText(d)
            self.refresh()

    def pick_image(self):
        f, _ = QFileDialog.getOpenFileName(
            self, t("dlg_image"), str(HOME / "Pictures"), t("img_filter"))
        if f:
            self.image.setText(f)
            self.refresh()

    def open_folder(self):
        d = Path(self.folder.text().strip()).expanduser()
        d.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(d)])
        self.refresh()

    def get(self):
        m = self.mode.currentData()
        d = {k: v for k, v in self.orig.items()
             if k not in ("mode", "dir", "image", "minutes", "times", "fade", "day_count", "twilight_min", "slideshow_dir", "slideshow_source", "aerial")}
        d["mode"] = m
        # SLIDEDIR2: remember both folders
        _g = "slide" if m == "slideshow" else "main"
        _st = dict(self.dir_store)
        _st[_g] = self.folder.text().strip()
        d["dir"] = _st["main"]
        d["slideshow_dir"] = _st["slide"]
        d["slideshow_source"] = self.slidesrc.currentData()
        if m == "static":
            if not self.image.text().strip():
                raise ValueError(t("err_image", n=self.n))
            d["image"] = self.image.text().strip()
        if m == "slideshow":
            d["minutes"] = self.minutes.value()
        if m == "schedule":
            ts = [x.strip() for x in self.times.text().replace("、", ",").split(",") if x.strip()]
            if not ts or len(ts) > 100:
                raise ValueError(t("err_times_count", n=self.n))
            fixed = []
            for x in ts:
                mt = re.fullmatch(r"(\d{1,2}):(\d{2})", x)
                if not mt or int(mt.group(1)) > 23 or int(mt.group(2)) > 59:
                    raise ValueError(t("err_time_bad", n=self.n, t=x))
                fixed.append(f"{int(mt.group(1)):02d}:{mt.group(2)}")
            d["times"] = sorted(fixed)
        if m in ("schedule", "sunpath", "slideshow"):
            d["fade"] = self.fade.isChecked()
        if m == "sunpath" and self.daycount.value() > 0:
            d["day_count"] = self.daycount.value()
        if m == "sunpath":
            d["twilight_min"] = self.twilight.value()
        a = {"source": self.a_src.currentData(), "after": self.a_after.currentData()}
        v = self.a_video.currentData()
        if a["source"] == "file" and not v:
            raise ValueError(ta("err_video", n=self.n))
        if v:
            a["video"] = v
        d["aerial"] = a
        d["chime"] = self.chime.isChecked()
        return d


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("title"))
        self.resize(760, 900)
        self.cfg = load()
        self.lang_setting = self.cfg.get("language", "auto")

        loc = self.cfg.get("location", "auto")
        if isinstance(loc, dict):
            loc = f'{loc.get("lat")},{loc.get("lon")}'
        self.loc = QLineEdit(str(loc))
        self.loc.setPlaceholderText(t("loc_ph"))
        self.count = QSpinBox()
        self.count.setRange(1, MAX_DESK)
        self.count.setValue(kwin_count())
        b_count = QPushButton(t("change_count"))
        self.hello = QCheckBox(t("hello"))
        self.hello.setChecked(self.cfg.get("hello_sync", False))
        self.hello.setVisible(Path("/usr/local/share/hello-wallpaper.jpg").exists())
        self.paused = QCheckBox(t("paused"))
        self.paused.setChecked(self.cfg.get("paused", False))

        self.langbox = QComboBox()
        self.langbox.addItem(t("lang_auto"), "auto")
        for code, d in STR.items():
            self.langbox.addItem(d["name"], code)
        idx = self.langbox.findData(self.lang_setting)
        self.langbox.setCurrentIndex(idx if idx >= 0 else 0)

        box = QGroupBox(t("g_settings"))
        g = QFormLayout(box)
        g.addRow(t("location"), self.loc)
        cw = QWidget()
        cl = QHBoxLayout(cw)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.count)
        cl.addWidget(b_count)
        cl.addStretch(1)
        g.addRow(t("desk_count"), cw)
        g.addRow(t("language"), self.langbox)
        g.addRow("", self.hello)
        g.addRow("", self.paused)

        self.nb = QTabWidget()
        d = self.cfg.get("desktops", {})
        self.tabs = {n: DeskTab(n, d.get(str(n))) for n in range(1, MAX_DESK + 1)}
        self.show_tabs(kwin_count())

        b_apply = QPushButton(t("apply"))
        b_close = QPushButton(t("close"))
        bl = QHBoxLayout()
        bl.addStretch(1)
        bl.addWidget(b_apply)
        bl.addWidget(b_close)

        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(box)
        lay.addWidget(self.nb, 1)
        lay.addLayout(bl)
        self.setCentralWidget(root)

        b_count.clicked.connect(self.change_count)
        b_apply.clicked.connect(self.apply)
        b_close.clicked.connect(self.close)

    def closeEvent(self, e):
        if ACTIVE[0] is not None:
            ACTIVE[0].stop_preview()
        super().closeEvent(e)

    def show_tabs(self, n):
        self.nb.clear()
        for i in range(1, n + 1):
            self.nb.addTab(self.tabs[i], t("tab", n=i))

    def change_count(self):
        try:
            set_kwin_count(self.count.value())
            self.show_tabs(kwin_count())
            self.statusBar().showMessage(t("count_done", n=kwin_count()), 5000)
        except Exception as e:
            QMessageBox.critical(self, t("count_fail"), str(e))

    def apply(self):
        if ACTIVE[0] is not None:
            ACTIVE[0].stop_preview()
        try:
            cfg = load()
            loc = self.loc.text().strip()
            if re.fullmatch(r"-?\d+(\.\d+)?\s*,\s*-?\d+(\.\d+)?", loc):
                a, b = [float(x) for x in loc.split(",")]
                cfg["location"] = {"lat": a, "lon": b}
            elif loc.lower() == "auto":
                cfg["location"] = "auto"
            else:
                from astral.geocoder import database, lookup
                lookup(loc, database())
                cfg["location"] = loc
            cfg["hello_sync"] = self.hello.isChecked()
            cfg["paused"] = self.paused.isChecked()
            cfg["language"] = self.langbox.currentData()
            ag = cfg.get("aerial", {}) or {}  # AERIAL-UI2
            ag.setdefault("dir", "~/Videos/aerial")
            cfg["aerial"] = ag
            write_inherit(True)
            cfg.setdefault("desktops", {})
            for n in range(1, kwin_count() + 1):
                dd = self.tabs[n].get()
                cfg["desktops"][str(n)] = dd
                if dd.get("dir"):
                    Path(dd["dir"]).expanduser().mkdir(parents=True, exist_ok=True)
                if dd.get("slideshow_dir"):
                    Path(dd["slideshow_dir"]).expanduser().mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, t("input_check"), str(e))
            return
        save(cfg)
        subprocess.run([str(HOME / ".local/bin/timewall.py"), "--force"], capture_output=True)
        changed = cfg["language"] != self.lang_setting
        self.statusBar().showMessage(t("saved_lang") if changed else t("saved"), 6000)


if __name__ == "__main__":
    LANG = detect_lang(load().get("language", "auto"))
    app = QApplication(sys.argv)
    app.setApplicationName("TimeWall")
    icon = HOME / ".local/share/icons/timewall.svg"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    w = Main()
    w.show()
    sys.exit(app.exec())

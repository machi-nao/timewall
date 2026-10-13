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
MAX_DESK = 8
THUMB = QSize(120, 68)

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
        "paused": "全体を一時停止する",
        "language": "言語",
        "lang_auto": "自動(システムに合わせる)",
        "tab": "デスクトップ {n}",
        "apply": "保存して適用",
        "close": "閉じる",
        "mode": "モード",
        "mode_off": "停止(壁紙に触らない)",
        "mode_static": "固定(1枚)",
        "mode_slideshow": "スライドショー",
        "mode_schedule": "時刻指定(最大12枚)",
        "mode_sunpath": "日の出・日の入り連動(最大12枚)",
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
        "day_auto": "自動(昼夜の長さで決める)",
        "info_folder": "フォルダ内の画像: {n}枚(ファイル名の順に使います)",
        "info_over12": " ※使われるのは先頭の12枚までです",
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
        "err_times_count": "デスクトップ{n}: 時刻を1〜12個入れてください",
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
        "mode_schedule": "Time schedule (up to 12 images)",
        "mode_sunpath": "Sunrise / sunset (up to 12 images)",
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
        "day_auto": "Auto (from day/night length)",
        "info_folder": "Images in folder: {n} (used in file name order)",
        "info_over12": " * only the first 12 are used",
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
        "err_times_count": "Desktop {n}: enter 1 to 12 times",
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

        self.folder = QLineEdit(self.orig.get("dir", f"~/Pictures/wp/desktop{n}"))
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
        self.daycount.setRange(0, 12)
        self.daycount.setSpecialValueText(t("day_auto"))
        self.daycount.setValue(int(self.orig.get("day_count", 0)))

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
        self.form.addRow(QLabel(t("mode")), self.mode)
        self._row("folder", t("folder"), fw)
        self._row("image", t("image"), iw)
        self._row("minutes", t("interval"), self.minutes)
        self._row("times", t("times"), self.times)
        self._row("fade", "", self.fade)
        self._row("daycount", t("day_count"), self.daycount)

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

    def _row(self, key, text, widget):
        lab = QLabel(text)
        self.form.addRow(lab, widget)
        self.rows[key] = (lab, widget)

    def refresh(self):
        m = self.mode.currentData()
        show = {"folder": m in FOLDER_MODES, "image": m == "static",
                "minutes": m == "slideshow", "times": m == "schedule",
                "fade": m in ("schedule", "sunpath"), "daycount": m == "sunpath"}
        for k, (lab, w) in self.rows.items():
            lab.setVisible(show[k])
            w.setVisible(show[k])
        files = []
        if m == "static" and self.image.text().strip():
            files = [Path(self.image.text().strip()).expanduser()]
        elif m in FOLDER_MODES:
            files = list_images(self.folder.text().strip())
        if m in FOLDER_MODES:
            msg = t("info_folder", n=len(files))
            if m in ("schedule", "sunpath") and len(files) > 12:
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

    def toggle_preview(self):
        if getattr(self, "timer", None) and self.timer.isActive():
            self.stop_preview()
        else:
            self.start_preview()

    def start_preview(self):
        m = self.mode.currentData()
        files = [f for f in getattr(self, "cur_files", []) if f.exists()]
        if m in ("schedule", "sunpath"):
            files = files[:12]
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
        d = {"mode": m}
        if m in FOLDER_MODES:
            d["dir"] = self.folder.text().strip()
        if m == "static":
            if not self.image.text().strip():
                raise ValueError(t("err_image", n=self.n))
            d["image"] = self.image.text().strip()
        if m == "slideshow":
            d["minutes"] = self.minutes.value()
        if m == "schedule":
            ts = [x.strip() for x in self.times.text().replace("、", ",").split(",") if x.strip()]
            if not ts or len(ts) > 12:
                raise ValueError(t("err_times_count", n=self.n))
            fixed = []
            for x in ts:
                mt = re.fullmatch(r"(\d{1,2}):(\d{2})", x)
                if not mt or int(mt.group(1)) > 23 or int(mt.group(2)) > 59:
                    raise ValueError(t("err_time_bad", n=self.n, t=x))
                fixed.append(f"{int(mt.group(1)):02d}:{mt.group(2)}")
            d["times"] = sorted(fixed)
        if m in ("schedule", "sunpath"):
            d["fade"] = self.fade.isChecked()
        if m == "sunpath" and self.daycount.value() > 0:
            d["day_count"] = self.daycount.value()
        return d


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(t("title"))
        self.resize(760, 640)
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
            cfg.setdefault("desktops", {})
            for n in range(1, kwin_count() + 1):
                dd = self.tabs[n].get()
                cfg["desktops"][str(n)] = dd
                if dd.get("dir"):
                    Path(dd["dir"]).expanduser().mkdir(parents=True, exist_ok=True)
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

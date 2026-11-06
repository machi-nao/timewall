#!/usr/bin/env python3
import hashlib, json, shutil, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path
from astral import Observer
from astral.geocoder import database, lookup
from astral.sun import sun

HOME = Path.home()
CACHE = HOME / ".cache/timewall"
CACHE.mkdir(parents=True, exist_ok=True)
import fcntl  # SUN5c: run one instance at a time
_runlock = open(CACHE / "run.lock", "w")
fcntl.flock(_runlock, fcntl.LOCK_EX)
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
HELLO = "/usr/local/share/hello-wallpaper.jpg"
# AERIAL-HOOK
LOCKFRAME = HOME / ".cache/lockframe.png"
FRAMES = CACHE / "frames"
OVERRIDE = CACHE / "override.json"
HOLD_SEC = 600     # 最低10分は引き継ぎを保持
MAX_SEC = 86400    # 最長24時間
MAXN = 100  # SUN5: max images per folder

cfg = json.load(open(HOME / ".config/timewall.json"))
paused = bool(cfg.get("paused"))  # AERIAL-PAUSE
_lock = CACHE / "preview.lock"
if _lock.exists() and time.time() - _lock.stat().st_mtime < 120:
    print("timewall: preview running")
    sys.exit(0)

now = datetime.now().astimezone()
args = [a for a in sys.argv[1:] if not a.startswith("--")]
force_apply = "--force" in sys.argv
forced = args[0] if args else None
# テスト: timewall.py 17:30 で時刻指定 / timewall.py night で旧モードの時間帯指定
if forced and ":" in forced:
    h, mi = forced.split(":")
    now = now.replace(hour=int(h), minute=int(mi), second=0, microsecond=0)
    forced = None
    force_apply = True

def tz_observer():
    import re
    r = subprocess.run(["timedatectl", "show", "-p", "Timezone", "--value"],
                       capture_output=True, text=True)
    tz = r.stdout.strip() or "Asia/Tokyo"
    for tab in ("zone1970.tab", "zone.tab"):
        try:
            for line in open("/usr/share/zoneinfo/" + tab):
                c = line.rstrip("\n").split("\t")
                if not line.startswith("#") and len(c) >= 3 and c[2] == tz:
                    m = re.fullmatch(r"([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?", c[1])
                    if m:
                        g = m.groups()
                        lat = int(g[1]) + int(g[2]) / 60 + int(g[3] or 0) / 3600
                        lon = int(g[5]) + int(g[6]) / 60 + int(g[7] or 0) / 3600
                        return Observer(-lat if g[0] == "-" else lat, -lon if g[4] == "-" else lon)
        except OSError:
            pass
    return lookup("Tokyo", database()).observer

def get_observer():
    loc = cfg["location"]
    if isinstance(loc, str):
        if loc.lower() == "auto":
            return tz_observer()
        return lookup(loc, database()).observer
    return Observer(loc["lat"], loc["lon"])

def list_images(d):
    if not d.is_dir():
        return []
    return sorted((f for f in d.iterdir() if f.suffix.lower() in EXTS),
                  key=lambda f: f.name.lower())

def blend(a, b, step):
    if step <= 0:
        return a
    if step >= 20:
        return b
    from PIL import Image
    key = hashlib.md5(f"{a}|{a.stat().st_mtime_ns}|{b}|{b.stat().st_mtime_ns}|{step}".encode()).hexdigest()[:16]
    out = CACHE / f"mix-{key}.jpg"
    if not out.exists():
        A = Image.open(a).convert("RGB")
        B = Image.open(b).convert("RGB").resize(A.size)
        Image.blend(A, B, step / 20).save(out, quality=92)
    return out

def pick(segs, fade):
    segs.sort(key=lambda x: x[0])
    cur = None
    for i, (t, _) in enumerate(segs):
        if t <= now:
            cur = i
    if cur is None or cur + 1 >= len(segs):
        return segs[0][1]
    t0, a = segs[cur]
    t1, b = segs[cur + 1]
    if fade and a != b:
        fw = min(timedelta(minutes=30), (t1 - t0) / 3)
        ft = t1 - fw
        if now >= ft:
            return blend(a, b, round((now - ft) / fw * 20))
    return a

def segs_schedule(imgs, times):
    n = min(len(imgs), len(times))
    pairs = list(zip(sorted(times)[:n], imgs[:n]))
    segs = []
    for k in (-1, 0, 1):
        d = now.date() + timedelta(days=k)
        for hm, img in pairs:
            h, m = map(int, hm.split(":"))
            segs.append((datetime(d.year, d.month, d.day, h, m, tzinfo=now.tzinfo), img))
    return segs

def segs_sun(imgs, day_count):
    obs = get_observer()
    n = len(imgs)
    suns = {k: sun(obs, date=now.date() + timedelta(days=k), tzinfo=now.tzinfo) for k in (-1, 0, 1, 2)}
    if day_count is None:
        ratio = (suns[0]["sunset"] - suns[0]["sunrise"]) / timedelta(hours=24)
        dc = round(n * ratio)
        dc = max(1, min(n - 1, dc)) if n >= 2 else n
    else:
        dc = max(1, min(n, int(day_count)))
    nc = n - dc
    segs = []
    for k in (-1, 0, 1):
        rise, sset, nxt = suns[k]["sunrise"], suns[k]["sunset"], suns[k + 1]["sunrise"]
        for j in range(dc):
            segs.append((rise + (sset - rise) * j / dc, imgs[j]))
        for j in range(nc):
            segs.append((sset + (nxt - sset) * j / nc, imgs[dc + j]))
    return segs

SUN_DIRS = ["1_before_sunrise", "2_sunrise", "3_day", "4_sunset", "5_after_sunset"]  # SUN5

def sun_sections(d):
    # サブフォルダが1つでもあれば新方式(5区間)。なければ None(従来方式)
    if not any((d / n).is_dir() for n in SUN_DIRS):
        return None
    secs = [list_images(d / n)[:MAXN] for n in SUN_DIRS]  # SUN5b
    if not any(secs):
        return None  # all empty: fall back to legacy (images in the folder itself)
    return secs

def segs_sun5(sec, tw_min):
    obs = get_observer()
    W = timedelta(minutes=max(0, min(120, tw_min)))
    segs = []
    for k in (-1, 0, 1):
        day = now.date() + timedelta(days=k)
        mid0 = datetime(day.year, day.month, day.day, tzinfo=now.tzinfo)
        mid1 = mid0 + timedelta(days=1)
        sn = sun(obs, date=day, tzinfo=now.tzinfo)
        rise, sset = sn["sunrise"], sn["sunset"]
        bounds = [mid0, rise - W, rise + W, sset - W, sset + W, mid1]
        for i, imgs in enumerate(sec):
            t0, t1 = bounds[i], bounds[i + 1]
            n = len(imgs)
            for j in range(n):
                segs.append((t0 + (t1 - t0) * j / n, imgs[j]))
    return segs

def slideshow_images(s, desk, d):  # SLIDESRC
    if (s.get("slideshow_source") or "auto") == "manual":
        sd = Path(s.get("slideshow_dir") or f"~/Pictures/wp/desktop{desk}-slideshow").expanduser()
        return list_images(sd)
    base = Path(s.get("dir") or f"~/Pictures/wp/desktop{desk}").expanduser()
    out, seen = [], set()
    for folder in [base] + [base / n for n in SUN_DIRS]:
        for f in list_images(folder):
            try:
                key = (f.name.lower(), f.stat().st_size)
            except OSError:
                continue
            if key not in seen:
                seen.add(key)
                out.append(f)
    return out

def segs_slideshow(imgs, minutes):  # SLIDEFADE
    k0 = int(now.timestamp() // 60 // minutes)
    segs = []
    for k in range(k0 - 1, k0 + 3):
        t = datetime.fromtimestamp(k * minutes * 60, tz=now.tzinfo)
        segs.append((t, imgs[k % len(imgs)]))
    return segs

# ---- 今のデスクトップ ----
out = subprocess.run(["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.currentDesktop"],
                     capture_output=True, text=True).stdout.strip()
desk = out if out else "1"
try:  # SLIDEDIR: make ~/Pictures/wp/desktopN-slideshow for this desktop
    (HOME / "Pictures/wp" / f"desktop{desk}-slideshow").mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# ---- Aerial: このデスクトップで流す動画を、固定のパスにつなぐ ----  # AERIAL-VIDEO
def update_aerial(desk):
    import os, random
    g = cfg.get("aerial", {})
    ds = cfg["desktops"].get(desk, {}).get("aerial", {})
    adir = Path(g.get("dir", "~/Videos/aerial")).expanduser()
    link = HOME / ".cache/aerial/current.mp4"
    link.parent.mkdir(parents=True, exist_ok=True)
    exts = (".mp4", ".webm", ".mkv", ".mov")
    vids = sorted(p for p in adir.iterdir() if p.suffix.lower() in exts) if adir.is_dir() else []
    def rnd():
        return random.choice(vids) if vids else None
    def default():
        if g.get("mode", "same") == "random":
            return rnd()
        v = g.get("video")
        if v:
            return Path(v).expanduser()
        return vids[0] if vids else None
    mode = ds.get("source", "default")
    if mode == "none" or not ds.get("use", True):  # AERIAL-UI2
        target = None
    elif mode == "file":
        target = Path(ds.get("video", "")).expanduser()
    elif mode == "random":
        target = rnd()
    else:
        target = default()
    try:
        if target and target.is_file():
            tmp = link.with_name("current.tmp")
            if tmp.is_symlink() or tmp.exists():
                tmp.unlink()
            tmp.symlink_to(target)
            os.replace(tmp, link)
        else:
            link.unlink(missing_ok=True)
    except Exception as e:
        print("aerial link skipped:", e)

update_aerial(desk)

if paused and "--lockframe" not in sys.argv:
    print("timewall: paused (Aerial keeps working)")
    sys.exit(0)
s = cfg["desktops"].get(desk)
if not s or s.get("mode", "off") == "off":
    print("desktop", desk, "is off; nothing to do")
    sys.exit(0)

mode = s["mode"]
if mode == "slideshow":  # SLIDEDIR2: slideshow has its own folder
    d = Path(s.get("slideshow_dir") or s.get("dir") or f"~/Pictures/wp/desktop{desk}-slideshow").expanduser()
else:
    d = Path(s.get("dir") or f"~/Pictures/wp/desktop{desk}").expanduser()
p = None
slot = mode

if mode == "static":
    p = Path(s["image"]).expanduser()
elif mode == "slideshow":
    imgs = slideshow_images(s, desk, d)
    if imgs:
        minutes = max(3, min(60, int(s.get("minutes", 10))))
        p = pick(segs_slideshow(imgs, minutes), s.get("fade", False))  # SLIDEFADE
elif mode == "schedule":
    imgs = list_images(d)[:MAXN]
    times = s.get("times", [])[:MAXN]
    if imgs and times:
        p = pick(segs_schedule(imgs, times), s.get("fade", False))
elif mode == "sunpath":
    sec = sun_sections(d)  # SUN5
    if sec is not None:
        segs = segs_sun5(sec, int(s.get("twilight_min", 30)))
        if segs:
            p = pick(segs, s.get("fade", False))
    else:
        imgs = list_images(d)[:MAXN]
        if imgs:
            p = pick(segs_sun(imgs, s.get("day_count")), s.get("fade", False))
else:
    print("desktop", desk, "unknown mode:", mode)
    sys.exit(0)

if not p or not Path(p).exists():
    print("image not found for desktop", desk, slot)
    sys.exit(1)

p = Path(p)

# ---- Aerial: ロック解除時のフレームを引き継ぐ ----
base = str(p)
if "--lockframe" in sys.argv:
    _ao = s.get("aerial", {}) or {}
    if _ao.get("after", "frame") == "timewall" or _ao.get("source") == "none" or _ao.get("use") is False:
        LOCKFRAME.unlink(missing_ok=True)
        print("timewall: this desktop keeps the timewall image after unlock")
        sys.exit(0)
    if LOCKFRAME.exists() and LOCKFRAME.stat().st_size > 10000:
        FRAMES.mkdir(parents=True, exist_ok=True)
        dst = FRAMES / f"lock-{int(time.time())}.png"
        shutil.move(str(LOCKFRAME), str(dst))
        OVERRIDE.write_text(json.dumps({"desk": desk, "base": base, "image": str(dst), "created": time.time()}))
        for old in sorted(FRAMES.glob("lock-*.png"))[:-5]:
            old.unlink()
        p = dst
        slot = "lockframe"
        force_apply = True
    else:
        print("timewall: no lockframe")
        sys.exit(0)
else:
    try:
        ov = json.loads(OVERRIDE.read_text())
    except Exception:
        ov = None
    if ov and ov.get("desk") == desk:
        age = time.time() - ov.get("created", 0)
        if Path(ov.get("image", "")).exists() and age < MAX_SEC and (age < HOLD_SEC or ov.get("base") == base) and (s.get("aerial", {}) or {}).get("after", "frame") != "timewall":
            p = Path(ov["image"])
            slot = "lockframe"
        else:
            OVERRIDE.unlink(missing_ok=True)

state = CACHE / "last_applied"
if not force_apply and state.exists() and state.read_text() == str(p):
    print("desktop", desk, "unchanged", p.name)
    sys.exit(0)
print("desktop", desk, "slot", slot, p)

if cfg.get("hello_sync", False) and Path(HELLO).exists():
    try:
        if p.suffix.lower() in (".jpg", ".jpeg"):
            shutil.copyfile(p, HELLO)
        else:
            from PIL import Image
            Image.open(p).convert("RGB").save(HELLO, "JPEG", quality=92)
    except Exception as e:
        print("hello sync skipped:", e)

try:
    lg = CACHE / "run.log"
    if lg.exists() and lg.stat().st_size > 200000:
        lg.write_text("")
    with open(lg, "a") as lf:
        lf.write(f"{datetime.now():%m-%d %H:%M:%S} desk={desk} mode={slot} img={p.name}\n")
except Exception:
    pass

js = f"""
var img = "file://{p}";
desktops().forEach(function(d) {{
  if (d.screen < 0) return;
  d.wallpaperPlugin = "org.kde.image";
  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
  d.writeConfig("Image", img);
}});
"""
# SUN5c: wait for plasmashell, retry, and record "applied" only after success
_ok = False
for _i in range(30):
    _r = subprocess.run(["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
                         "org.kde.PlasmaShell.evaluateScript", js],
                        capture_output=True, text=True)
    if _r.returncode == 0 and "Cannot find" not in _r.stderr and "does not exist" not in _r.stderr:
        _ok = True
        break
    time.sleep(2)
if _ok:
    state.write_text(str(p))
else:
    print("timewall: plasmashell not ready; will retry next run")
    sys.exit(1)

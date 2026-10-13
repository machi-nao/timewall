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
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
HELLO = "/usr/local/share/hello-wallpaper.jpg"

cfg = json.load(open(HOME / ".config/timewall.json"))
if cfg.get("paused"):
    print("timewall: paused")
    sys.exit(0)
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

# ---- 今のデスクトップ ----
out = subprocess.run(["qdbus6", "org.kde.KWin", "/KWin", "org.kde.KWin.currentDesktop"],
                     capture_output=True, text=True).stdout.strip()
desk = out if out else "1"
s = cfg["desktops"].get(desk)
if not s or s.get("mode", "off") == "off":
    print("desktop", desk, "is off; nothing to do")
    sys.exit(0)

mode = s["mode"]
d = Path(s.get("dir") or f"~/Pictures/wp/desktop{desk}").expanduser()
p = None
slot = mode

if mode == "static":
    p = Path(s["image"]).expanduser()
elif mode == "slideshow":
    imgs = list_images(d)
    if imgs:
        minutes = max(3, min(60, int(s.get("minutes", 10))))
        p = imgs[int(now.timestamp() // 60 // minutes) % len(imgs)]
elif mode == "schedule":
    imgs = list_images(d)[:12]
    times = s.get("times", [])[:12]
    if imgs and times:
        p = pick(segs_schedule(imgs, times), s.get("fade", False))
elif mode == "sunpath":
    imgs = list_images(d)[:12]
    if imgs:
        p = pick(segs_sun(imgs, s.get("day_count")), s.get("fade", False))
else:
    print("desktop", desk, "unknown mode:", mode)
    sys.exit(0)

if not p or not Path(p).exists():
    print("image not found for desktop", desk, slot)
    sys.exit(1)

p = Path(p)
state = CACHE / "last_applied"
if not force_apply and state.exists() and state.read_text() == str(p):
    print("desktop", desk, "unchanged", p.name)
    sys.exit(0)
state.write_text(str(p))
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
subprocess.run(["qdbus6", "org.kde.plasmashell", "/PlasmaShell",
                "org.kde.PlasmaShell.evaluateScript", js])

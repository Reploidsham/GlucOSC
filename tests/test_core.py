import hashlib
import json
import socket
import struct
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import glucose_osc_bridge as g  # noqa: E402

FAILS = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if (extra and not cond) else ""))
    if not cond:
        FAILS.append(name)


def read_str(data, i):
    end = data.index(b"\0", i)
    return data[i:end].decode(), (end // 4 + 1) * 4


def decode(data):
    addr, i = read_str(data, 0)
    tags, i = read_str(data, i)
    tag = tags[1:]
    if tag == "i":
        return addr, struct.unpack(">i", data[i:i + 4])[0]
    if tag == "f":
        return addr, struct.unpack(">f", data[i:i + 4])[0]
    if tag == "T":
        return addr, True
    if tag == "F":
        return addr, False
    raise ValueError(tags)


# ---------- encoder known bytes ----------
check("osc int bytes", g.osc_message("/a", 1) == b"/a\0\0,i\0\0\0\0\0\1")
check("osc true bytes", g.osc_message("/a", True) == b"/a\0\0,T\0\0")
check("osc false bytes", g.osc_message("/a", False) == b"/a\0\0,F\0\0")
check("osc float bytes", g.osc_message("/abc", 0.5) == b"/abc\0\0\0\0,f\0\0" + struct.pack(">f", 0.5))

# ---------- digit layout (pure logic) ----------
B = g.BLANK
check("mmol 5.6 -> blank,5,6", g.digits_for(5.6, "mmol/L") == (B, 5, 6), g.digits_for(5.6, "mmol/L"))
check("mmol 12.4 -> 1,2,4", g.digits_for(12.4, "mmol/L") == (1, 2, 4))
check("mmol 10.0 -> 1,0,0", g.digits_for(10.0, "mmol/L") == (1, 0, 0))
check("mmol 9.95 rounds half up -> 1,0,0", g.digits_for(9.95, "mmol/L") == (1, 0, 0), g.digits_for(9.95, "mmol/L"))
check("mmol 0.4 -> blank,0,4", g.digits_for(0.4, "mmol/L") == (B, 0, 4))
check("mmol 33.3 -> 3,3,3", g.digits_for(33.3, "mmol/L") == (3, 3, 3))
check("mmol clamps at 99.9", g.digits_for(150.0, "mmol/L") == (9, 9, 9))
check("mgdl 112 -> 1,1,2", g.digits_for(112 / g.MGDL_PER_MMOL, "mg/dL") == (1, 1, 2))
check("mgdl 95 -> blank,9,5", g.digits_for(95 / g.MGDL_PER_MMOL, "mg/dL") == (B, 9, 5))
check("mgdl 7 -> blank,blank,7", g.digits_for(7 / g.MGDL_PER_MMOL, "mg/dL") == (B, B, 7))
check("mgdl 400 -> 4,0,0", g.digits_for(400 / g.MGDL_PER_MMOL, "mg/dL") == (4, 0, 0))
check("every integer mg/dL 20..600 round-trips",
      all((lambda d: (0 if d[0] == B else d[0]) * 100 + (0 if d[1] == B else d[1]) * 10 + d[2] == v)(
          g.digits_for(v / g.MGDL_PER_MMOL, "mg/dL")) for v in range(20, 601) if v <= 999))
check("format mmol", g.format_value(5.62, "mmol/L") == "5.6")
check("format mgdl", g.format_value(112 / g.MGDL_PER_MMOL, "mg/dL") == "112")

# ---------- state tags ----------
st = g.Settings()
lo, hi, ok = g.Reading(3.5, time.time(), 3), g.Reading(11.0, time.time(), 3), g.Reading(6.0, time.time(), 3)
check("tag LO", g.state_tag(lo, st, False) == "LO")
check("tag HI", g.state_tag(hi, st, False) == "HI")
check("tag none in range", g.state_tag(ok, st, False) == "")
check("tag -- when stale", g.state_tag(ok, st, True) == "--")
check("tag -- when no reading", g.state_tag(None, st, False) == "--")
check("exactly 4.0 is not low", g.build_params(g.Reading(4.0, time.time(), 3), st)[5][1] is False)
check("exactly 10.0 is not high", g.build_params(g.Reading(10.0, time.time(), 3), st)[6][1] is False)

# ---------- param list shape ----------
names = [n for n, _ in g.build_params(ok, st)]
check("10 params, expected names", names == ["BG_D1", "BG_D2", "BG_D3", "BG_Trend", "BG_Stale", "BG_Low",
                                             "BG_High", "BG_Mgdl", "BG_Beat", "BG_Words"], names)
check("no BG_Lang any more (bridge does not drive language)", "BG_Lang" not in names)
check("no old BG_Tenths / BG_Norm", "BG_Tenths" not in names and "BG_Norm" not in names)
check("no float params (sync cost)", all(not isinstance(v, float) for _, v in g.build_params(ok, st)))

# ---------- mock xDrip+ ----------
STATE = {"body": [], "secret": ""}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if STATE["secret"]:
            want = hashlib.sha1(STATE["secret"].encode()).hexdigest()
            if self.headers.get("api-secret") != want:
                self.send_response(401)
                self.end_headers()
                return
        body = json.dumps(STATE["body"]).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(("127.0.0.1", 0))
udp.settimeout(1.0)

s = g.Settings(phone_host="127.0.0.1", phone_port=server.server_address[1], osc_host="127.0.0.1",
               osc_port=udp.getsockname()[1])


def ms(minutes_ago):
    return int((time.time() - minutes_ago * 60) * 1000)


def collect(n=10):
    got = {}
    for _ in range(n):
        addr, val = decode(udp.recvfrom(512)[0])
        got[addr.rsplit("/", 1)[1]] = val
    return got


def send_and_collect(reading, settings=None, beat=False):
    settings = settings or s
    client = g.OscClient(settings.osc_host, settings.osc_port)
    params = g.build_params(reading, settings, beat=beat)
    client.send_all(params)
    client.close()
    return collect(len(params))


def poll():
    return g.parse_sgv(g.fetch_sgv(s), s.units)


# 1. normal mg/dL reading, direction given
STATE["body"] = [{"date": ms(2), "sgv": 112, "direction": "FortyFiveUp"}, {"date": ms(7), "sgv": 105}]
got = send_and_collect(poll())
check("112 mg/dL as mmol -> 6.2 (B,6,2)", (got["BG_D1"], got["BG_D2"], got["BG_D3"]) == (B, 6, 2), got)
check("FortyFiveUp -> trend 2", got["BG_Trend"] == 2, got)
check("fresh not stale", got["BG_Stale"] is False, got)
check("in range not low/high", got["BG_Low"] is False and got["BG_High"] is False, got)
check("mgdl flag false in mmol mode", got["BG_Mgdl"] is False, got)

# 2. same reading shown in mg/dL
s_mg = g.Settings(**{**s.__dict__, "display_units": "mg/dL"})
got = send_and_collect(poll(), s_mg)
check("mg/dL display -> 1,1,2", (got["BG_D1"], got["BG_D2"], got["BG_D3"]) == (1, 1, 2), got)
check("mgdl flag true in mg/dL mode", got["BG_Mgdl"] is True, got)

# 3. low / high
STATE["body"] = [{"date": ms(1), "sgv": 61, "direction": "SingleDown"}]
got = send_and_collect(poll())
check("61 mg/dL -> 3.4 low", (got["BG_D2"], got["BG_D3"]) == (3, 4) and got["BG_Low"] is True and got["BG_High"] is False, got)
check("SingleDown -> trend 5", got["BG_Trend"] == 5, got)
STATE["body"] = [{"date": ms(1), "sgv": 216, "direction": "Flat"}]
got = send_and_collect(poll())
check("216 mg/dL -> 12.0 high", (got["BG_D1"], got["BG_D2"], got["BG_D3"]) == (1, 2, 0) and got["BG_High"] is True, got)

# 4. already-mmol input
STATE["body"] = [{"date": ms(1), "sgv": 5.8, "direction": "Flat"}]
got = send_and_collect(poll())
check("5.8 mmol/L auto -> B,5,8", (got["BG_D1"], got["BG_D2"], got["BG_D3"]) == (B, 5, 8), got)

# 5. stale keeps digits but flags stale
STATE["body"] = [{"date": ms(30), "sgv": 112, "direction": "Flat"}]
got = send_and_collect(poll())
check("30 min old -> stale, digits kept", got["BG_Stale"] is True and got["BG_D2"] == 6, got)

# 6. trend fallbacks
STATE["body"] = [{"date": ms(1), "sgv": 108}, {"date": ms(6), "sgv": 90}]
check("slope fast rise -> 1", send_and_collect(poll())["BG_Trend"] == 1)
STATE["body"] = [{"date": ms(1), "sgv": 90}, {"date": ms(6), "sgv": 108}]
check("slope fast fall -> 5", send_and_collect(poll())["BG_Trend"] == 5)
STATE["body"] = [{"date": ms(1), "sgv": 100}, {"date": ms(6), "sgv": 101}]
check("slope flat -> 3", send_and_collect(poll())["BG_Trend"] == 3)
STATE["body"] = [{"date": ms(1), "sgv": 100, "direction": "NOT COMPUTABLE"}]
check("unknown direction -> 0", send_and_collect(poll())["BG_Trend"] == 0)

# 7. newest wins
STATE["body"] = [{"date": ms(20), "sgv": 200}, {"date": ms(1), "sgv": 100, "direction": "Flat"}]
check("newest entry chosen", abs(poll().mmol - 100 / 18.0156) < 1e-6)

# 8. no reading -> blank + stale, units flag still honoured
got = send_and_collect(None)
check("no reading: blank digits + stale", (got["BG_D1"], got["BG_D2"], got["BG_D3"]) == (B, B, B) and got["BG_Stale"] is True, got)
check("no reading: low/high false", got["BG_Low"] is False and got["BG_High"] is False, got)
got = send_and_collect(None, s_mg)
check("no reading mg/dL flag", got["BG_Mgdl"] is True, got)

# 9. heartbeat value is passed through
check("beat True sent", send_and_collect(ok, beat=True)["BG_Beat"] is True)
check("beat False sent", send_and_collect(ok, beat=False)["BG_Beat"] is False)

# 10. junk responses
STATE["body"] = []
check("empty list -> None", poll() is None)
STATE["body"] = [{"foo": 1}, {"sgv": "x"}]
check("junk entries -> None", poll() is None)

# 11. secret header
STATE["secret"] = "hunter2"
STATE["body"] = [{"date": ms(1), "sgv": 112, "direction": "Flat"}]
s.secret = "hunter2"
check("correct secret accepted", poll() is not None)
s.secret = "wrong"
try:
    poll()
    check("wrong secret rejected", False)
except Exception:
    check("wrong secret rejected", True)
s.secret = ""
try:
    poll()
    check("missing secret rejected", False)
except Exception:
    check("missing secret rejected", True)
STATE["secret"] = ""

# 12. unreachable
try:
    g.fetch_sgv(g.Settings(phone_host="127.0.0.1", phone_port=1), timeout=1.0)
    check("unreachable raises", False)
except Exception:
    check("unreachable raises", True)

# 13. custom names
s2 = g.Settings(p_d1="/avatar/parameters/Glu", p_trend="GluTrend")
c = g.OscClient("127.0.0.1", udp.getsockname()[1])
c.send(s2.p_d1, 5)
c.send(s2.p_trend, 3)
a1, a2 = decode(udp.recvfrom(512)[0]), decode(udp.recvfrom(512)[0])
c.close()
check("full path as-is", a1 == ("/avatar/parameters/Glu", 5), a1)
check("short name gets prefix", a2 == ("/avatar/parameters/GluTrend", 3), a2)

# 14. CLI --once end to end (mg/dL display)
STATE["body"] = [{"date": ms(1), "sgv": 126, "direction": "Flat"}]
s_cli = g.Settings(**{**s.__dict__, "display_units": "mg/dL"})
rc = g.run_cli(s_cli, once=True)
pk = collect()
check("cli --once exit 0, 126 mg/dL digits", rc == 0 and (pk["BG_D1"], pk["BG_D2"], pk["BG_D3"]) == (1, 2, 6), (rc, pk))
check("cli --once heartbeat flips to True on first send", pk["BG_Beat"] is True, pk)
STATE["body"] = []
rc = g.run_cli(s, once=True)
collect()
check("cli --once with no reading exits 1", rc == 1, rc)

# 15. CLI loop: heartbeat alternates each cycle, final 'stopped' packet is stale + blank
import itertools  # noqa: E402

real_sleep = g.time.sleep
cycles = {"n": 0}


def fake_sleep(_):
    cycles["n"] += 1
    if cycles["n"] >= 3:
        raise KeyboardInterrupt


g.time.sleep = fake_sleep
STATE["body"] = [{"date": ms(1), "sgv": 126, "direction": "Flat"}]
g.run_cli(s, once=False)
g.time.sleep = real_sleep
beats, last = [], None
for _ in range(3):
    beats.append(collect()["BG_Beat"])
final = collect()
check("heartbeat alternates True/False/True", beats == [True, False, True], beats)
check("on exit: stale + blank sent", final["BG_Stale"] is True and final["BG_D1"] == B and final["BG_D3"] == B, final)
check("on exit: heartbeat flipped once more (False)", final["BG_Beat"] is False, final)


# ---- languages
check("auto lang from env C -> en", g.resolve_ui_language("auto") == "en")
check("ui lang fr kept", g.resolve_ui_language("fr") == "fr")
check("ui lang zh-Hant has its own translation", g.resolve_ui_language("zh-Hant") == "zh-Hant")
check("ui langs are the 10 panel langs in the same order", g.UI_LANGS == ['en', 'fr', 'es', 'de', 'ja', 'zh-Hans', 'zh-Hant', 'ko', 'pt-BR', 'ru'])
check("unknown language falls back to English", g.resolve_ui_language("it") == "en")
check("pt falls to pt-BR", g.resolve_ui_language("pt") == "pt-BR")
check("other zh variants go to Simplified", g.resolve_ui_language("zh") == "zh-Hans")
check("Traditional text differs from Simplified", g.APP_STRINGS["zh-Hant"]["stopped"] != g.APP_STRINGS["zh-Hans"]["stopped"] or g.APP_STRINGS["zh-Hant"]["unreachable"] != g.APP_STRINGS["zh-Hans"]["unreachable"])
check("every translation is non-empty and not just the English copy (except names)",
      all(g.APP_STRINGS[c][k].strip() and (g.APP_STRINGS[c][k] != g.APP_STRINGS["en"][k] or k in ("window_title", "group_osc", "port"))
          for c in ("zh-Hant", "ko", "pt-BR", "ru") for k in g.APP_STRINGS["en"] if k not in ("window_title", "group_osc", "port", "secret")), "")
check("unknown ui lang -> en", g.resolve_ui_language("xx") == "en")
for code in g.UI_LANGS:
    miss = set(g.APP_STRINGS["en"]) - set(g.APP_STRINGS[code])
    check(f"ui strings complete for {code}", not miss, miss)
check("placeholders survive translation", all(("{host}" in g.APP_STRINGS[c]["started"] and "{err}" in g.APP_STRINGS[c]["unreachable"]
      and "{value}" in g.APP_STRINGS[c]["sent_test"] and "{age}" in g.APP_STRINGS[c]["reading_age"]) for c in g.UI_LANGS))
check("tr formats", g.tr("fr", "unreachable", err="x") == "Impossible de joindre xDrip+ : x")
check("tr falls back to English", g.tr("xx", "start") == "Start")
# ---- rotate mode: mmol/L, mg/dL, words, 10 s each
sr = g.Settings(display_units="rotate", rotate_seconds=10)
seq = []
for t in (0, 5, 10, 15, 20, 25, 30, 45):
    p = dict(g.build_params(ok, sr, now=float(t)))
    seq.append((g.display_phase(sr, float(t)), p["BG_Mgdl"], p["BG_Words"]))
check("rotate phases mmol, mg/dL, words, mmol", [x[0] for x in seq] == ["mmol/L", "mmol/L", "mg/dL", "mg/dL", "words", "words", "mmol/L", "mg/dL"], seq)
check("BG_Mgdl true only in the mg/dL phase", [x[1] for x in seq] == [False, False, True, True, False, False, False, True], seq)
check("BG_Words true only in the words phase", [x[2] for x in seq] == [False, False, False, False, True, True, False, False], seq)
check("words phase keeps real digits (mmol)", dict(g.build_params(ok, sr, now=20.0))["BG_D2"] == dict(g.build_params(ok, sr, now=0.0))["BG_D2"])
for mode in ("mmol/L", "mg/dL", "alternate"):
    sm = g.Settings(display_units=mode)
    check(f"BG_Words never true in {mode}", all(dict(g.build_params(ok, sm, now=float(t)))["BG_Words"] is False for t in range(0, 60, 5)))
check("rotate_seconds respected", g.display_phase(g.Settings(display_units="rotate", rotate_seconds=5), 5.0) == "mg/dL")
check("alternate unchanged (15 s)", g.effective_units(g.Settings(display_units="alternate"), 0.0) == "mmol/L" and g.effective_units(g.Settings(display_units="alternate"), 15.0) == "mg/dL")

print()
print("FAILURES:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)

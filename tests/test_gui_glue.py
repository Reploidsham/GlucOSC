"""Smoke-test the window logic with a hand-made stand-in for PySide6.

This checks MY glue code (form collection, start/stop, polling, display text,
packets sent). It does NOT prove the real Qt API calls are right.
"""
import json
import os
os.environ['LC_ALL'] = 'C'
import socket
import struct
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, HTTPServer


# ---------------- fake PySide6 ----------------
class FakeBoundSignal:
    def __init__(self):
        self.slots = []

    def connect(self, f):
        self.slots.append(f)

    def emit(self, *a):
        for f in list(self.slots):
            f(*a)


class Signal:
    def __init__(self, *types_):
        pass

    def __set_name__(self, owner, name):
        self.name = "_sig_" + name

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        if self.name not in obj.__dict__:
            obj.__dict__[self.name] = FakeBoundSignal()
        return obj.__dict__[self.name]


class Loose:
    """Accepts any method call and ignores it."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: Loose()


class QObject(Loose):
    pass


class QRunnable(Loose):
    pass


class QSettings(Loose):
    def value(self, key, default=None):
        return default

    def setValue(self, key, value):
        pass


class _Pool:
    def start(self, task):
        task.run()  # synchronous


class QThreadPool:
    @staticmethod
    def globalInstance():
        return _Pool()


class QTimer(Loose):
    def __init__(self, *a):
        self.timeout = FakeBoundSignal()
        self.active = False

    def start(self, *a):
        self.active = True

    def stop(self):
        self.active = False


class Qt:
    AlignCenter = 0


class QWidget(Loose):
    pass


class QLabel(Loose):
    def __init__(self, text="", *a):
        self._t = text
        self.style = ""

    def setText(self, t):
        self._t = t

    def text(self):
        return self._t

    def setStyleSheet(self, s):
        self.style = s

    def font(self):
        return Loose()


class QLineEdit(Loose):
    Password = 1

    def __init__(self, text="", *a):
        self._v = text

    def text(self):
        return self._v


class QSpinBox(Loose):
    def __init__(self, *a):
        self._v = 0

    def setValue(self, v):
        self._v = v

    def value(self):
        return self._v


class QDoubleSpinBox(QSpinBox):
    pass


class QComboBox(Loose):
    def __init__(self, *a):
        self._v = ""
        self.currentTextChanged = FakeBoundSignal()

    def setCurrentText(self, t):
        changed = t != self._v
        self._v = t
        if changed:
            self.currentTextChanged.emit(t)

    def currentText(self):
        return self._v


class QPushButton(Loose):
    def __init__(self, text="", *a):
        self._t = text
        self.clicked = FakeBoundSignal()

    def setText(self, t):
        self._t = t

    def text(self):
        return self._t


class QPlainTextEdit(Loose):
    def __init__(self, *a):
        self.lines = []

    def appendPlainText(self, t):
        self.lines.append(t)


for name in ("QApplication", "QFormLayout", "QGroupBox", "QHBoxLayout", "QVBoxLayout"):
    globals()[name] = type(name, (Loose,), {})

core = types.ModuleType("PySide6.QtCore")
for n in ("QObject", "QRunnable", "QSettings", "QThreadPool", "QTimer", "Qt", "Signal"):
    setattr(core, n, globals()[n])
widgets = types.ModuleType("PySide6.QtWidgets")
for n in ("QApplication", "QComboBox", "QDoubleSpinBox", "QFormLayout", "QGroupBox", "QHBoxLayout", "QLabel",
          "QLineEdit", "QPlainTextEdit", "QPushButton", "QSpinBox", "QVBoxLayout", "QWidget"):
    setattr(widgets, n, globals()[n])
pkg = types.ModuleType("PySide6")
sys.modules.update({"PySide6": pkg, "PySide6.QtCore": core, "PySide6.QtWidgets": widgets})

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import glucose_osc_bridge as g  # noqa: E402

assert g.HAVE_QT, "fake Qt not picked up"

FAILS = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if (extra and not cond) else ""))
    if not cond:
        FAILS.append(name)


# ---------------- mock phone + OSC listener ----------------
BODY = {"v": []}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(BODY["v"]).encode())

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp.bind(("127.0.0.1", 0))
udp.settimeout(1.0)


def read_str(data, i):
    end = data.index(b"\0", i)
    return data[i:end].decode(), (end // 4 + 1) * 4


def decode(data):
    addr, i = read_str(data, 0)
    tags, i = read_str(data, i)
    t = tags[1:]
    if t == "i":
        return addr.rsplit("/", 1)[1], struct.unpack(">i", data[i:i + 4])[0]
    if t == "f":
        return addr.rsplit("/", 1)[1], struct.unpack(">f", data[i:i + 4])[0]
    return addr.rsplit("/", 1)[1], t == "T"


def drain(n=10):
    out = {}
    for _ in range(n):
        k, v = decode(udp.recvfrom(512)[0])
        out[k] = v
    return out


now_ms = int(time.time() * 1000)
BODY["v"] = [{"date": now_ms - 60_000, "sgv": 112, "direction": "FortyFiveUp"}]

win = g.MainWindow()
check("form built with every setting", set(win.w) == {f.name for f in g.fields(g.Settings)})
check("defaults loaded into widgets", win.w["phone_port"].value() == 17580 and win.w["units"].currentText() == "auto")

win.w["phone_host"]._v = "127.0.0.1"
win.w["phone_port"].setValue(srv.server_address[1])
win.w["osc_port"].setValue(udp.getsockname()[1])
win.w["secret"]._v = ""

collected = win._collect()
check("collect reads widgets back", collected.phone_port == srv.server_address[1] and collected.osc_host == "127.0.0.1")
check("collect keeps parameter names", collected.p_d1 == "BG_D1" and collected.p_beat == "BG_Beat" and collected.p_mgdl == "BG_Mgdl")

win.start_button.clicked.emit()  # same path as clicking Start
check("start toggles button", win.start_button.text() == "Stop" and win.running)
check("timers started", win.poll_timer.active and win.send_timer.active)
check("big label shows value + arrow", win.big.text() == "6.2  \u2197", win.big.text())
check("in-range colour is green", g.COLOR_OK in win.big.style, win.big.style)
check("sub label shows age, no tag", "min old" in win.sub.text() and "STALE" not in win.sub.text() and "LO" not in win.sub.text(), win.sub.text())

win._tick()
pk = drain()
check("tick sends digits 6.2 + trend", (pk["BG_D1"], pk["BG_D2"], pk["BG_D3"], pk["BG_Trend"]) == (10, 6, 2, 2), pk)
check("fresh not stale", pk["BG_Stale"] is False, pk)
beat1 = pk["BG_Beat"]
win._tick()
beat2 = drain()["BG_Beat"]
check("heartbeat flips on every tick", beat1 != beat2, (beat1, beat2))

# low reading: pink, LO tag
BODY["v"] = [{"date": int(time.time() * 1000), "sgv": 61, "direction": "Flat"}]
win._poll()
check("low reading is pink", g.COLOR_LOW in win.big.style and g.COLOR_LOW == "#ff7eb6", win.big.style)
check("low reading shows LO word", "LO" in win.sub.text(), win.sub.text())

# high reading: orange, HI tag
BODY["v"] = [{"date": int(time.time() * 1000), "sgv": 216, "direction": "Flat"}]
win._poll()
check("high reading is orange", g.COLOR_HIGH in win.big.style and g.COLOR_HIGH == "#ff9a3c", win.big.style)
check("high reading shows HI word", "HI" in win.sub.text(), win.sub.text())
check("colours are distinct", len({g.COLOR_OK, g.COLOR_LOW, g.COLOR_HIGH, g.COLOR_STALE}) == 4)

# stale reading
BODY["v"] = [{"date": int((time.time() - 40 * 60) * 1000), "sgv": 120, "direction": "Flat"}]
win._poll()
check("stale colour grey, STALE + -- shown", g.COLOR_STALE in win.big.style and "STALE" in win.sub.text() and "--" in win.sub.text(), win.sub.text())
win._tick()
pk = drain()
check("stale flag sent", pk["BG_Stale"] is True, pk)

# switch display to mg/dL in the form
BODY["v"] = [{"date": int(time.time() * 1000), "sgv": 112, "direction": "Flat"}]
win.w["display_units"].setCurrentText("mg/dL")
win.s = win._collect()
win.s.phone_port = srv.server_address[1]
win._poll()
check("mg/dL shown in big label", win.big.text().startswith("112"), win.big.text())
check("mg/dL named in sub label", "mg/dL" in win.sub.text(), win.sub.text())
win._tick()
pk = drain()
check("mg/dL digits + flag sent", (pk["BG_D1"], pk["BG_D2"], pk["BG_D3"], pk["BG_Mgdl"]) == (1, 1, 2, True), pk)
win.w["display_units"].setCurrentText("mmol/L")
win.s = win._collect()
win.s.phone_port = srv.server_address[1]

# phone unreachable keeps last value, logs error
win.s.phone_port = 1
win._poll()
check("unreachable logged, last reading kept", any("Could not reach" in l for l in win.log.lines) and win.reading is not None)

# test button
win._send_test()
pk = drain()
check("test values = 6.0 flat not stale", (pk["BG_D2"], pk["BG_D3"], pk["BG_Trend"], pk["BG_Stale"]) == (6, 0, 3, False), pk)


# ---- language switching
win.w["ui_language"].setCurrentText("fr")
check("window switches to French", win.start_button.text() in ("Arrêter", "Démarrer") and win.test_button.text() == "Envoyer des valeurs de test", win.test_button.text())
check("running button says Arrêter in French", win.start_button.text() == "Arrêter", win.start_button.text())
check("form labels retranslated", any(l.text() == "Adresse du téléphone" for l, _k in win._labels))
check("no words-language box in the window", "words_lang" not in win.w)
check("no BG_Lang box in the window", "p_lang" not in win.w)
win.w["display_units"].setCurrentText("rotate")
win._tick()
pk = drain()
check("rotate mode sends BG_Words", "BG_Words" in pk and "BG_Lang" not in pk, pk)
win.w["display_units"].setCurrentText("mmol/L")
for code in ("zh-Hant", "ko", "pt-BR", "ru", "ja", "zh-Hans", "de", "es"):
    win.w["ui_language"].setCurrentText(code)
    expect = g.APP_STRINGS[code]["send_test"]
    check(f"window switches to {code}", win.test_button.text() == expect and expect != g.APP_STRINGS["en"]["send_test"], win.test_button.text())
    check(f"labels retranslated in {code}", any(l.text() == g.APP_STRINGS[code]["phone_address"] for l, _k in win._labels))
win.w["ui_language"].setCurrentText("en")
check("back to English", win.test_button.text() == "Send test values")

# stop sends 'no data'
win.start_button.clicked.emit()
pk = drain()
check("stop sends stale + blank digits", pk["BG_Stale"] is True and (pk["BG_D1"], pk["BG_D2"], pk["BG_D3"]) == (10, 10, 10), pk)
check("stop resets UI", (not win.running) and win.start_button.text() == "Start")
check("timers stopped", not win.poll_timer.active and not win.send_timer.active)

print()
print("FAILURES:", FAILS if FAILS else "none")
sys.exit(1 if FAILS else 0)

#!/usr/bin/env python3
"""One-off: add zh-Hant, ko, pt-BR and ru to the bridge app's and the Unity builder's window languages.

Reads tools/i18n_more.py and rewrites src/glucose_osc_bridge.py and
unity/GlucoseDevice/Editor/GlucoseDeviceBuilder.cs. Refuses to run twice.
Run from the repository root:  python3 tools/add_languages.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import i18n_more as M  # noqa: E402

BRIDGE = os.path.join(REPO, "src", "glucose_osc_bridge.py")
BUILDER = os.path.join(REPO, "unity", "GlucoseDevice", "Editor", "GlucoseDeviceBuilder.cs")


def cs_escape(text: str) -> str:
    out = []
    for ch in text:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ord(ch) > 126:
            assert ord(ch) < 0x10000, "only characters in the basic plane are expected"
            out.append("\\u%04x" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def patch_bridge():
    s = open(BRIDGE, encoding="utf-8").read()
    if "'zh-Hant'" in s.split("APP_STRINGS")[0]:
        raise SystemExit("bridge already has the extra languages")
    old = "UI_LANGS = ['en', 'fr', 'es', 'de', 'ja', 'zh-Hans']"
    assert old in s
    s = s.replace(old, "UI_LANGS = ['en', 'fr', 'es', 'de', 'ja', 'zh-Hans', 'zh-Hant', 'ko', 'pt-BR', 'ru']")

    # Missing keys fall back to English in tr(), but give every language the full set.
    english_keys = re.findall(r"^        '(\w+)':", s[s.index("'en': {"):s.index("'fr': {")], flags=re.M)
    assert set(english_keys) == set(M.APP), (set(english_keys) ^ set(M.APP))

    blocks = []
    for i, code in enumerate(M.NEW_LANGS):
        lines = [f"    '{code}': {{"]
        for key in english_keys:
            lines.append(f"        {key!r}: {M.APP[key][i]!r},")
        lines.append("    },")
        blocks.append("\n".join(lines))
    start = s.index("'zh-Hans': {", s.index("APP_STRINGS = {"))
    end = s.index("\n}\n", start)
    s = s[:end] + "\n" + "\n".join(blocks) + s[end:]

    old = '''    if code.startswith("zh"):
        return "zh-Hans"
    return "en"'''
    assert old in s
    s = s.replace(old, '''    if code.startswith("zh"):
        return "zh-Hant" if any(t in code for t in ("TW", "HK", "MO", "Hant")) else "zh-Hans"
    if code.startswith("pt"):
        return "pt-BR"
    return "en"''')
    open(BRIDGE, "w", encoding="utf-8", newline="\n").write(s)


def patch_builder():
    s = open(BUILDER, encoding="utf-8").read()
    ui_line = re.search(r"static readonly string\[\] UiLangNames = \{[^}]*\};", s).group(0)
    if cs_escape(M.NEW_NAMES[0]) in ui_line:
        raise SystemExit("builder already has the extra languages")
    names = ", ".join('"%s"' % cs_escape(n) for n in M.NEW_NAMES)
    s = re.sub(r"(static readonly string\[\] UiLangNames = \{[^}]*?)( \};)", lambda m: m.group(1) + ", " + names + m.group(2), s, count=1)

    a = s.index("Strings = new Dictionary")
    b = s.index("\n        };", a)
    block = s[a:b]
    seen = set()

    def fix(m):
        key, body = m.group(1), m.group(2)
        items = re.findall(r'"(?:[^"\\]|\\.)*"', body)
        if key == "menu_lang_tip":
            items[0] = items[0].rstrip('" ') + '"'
        if len(items) == 1:
            items += ['""'] * 5          # empty = fall back to English
        assert len(items) == 6, (key, len(items))
        assert key in M.ED, "no translation for " + key
        items += ['"%s"' % cs_escape(t) for t in M.ED[key]]
        seen.add(key)
        return '{ "%s", new[] { %s } }' % (key, ", ".join(items))

    block = re.sub(r'\{ "(\w+)", new\[\] \{(.*?)\} \}', fix, block, flags=re.S)
    missing = set(M.ED) - seen
    assert not missing, missing
    s = s[:a] + block + s[b:]

    old = "                case SystemLanguage.ChineseSimplified:\n                case SystemLanguage.ChineseTraditional: return 5;"
    assert old in s
    s = s.replace(old, "                case SystemLanguage.ChineseSimplified: return 5;\n"
                       "                case SystemLanguage.ChineseTraditional: return 6;\n"
                       "                case SystemLanguage.Korean: return 7;\n"
                       "                case SystemLanguage.Portuguese: return 8;\n"
                       "                case SystemLanguage.Russian: return 9;")
    old = "// UI language index -> words-panel language index (en, fr, es, de, ja, zh-Hans share positions 0-5)."
    assert old in s
    s = s.replace(old, "// UI language index -> words-panel language index (both lists use the same 10 positions).")
    old = "                int i = Mathf.Clamp(uiLang < 0 ? 0 : uiLang, 0, values.Length - 1);\n                return string.IsNullOrEmpty(values[i]) ? values[0] : values[i];"
    assert old in s
    s = s.replace(old, "                int i = uiLang < 0 ? 0 : uiLang;\n                return i >= values.Length || string.IsNullOrEmpty(values[i]) ? values[0] : values[i];")
    open(BUILDER, "w", encoding="utf-8", newline="\n").write(s)


if __name__ == "__main__":
    patch_bridge()
    patch_builder()
    print("done")

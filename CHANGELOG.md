# Changelog

## 0.1.0 (unreleased)

First public release.

- Bridge app (Windows and Linux): reads xDrip+ / Nightscout `sgv.json` and sends VRChat OSC parameters (digits, trend, low/high/stale, units, heartbeat).
- Display modes: mmol/L, mg/dL, alternate (units every 15 s), rotate (mmol/L, mg/dL, plain words; 10 s each).
- Unity builder: LCD-style device prefab and animator layers; prop-relative paths for VRCFury / Modular Avatar; Write Defaults ON or OFF.
- Plain-words "simple mode" in 10 languages, with an optional language dial in the VRChat menu.
- Watchdog: the screen goes grey ("--") when the bridge stops sending.
- App window and Unity builder in 10 languages: English, French, Spanish, German, Japanese, Simplified and Traditional Chinese, Korean, Brazilian Portuguese, Russian (machine-translated, not yet reviewed by native speakers).

### Updating from a pre-release copy
If you copied the `GlucoseDevice` folder into Unity by hand before, delete `Assets/GlucoseDevice/Editor`, `Textures` and `Models` first (keep `Generated`), then import the package and press **Build device prefab** again. The package's files have new fixed IDs, so Unity would otherwise import them as duplicates.

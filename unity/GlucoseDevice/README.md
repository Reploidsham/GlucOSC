# Glucose Device (VRChat prefab builder)

A small handheld that shows your CGM number in VRChat, driven by the GlucOSC bridge app over OSC.

The screen is black with bright seven-segment digits, so it stays readable in dark or bright worlds. Nothing is lit by the world's lighting. Colours are switched by texture rows, so any shader with a main texture, tiling and offset and transparency will work.

**Display only.** CGM readings lag the real value. Never use this to make treatment decisions, and keep your real alarms on.

Colours of the digits: pink = low, orange = high, mint green = in range, grey = stale or no data. The trend arrow turns to point up, up-right, flat, down-right or down (a double arrow for fast changes). The words LO / HI / -- are also drawn, so colour is never the only signal. Nothing pulses or flashes.

## Before you start

Try it in a **copy** of your avatar project first. If something goes wrong, copy the red Console text into an issue on the GlucOSC repository.

## Steps

1. Open your avatar project (Unity **2022.3**, the version VRChat uses). The VRChat SDK is only needed for the ready-made Parameters and Menu assets.
2. **Assets > Import Package > Custom Package** and pick `GlucOSC-Unity.unitypackage`, or unzip `GlucOSC-Unity.zip` into `Assets`. Either way you get `Assets/GlucoseDevice`. (Updating from a hand-copied pre-release? See the note in CHANGELOG.md first.)
3. Menu: **Tools > Glucose Device > Open Builder**.
4. Press **Build device prefab**. Drag `Assets/GlucoseDevice/Generated/GlucoseDevice.prefab` into a scene. The screen faces the **-Z** side (turn the device so that side faces you).
5. Press **Create a standalone controller** to get a test controller, or drag your own FX controller into the box and press **Add layers + parameters to my controller** (a backup copy is made first).
6. Add the parameters in `PARAMETERS.txt` to your avatar's Expression Parameters by hand. The builder has a **Copy parameter list** button too.
7. (Avatar-relative only) Put the prefab on your avatar. If you move it (for example onto a wrist bone), drag your avatar root and the moved device into the two boxes in step 2 of the window and **rebuild the layers** so the animation paths match.

## Using it with VRCFury (Full Controller)

1. In the builder, set **Path style** to *Prop-relative* (the default).
2. Build the prefab, then **Create a standalone controller**, then **Create Expression Parameters + Menu assets** (needs the VRChat SDK in the project).
3. On the prefab's **root** object add VRCFury > **Full Controller**. Put the controller in *Controller* (type FX), the Menu asset in *Menu*, and the Parameters asset in *Parameters*.
4. Put the prefab on the avatar wherever you like (wrist bone, hand). VRCFury moves the animation paths for you, so nothing needs rebuilding when you move it.
5. If VRCFury lists "paths animated but not found", the controller was built with *Avatar-relative* paths. Switch to *Prop-relative* and rebuild the controller.
6. The yellow "controller uses WD off" note is fine; VRCFury converts it to match the avatar.

## Important: parameter names with VRCFury / Modular Avatar

The bridge sends plain names (`BG_D1`, `BG_Beat` ...). If the animator sees different names, the device never reacts, even though VRChat's OSC debug window shows the values arriving. The screen then sits on the grey "--" cover because the heartbeat never reaches the watchdog.

**VRCFury** renames every parameter in a Full Controller to something like `VF111_BG_D1` when the avatar is built, unless the parameter is marked global. Fix (do one of these):

1. Drag `GlucoseDevice_Parameters` (made by the builder) into the Full Controller's **Parameters** list, or
2. Add a **Global Parameter** entry there. `BG_*` should cover them all if your VRCFury version accepts the wildcard; otherwise add the names one by one.

Rebuild/re-upload the avatar after changing it.

**Quick check:** in VRChat, open the debug menu (Local Avatar page). If you see `VF###_BG_D1` instead of `BG_D1`, the parameters are being renamed. Putting the `VF###_` names into the bridge's parameter-name boxes does work, but it is only a test: that number can change when you add or remove VRCFury components on the avatar.

**Modular Avatar** should keep the names as they are by default (untested). The same check applies.

## Options

- **Write Defaults ON**: tick this if the rest of your FX controller uses WD ON. Leave it off if you use WD OFF (your usual). The layers are built so every state in a layer animates the same properties, so they behave either way.
- **No-data timeout**: how long the heartbeat can be silent before the screen is covered by a grey "--". Default 90 s.

## Simple mode (for people who don't know about sugars)

Turn on **Simple mode (words)** in your menu and the numbers are replaced by plain words in the same colour:

- Green: ALL GOOD, NO HELP NEEDED
- Pink: LOW, NEEDS SUGAR
- Orange: HIGH, NO SUGAR
- Grey: NO DATA, ASK ME

The trend arrow stays visible in both modes. The thresholds are the bridge's low and high limits. The words describe a state; they are not medical advice, and readings lag by an amount that differs between sensors (users should note their own sensor's lag here). Never use the display in place of a real alarm or a fingerstick.

## Languages

- **Plain-words panel (simple mode)** comes in 10 languages: English, French, Spanish, German, Japanese, Simplified Chinese, Traditional Chinese, Korean, Brazilian Portuguese and Russian. Pick one in the builder (**Simple-mode language**) before building the prefab. Numbers, LO / HI and the unit labels are the same in every language, and the trend arrow is a separate object, so it never needs translating.
- **Language dial in the VRChat menu (optional):** tick *Language dial in the VRChat menu* in the builder. This adds a Float parameter, `BG_LangSel` (+8 sync bits, saved), a Radial Puppet in the menu asset, and one animator layer. Each tenth of the dial is one language, in this order: 0-10% English, French, Spanish, German, Japanese, Simplified Chinese, Traditional Chinese, Korean, Brazilian Portuguese, Russian (90-100%). The dial starts in the middle of the language you picked in the builder. Leave it off to keep the language fixed in the prefab and save the bits.
- **The bridge app does not send a language.** The panel's language is set by the builder (default: your computer's language, changeable in the dropdown) or by the dial. The bridge app has its own window language box, which only changes the app itself.
- **Builder window and bridge app** are translated into the same 10 languages. They pick your system language at first start (English if yours isn't listed) and have a language box at the top. A few newer builder labels (the two optional language/rotate options) are translated only into the four newest languages and shown in English in French, Spanish, German, Japanese and Simplified Chinese.
- **All translations were written by an AI and have not been checked by native speakers.** Please review them, especially the plain-words panel, because wrong words on a medical display are worse than no words. To fix a word, edit the text table (`tools/i18n_src.py` in the source repo) and run `tools/make_textures.py`.

## Rotating displays (optional)

In the bridge app, set **Avatar shows** to **rotate**. It then cycles mmol/L, mg/dL and the plain-words panel, 10 seconds each (**Rotate every (s)**, minimum 5). The mmol/L and mg/dL steps work with any avatar. For the words step, tick *Let the bridge app rotate to the words panel* in the builder: that adds one Bool, `BG_Words` (+1 sync bit, not saved), and the panel switches on when either `BG_Words` (bridge) or `BG_Simple` (your menu toggle) is true. Without it, the words step simply keeps showing numbers.

## Units

The bridge app's **Avatar shows** setting can be mmol/L, mg/dL, **alternate**, or **rotate** (see above). Alternate flips between the two every 15 seconds (changeable) so a helper who only reads one of them can still see it. The device follows automatically; nothing to rebuild.

## Performance

The screen is built from one set of glyph objects. Colour is chosen by moving the texture offset to a different colour row, so nothing is recoloured and no colour property is animated. Counting every object, including hidden ones, the device is **13 material slots** (10 for the screen, 3 for the shell) and **9 animator layers** (10 with the language dial). Merge the three shell meshes into one in Blender to save 2 more slots. Synced parameters cost 39 bits of VRChat's 256, plus 8 for the language dial and 1 for `BG_Words`.

## Making it look nicer

`Models/GD_Shell.obj` is a placeholder case. Convert it to FBX if you like, or model your own in Blender, name it `GD_Shell`, rebuild the prefab, and leave the `Screen` object and its children alone (the animations find them by name). Units are metres and the screen faces -Z.

## Testing without a CGM

Run the bridge app's **Test** button (sends a fixed 6.0 flat) or use VRChat's OSC debug window / any OSC tool to set `BG_D2`, `BG_D3`, etc.

## For the friends reviewing it

- Units can be switched between mmol/L and mg/dL by the bridge app (the device follows via `BG_Mgdl`).
- Only built-in Unity shaders are used, no extra packages.
- `BG_Show` lets the wearer hide the numbers from others.

## Reporting problems

Open an issue with the exact red Console text, which button you pressed, and what you saw versus what you expected. A screenshot of the Animator window helps if the layers look wrong.

## Alternative text style (dot-matrix)

`Textures/Alternatives/lcd_words_dotmatrix.png` is the same plain-words panel in a blocky dot-matrix look (same layout, same 10 languages). To use it, rename your current `lcd_words.png` to something else, copy the alternative into `Textures/` as `lcd_words.png`, and rebuild the prefab. Unity may need Reimport if the old import settings stick (no mipmaps, clamp, uncompressed).

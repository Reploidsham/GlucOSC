// Glucose Device builder
// ======================
// Builds a small LCD-style device prefab plus the animator layers that drive it
// from the OSC parameters sent by the glucose bridge app.
//
// Menu: Tools > Glucose Device > Open Builder
//
// Written for Unity 2022.3 (VRChat's version). It uses only Unity's own editor API
// and does NOT need the VRChat SDK, so it also runs in a plain test project.
// See README.md in the same folder for the step-by-step instructions.

using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;
#if VRC_SDK_VRCSDK3
using VRC.SDK3.Avatars.ScriptableObjects;
#endif

namespace GlucoseDevice.EditorTools
{
    public class GlucoseDeviceBuilder : EditorWindow
    {
        // ------------------------------------------------------------------ languages
        // Window languages (machine-written translations: please have native speakers review them).
        static readonly string[] UiLangNames = { "English", "Fran\u00e7ais", "Espa\u00f1ol", "Deutsch", "\u65e5\u672c\u8a9e", "\u7b80\u4f53\u4e2d\u6587", "\u7e41\u9ad4\u4e2d\u6587", "\ud55c\uad6d\uc5b4", "Portugu\u00eas (BR)", "\u0420\u0443\u0441\u0441\u043a\u0438\u0439" };
        // Plain-words panel languages. ORDER = texture columns = the bridge app's WORD_LANGS.
        static readonly string[] WordLangNames = { "English", "Fran\u00e7ais", "Espa\u00f1ol", "Deutsch", "\u65e5\u672c\u8a9e", "\u7b80\u4f53\u4e2d\u6587", "\u7e41\u9ad4\u4e2d\u6587", "\ud55c\uad6d\uc5b4", "Portugu\u00eas (BR)", "\u0420\u0443\u0441\u0441\u043a\u0438\u0439" };
        const int WordLangCount = 10;

        static readonly Dictionary<string, string[]> Strings = new Dictionary<string, string[]>
        {
            { "language", new[] { "Language", "Langue", "Idioma", "Sprache", "\u8a00\u8a9e", "\u8bed\u8a00", "\u8a9e\u8a00", "\uc5b8\uc5b4", "Idioma", "\u042f\u0437\u044b\u043a" } },
            { "title", new[] { "GlucOSC device builder", "G\u00e9n\u00e9rateur d'appareil GlucOSC", "Constructor del dispositivo GlucOSC", "GlucOSC-Ger\u00e4te-Builder", "GlucOSC \u30c7\u30d0\u30a4\u30b9\u30d3\u30eb\u30c0\u30fc", "GlucOSC \u8bbe\u5907\u751f\u6210\u5668", "GlucOSC \u88dd\u7f6e\u5efa\u7acb\u5668", "GlucOSC \uae30\uae30 \ube4c\ub354", "Construtor do dispositivo GlucOSC", "\u041a\u043e\u043d\u0441\u0442\u0440\u0443\u043a\u0442\u043e\u0440 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430 GlucOSC" } },
            { "disclaimer", new[] { "Display only. CGM readings lag, so never use this device to make treatment decisions.", "Affichage seulement. Les mesures du CGM sont en retard : n'utilisez jamais cet appareil pour d\u00e9cider d'un traitement.", "Solo para mostrar. Las lecturas del CGM tienen retraso: nunca uses este dispositivo para decidir tratamientos.", "Nur Anzeige. CGM-Werte sind verz\u00f6gert. Triff damit niemals Behandlungsentscheidungen.", "\u8868\u793a\u5c02\u7528\u3067\u3059\u3002CGM\u306e\u6570\u5024\u306b\u306f\u9045\u308c\u304c\u3042\u308b\u305f\u3081\u3001\u6cbb\u7642\u306e\u5224\u65ad\u306b\u306f\u7d76\u5bfe\u306b\u4f7f\u308f\u306a\u3044\u3067\u304f\u3060\u3055\u3044\u3002", "\u4ec5\u7528\u4e8e\u663e\u793a\u3002CGM \u8bfb\u6570\u5b58\u5728\u5ef6\u8fdf\uff0c\u5207\u52ff\u636e\u6b64\u505a\u51fa\u6cbb\u7597\u51b3\u5b9a\u3002", "\u50c5\u4f9b\u986f\u793a\u3002CGM \u8b80\u6578\u5b58\u5728\u5ef6\u9072\uff0c\u5207\u52ff\u64da\u6b64\u505a\u51fa\u6cbb\u7642\u6c7a\u5b9a\u3002", "\ud45c\uc2dc \uc804\uc6a9\uc785\ub2c8\ub2e4. CGM \uce21\uc815\uac12\uc5d0\ub294 \uc9c0\uc5f0\uc774 \uc788\uc73c\ubbc0\ub85c \uc774 \uae30\uae30\ub85c \uce58\ub8cc \uacb0\uc815\uc744 \ub0b4\ub9ac\uc9c0 \ub9c8\uc138\uc694.", "Somente exibi\u00e7\u00e3o. As leituras do CGM t\u00eam atraso; nunca use este dispositivo para tomar decis\u00f5es de tratamento.", "\u0422\u043e\u043b\u044c\u043a\u043e \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435. \u041f\u043e\u043a\u0430\u0437\u0430\u043d\u0438\u044f CGM \u0437\u0430\u043f\u0430\u0437\u0434\u044b\u0432\u0430\u044e\u0442, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u043d\u0438\u043a\u043e\u0433\u0434\u0430 \u043d\u0435 \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0439\u0442\u0435 \u043f\u043e \u044d\u0442\u043e\u043c\u0443 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0443 \u0440\u0435\u0448\u0435\u043d\u0438\u044f \u043e \u043b\u0435\u0447\u0435\u043d\u0438\u0438." } },
            { "step1", new[] { "1. Build the device", "1. Cr\u00e9er l'appareil", "1. Crear el dispositivo", "1. Ger\u00e4t erstellen", "1. \u30c7\u30d0\u30a4\u30b9\u3092\u4f5c\u6210", "1. \u751f\u6210\u8bbe\u5907", "1. \u5efa\u7acb\u88dd\u7f6e", "1. \uae30\uae30 \ub9cc\ub4e4\uae30", "1. Criar o dispositivo", "1. \u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e" } },
            { "step1_help", new[] { "Creates the prefab and its materials in Assets/GlucoseDevice/Generated. The case comes from Models/GD_Shell (OBJ or FBX); without it you get a plain grey box. To use your own model, name it GD_Shell, rebuild, and keep the Screen object as it is.", "Cr\u00e9e le prefab et ses mat\u00e9riaux dans Assets/GlucoseDevice/Generated. Le bo\u00eetier vient de Models/GD_Shell (OBJ ou FBX) ; sans lui, vous obtenez une simple bo\u00eete grise. Pour utiliser votre mod\u00e8le, nommez-le GD_Shell, reconstruisez et laissez l'objet Screen tel quel.", "Crea el prefab y sus materiales en Assets/GlucoseDevice/Generated. La carcasa viene de Models/GD_Shell (OBJ o FBX); sin ella obtienes una caja gris. Para usar tu modelo, ll\u00e1malo GD_Shell, vuelve a generar y deja el objeto Screen como est\u00e1.", "Erstellt das Prefab und seine Materialien in Assets/GlucoseDevice/Generated. Das Geh\u00e4use stammt aus Models/GD_Shell (OBJ oder FBX); ohne es entsteht eine graue Box. F\u00fcr ein eigenes Modell: GD_Shell nennen, neu erstellen und das Screen-Objekt unver\u00e4ndert lassen.", "Assets/GlucoseDevice/Generated \u306b\u30d7\u30ec\u30cf\u30d6\u3068\u30de\u30c6\u30ea\u30a2\u30eb\u3092\u4f5c\u6210\u3057\u307e\u3059\u3002\u30b1\u30fc\u30b9\u306f Models/GD_Shell\uff08OBJ \u307e\u305f\u306f FBX\uff09\u304b\u3089\u8aad\u307f\u8fbc\u307e\u308c\u3001\u7121\u3044\u5834\u5408\u306f\u7070\u8272\u306e\u7bb1\u306b\u306a\u308a\u307e\u3059\u3002\u81ea\u4f5c\u30e2\u30c7\u30eb\u3092\u4f7f\u3046\u306b\u306f GD_Shell \u3068\u3044\u3046\u540d\u524d\u306b\u3057\u3066\u518d\u4f5c\u6210\u3057\u3001Screen \u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u306f\u305d\u306e\u307e\u307e\u306b\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "\u5728 Assets/GlucoseDevice/Generated \u4e2d\u751f\u6210\u9884\u5236\u4f53\u548c\u6750\u8d28\u3002\u5916\u58f3\u53d6\u81ea Models/GD_Shell\uff08OBJ \u6216 FBX\uff09\uff0c\u6ca1\u6709\u65f6\u4f7f\u7528\u7070\u8272\u76d2\u5b50\u3002\u8981\u4f7f\u7528\u81ea\u5df1\u7684\u6a21\u578b\uff0c\u8bf7\u547d\u540d\u4e3a GD_Shell \u540e\u91cd\u65b0\u751f\u6210\uff0c\u5e76\u4fdd\u6301 Screen \u5bf9\u8c61\u4e0d\u53d8\u3002", "\u5728 Assets/GlucoseDevice/Generated \u4e2d\u5efa\u7acb Prefab \u8207\u6750\u8cea\u3002\u5916\u6bbc\u53d6\u81ea Models/GD_Shell\uff08OBJ \u6216 FBX\uff09\uff0c\u6c92\u6709\u6642\u6703\u4f7f\u7528\u7070\u8272\u65b9\u76d2\u3002\u82e5\u8981\u4f7f\u7528\u81ea\u5df1\u7684\u6a21\u578b\uff0c\u8acb\u547d\u540d\u70ba GD_Shell \u5f8c\u91cd\u65b0\u5efa\u7acb\uff0c\u4e26\u4fdd\u6301 Screen \u7269\u4ef6\u4e0d\u8b8a\u3002", "Assets/GlucoseDevice/Generated\uc5d0 \ud504\ub9ac\ud339\uacfc \uba38\ud2f0\ub9ac\uc5bc\uc744 \ub9cc\ub4ed\ub2c8\ub2e4. \ucf00\uc774\uc2a4\ub294 Models/GD_Shell(OBJ \ub610\ub294 FBX)\uc5d0\uc11c \uac00\uc838\uc624\uba70, \uc5c6\uc73c\uba74 \ud68c\uc0c9 \uc0c1\uc790\uac00 \ub9cc\ub4e4\uc5b4\uc9d1\ub2c8\ub2e4. \uc9c1\uc811 \ub9cc\ub4e0 \ubaa8\ub378\uc744 \uc4f0\ub824\uba74 \uc774\ub984\uc744 GD_Shell\ub85c \uc9c0\uc815\ud558\uace0 \ub2e4\uc2dc \ub9cc\ub4e0 \ub4a4 Screen \uc624\ube0c\uc81d\ud2b8\ub294 \uadf8\ub300\ub85c \ub450\uc138\uc694.", "Cria o prefab e seus materiais em Assets/GlucoseDevice/Generated. A carca\u00e7a vem de Models/GD_Shell (OBJ ou FBX); sem ela, voc\u00ea recebe uma caixa cinza. Para usar seu pr\u00f3prio modelo, nomeie-o GD_Shell, gere novamente e mantenha o objeto Screen como est\u00e1.", "\u0421\u043e\u0437\u0434\u0430\u0451\u0442 \u043f\u0440\u0435\u0444\u0430\u0431 \u0438 \u0435\u0433\u043e \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u0432 Assets/GlucoseDevice/Generated. \u041a\u043e\u0440\u043f\u0443\u0441 \u0431\u0435\u0440\u0451\u0442\u0441\u044f \u0438\u0437 Models/GD_Shell (OBJ \u0438\u043b\u0438 FBX); \u0431\u0435\u0437 \u043d\u0435\u0433\u043e \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u0441\u044f \u0441\u0435\u0440\u0430\u044f \u043a\u043e\u0440\u043e\u0431\u043a\u0430. \u0427\u0442\u043e\u0431\u044b \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u0441\u0432\u043e\u044e \u043c\u043e\u0434\u0435\u043b\u044c, \u043d\u0430\u0437\u043e\u0432\u0438\u0442\u0435 \u0435\u0451 GD_Shell, \u043f\u0435\u0440\u0435\u0441\u043e\u0431\u0435\u0440\u0438\u0442\u0435 \u0438 \u043d\u0435 \u0442\u0440\u043e\u0433\u0430\u0439\u0442\u0435 \u043e\u0431\u044a\u0435\u043a\u0442 Screen." } },
            { "btn_build", new[] { "Build device prefab", "Cr\u00e9er le prefab de l'appareil", "Crear el prefab del dispositivo", "Ger\u00e4te-Prefab erstellen", "\u30c7\u30d0\u30a4\u30b9\u306e\u30d7\u30ec\u30cf\u30d6\u3092\u4f5c\u6210", "\u751f\u6210\u8bbe\u5907\u9884\u5236\u4f53", "\u5efa\u7acb\u88dd\u7f6e Prefab", "\uae30\uae30 \ud504\ub9ac\ud339 \ub9cc\ub4e4\uae30", "Criar prefab do dispositivo", "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043f\u0440\u0435\u0444\u0430\u0431 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430" } },
            { "step2", new[] { "2. How will it be attached?", "2. Comment sera-t-il fix\u00e9 ?", "2. \u00bfC\u00f3mo se acoplar\u00e1?", "2. Wie wird es befestigt?", "2. \u3069\u306e\u3088\u3046\u306b\u53d6\u308a\u4ed8\u3051\u307e\u3059\u304b\uff1f", "2. \u5982\u4f55\u5b89\u88c5\uff1f", "2. \u8981\u5982\u4f55\u5b89\u88dd\uff1f", "2. \uc5b4\ub5bb\uac8c \ubd80\ucc29\ud558\ub098\uc694?", "2. Como ser\u00e1 acoplado?", "2. \u041a\u0430\u043a \u0435\u0433\u043e \u043f\u0440\u0438\u043a\u0440\u0435\u043f\u0438\u0442\u044c?" } },
            { "path_style", new[] { "Path style", "Type de chemin", "Tipo de ruta", "Pfadart", "\u30d1\u30b9\u5f62\u5f0f", "\u8def\u5f84\u65b9\u5f0f", "\u8def\u5f91\u65b9\u5f0f", "\uacbd\ub85c \ubc29\uc2dd", "Tipo de caminho", "\u0422\u0438\u043f \u043f\u0443\u0442\u0435\u0439" } },
            { "path_prop", new[] { "Prop-relative (VRCFury Full Controller / Modular Avatar)", "Relatif \u00e0 l'objet (VRCFury Full Controller / Modular Avatar)", "Relativa al objeto (VRCFury Full Controller / Modular Avatar)", "Relativ zum Prop (VRCFury Full Controller / Modular Avatar)", "\u30d7\u30ed\u30c3\u30d7\u57fa\u6e96 (VRCFury Full Controller / Modular Avatar)", "\u76f8\u5bf9\u4e8e\u9053\u5177 (VRCFury Full Controller / Modular Avatar)", "\u76f8\u5c0d\u65bc\u9053\u5177 (VRCFury Full Controller / Modular Avatar)", "\ud504\ub86d \uae30\uc900 (VRCFury Full Controller / Modular Avatar)", "Relativo ao objeto (VRCFury Full Controller / Modular Avatar)", "\u041e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u0430 (VRCFury Full Controller / Modular Avatar)" } },
            { "path_avatar", new[] { "Avatar-relative (merge into my own FX controller)", "Relatif \u00e0 l'avatar (fusion dans mon propre contr\u00f4leur FX)", "Relativa al avatar (fusionar en mi propio controlador FX)", "Relativ zum Avatar (in meinen eigenen FX-Controller einf\u00fcgen)", "\u30a2\u30d0\u30bf\u30fc\u57fa\u6e96\uff08\u81ea\u5206\u306eFX\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc\u306b\u7d71\u5408\uff09", "\u76f8\u5bf9\u4e8e Avatar\uff08\u5408\u5e76\u5230\u6211\u81ea\u5df1\u7684 FX \u63a7\u5236\u5668\uff09", "\u76f8\u5c0d\u65bc Avatar\uff08\u5408\u4f75\u5230\u6211\u81ea\u5df1\u7684 FX \u63a7\u5236\u5668\uff09", "\uc544\ubc14\ud0c0 \uae30\uc900(\ub0b4 FX \ucee8\ud2b8\ub864\ub7ec\uc5d0 \ubcd1\ud569)", "Relativo ao avatar (mesclar no meu pr\u00f3prio controlador FX)", "\u041e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u0430\u0432\u0430\u0442\u0430\u0440\u0430 (\u0441\u043b\u0438\u0442\u044c \u0441 \u043c\u043e\u0438\u043c FX-\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440\u043e\u043c)" } },
            { "help_prop", new[] { "Use this if VRCFury or Modular Avatar will move the prop onto the avatar for you. Paths start at the prop itself (Screen/Numbers/Digit1 ...), so the prop can sit anywhere. Put the VRCFury component on the prop's root object.", "\u00c0 utiliser si VRCFury ou Modular Avatar place l'objet sur l'avatar pour vous. Les chemins partent de l'objet lui-m\u00eame (Screen/Numbers/Digit1 ...), il peut donc \u00eatre n'importe o\u00f9. Mettez le composant VRCFury sur l'objet racine.", "\u00dasalo si VRCFury o Modular Avatar colocar\u00e1 el objeto en el avatar por ti. Las rutas parten del propio objeto (Screen/Numbers/Digit1 ...), as\u00ed que puede estar en cualquier sitio. Pon el componente VRCFury en el objeto ra\u00edz.", "Verwenden, wenn VRCFury oder Modular Avatar den Prop f\u00fcr dich am Avatar anbringt. Die Pfade beginnen beim Prop selbst (Screen/Numbers/Digit1 ...), er kann also \u00fcberall sitzen. Die VRCFury-Komponente geh\u00f6rt auf das Root-Objekt des Props.", "VRCFury \u3084 Modular Avatar \u304c\u30d7\u30ed\u30c3\u30d7\u3092\u30a2\u30d0\u30bf\u30fc\u306b\u914d\u7f6e\u3059\u308b\u5834\u5408\u306b\u9078\u3073\u307e\u3059\u3002\u30d1\u30b9\u306f\u30d7\u30ed\u30c3\u30d7\u81ea\u8eab\u304b\u3089\u59cb\u307e\u308b\uff08Screen/Numbers/Digit1 \u2026\uff09\u305f\u3081\u3001\u3069\u3053\u306b\u7f6e\u3044\u3066\u3082\u52d5\u4f5c\u3057\u307e\u3059\u3002VRCFury \u30b3\u30f3\u30dd\u30fc\u30cd\u30f3\u30c8\u306f\u30d7\u30ed\u30c3\u30d7\u306e\u30eb\u30fc\u30c8\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u306b\u4ed8\u3051\u3066\u304f\u3060\u3055\u3044\u3002", "\u5f53 VRCFury \u6216 Modular Avatar \u4f1a\u66ff\u60a8\u628a\u9053\u5177\u653e\u5230 Avatar \u4e0a\u65f6\u4f7f\u7528\u3002\u8def\u5f84\u4ece\u9053\u5177\u81ea\u8eab\u5f00\u59cb\uff08Screen/Numbers/Digit1 \u2026\uff09\uff0c\u56e0\u6b64\u9053\u5177\u53ef\u653e\u5728\u4efb\u4f55\u4f4d\u7f6e\u3002\u8bf7\u628a VRCFury \u7ec4\u4ef6\u52a0\u5728\u9053\u5177\u7684\u6839\u5bf9\u8c61\u4e0a\u3002", "\u7576 VRCFury \u6216 Modular Avatar \u6703\u66ff\u60a8\u628a\u9053\u5177\u653e\u5230 Avatar \u4e0a\u6642\u4f7f\u7528\u3002\u8def\u5f91\u5f9e\u9053\u5177\u672c\u8eab\u958b\u59cb\uff08Screen/Numbers/Digit1 \u2026\uff09\uff0c\u56e0\u6b64\u9053\u5177\u53ef\u653e\u5728\u4efb\u4f55\u4f4d\u7f6e\u3002\u8acb\u628a VRCFury \u5143\u4ef6\u52a0\u5728\u9053\u5177\u7684\u6839\u7269\u4ef6\u4e0a\u3002", "VRCFury\ub098 Modular Avatar\uac00 \ud504\ub86d\uc744 \uc544\ubc14\ud0c0\uc5d0 \ubc30\uce58\ud574 \uc8fc\ub294 \uacbd\uc6b0\uc5d0 \uc0ac\uc6a9\ud558\uc138\uc694. \uacbd\ub85c\ub294 \ud504\ub86d \uc790\uccb4\uc5d0\uc11c \uc2dc\uc791\ud558\ubbc0\ub85c(Screen/Numbers/Digit1 \u2026) \ud504\ub86d\uc744 \uc5b4\ub514\uc5d0 \ub450\uc5b4\ub3c4 \ub429\ub2c8\ub2e4. VRCFury \ucef4\ud3ec\ub10c\ud2b8\ub294 \ud504\ub86d\uc758 \ub8e8\ud2b8 \uc624\ube0c\uc81d\ud2b8\uc5d0 \ubd99\uc774\uc138\uc694.", "Use se o VRCFury ou o Modular Avatar for colocar o objeto no avatar para voc\u00ea. Os caminhos come\u00e7am no pr\u00f3prio objeto (Screen/Numbers/Digit1 ...), ent\u00e3o ele pode ficar em qualquer lugar. Coloque o componente VRCFury no objeto raiz.", "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435, \u0435\u0441\u043b\u0438 VRCFury \u0438\u043b\u0438 Modular Avatar \u0441\u0430\u043c \u043f\u043e\u043c\u0435\u0441\u0442\u0438\u0442 \u043f\u0440\u0435\u0434\u043c\u0435\u0442 \u043d\u0430 \u0430\u0432\u0430\u0442\u0430\u0440. \u041f\u0443\u0442\u0438 \u043d\u0430\u0447\u0438\u043d\u0430\u044e\u0442\u0441\u044f \u043e\u0442 \u0441\u0430\u043c\u043e\u0433\u043e \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u0430 (Screen/Numbers/Digit1 ...), \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u043e\u043d \u043c\u043e\u0436\u0435\u0442 \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u044c\u0441\u044f \u0433\u0434\u0435 \u0443\u0433\u043e\u0434\u043d\u043e. \u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043a\u043e\u043c\u043f\u043e\u043d\u0435\u043d\u0442 VRCFury \u043d\u0430 \u043a\u043e\u0440\u043d\u0435\u0432\u043e\u0439 \u043e\u0431\u044a\u0435\u043a\u0442 \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u0430." } },
            { "help_avatar", new[] { "Use this if you merge the layers straight into your avatar's FX controller. Paths start at the avatar root, so put the device where it will live first, then drag the avatar root and the device from the scene into these boxes. Leave both empty to use the prefab at the avatar root.", "\u00c0 utiliser si vous fusionnez les couches directement dans le contr\u00f4leur FX de votre avatar. Les chemins partent de la racine de l'avatar : placez d'abord l'appareil, puis glissez la racine de l'avatar et l'appareil depuis la sc\u00e8ne dans ces champs. Laissez vides pour utiliser le prefab \u00e0 la racine.", "\u00dasalo si fusionas las capas directamente en el controlador FX de tu avatar. Las rutas parten de la ra\u00edz del avatar: coloca primero el dispositivo y luego arrastra la ra\u00edz del avatar y el dispositivo desde la escena a estas casillas. D\u00e9jalas vac\u00edas para usar el prefab en la ra\u00edz.", "Verwenden, wenn du die Layer direkt in den FX-Controller deines Avatars einf\u00fcgst. Die Pfade beginnen an der Avatar-Wurzel: Ger\u00e4t zuerst platzieren, dann Avatar-Wurzel und Ger\u00e4t aus der Szene in diese Felder ziehen. Leer lassen, um das Prefab an der Wurzel zu verwenden.", "\u30ec\u30a4\u30e4\u30fc\u3092\u30a2\u30d0\u30bf\u30fc\u306eFX\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc\u306b\u76f4\u63a5\u7d71\u5408\u3059\u308b\u5834\u5408\u306b\u9078\u3073\u307e\u3059\u3002\u30d1\u30b9\u306f\u30a2\u30d0\u30bf\u30fc\u306e\u30eb\u30fc\u30c8\u304b\u3089\u59cb\u307e\u308b\u305f\u3081\u3001\u5148\u306b\u30c7\u30d0\u30a4\u30b9\u3092\u914d\u7f6e\u3057\u3001\u30b7\u30fc\u30f3\u304b\u3089\u30a2\u30d0\u30bf\u30fc\u306e\u30eb\u30fc\u30c8\u3068\u30c7\u30d0\u30a4\u30b9\u3092\u3053\u306e\u6b04\u306b\u30c9\u30e9\u30c3\u30b0\u3057\u3066\u304f\u3060\u3055\u3044\u3002\u4e21\u65b9\u7a7a\u6b04\u306a\u3089\u30eb\u30fc\u30c8\u76f4\u4e0b\u306e\u30d7\u30ec\u30cf\u30d6\u3068\u3057\u3066\u6271\u3044\u307e\u3059\u3002", "\u5f53\u60a8\u628a\u5c42\u76f4\u63a5\u5408\u5e76\u5230 Avatar \u7684 FX \u63a7\u5236\u5668\u65f6\u4f7f\u7528\u3002\u8def\u5f84\u4ece Avatar \u6839\u5bf9\u8c61\u5f00\u59cb\uff0c\u8bf7\u5148\u653e\u597d\u8bbe\u5907\uff0c\u518d\u628a\u573a\u666f\u4e2d\u7684 Avatar \u6839\u5bf9\u8c61\u548c\u8bbe\u5907\u62d6\u5230\u4e0b\u9762\u7684\u6846\u4e2d\u3002\u4e24\u8005\u90fd\u7559\u7a7a\u5219\u89c6\u4e3a\u9884\u5236\u4f53\u4f4d\u4e8e\u6839\u5bf9\u8c61\u4e0b\u3002", "\u7576\u60a8\u628a\u5716\u5c64\u76f4\u63a5\u5408\u4f75\u5230 Avatar \u7684 FX \u63a7\u5236\u5668\u6642\u4f7f\u7528\u3002\u8def\u5f91\u5f9e Avatar \u6839\u7269\u4ef6\u958b\u59cb\uff0c\u8acb\u5148\u653e\u597d\u88dd\u7f6e\uff0c\u518d\u628a\u5834\u666f\u4e2d\u7684 Avatar \u6839\u7269\u4ef6\u548c\u88dd\u7f6e\u62d6\u5230\u4e0b\u9762\u7684\u6b04\u4f4d\u4e2d\u3002\u5169\u8005\u90fd\u7559\u7a7a\u5247\u8996\u70ba Prefab \u4f4d\u65bc\u6839\u7269\u4ef6\u4e0b\u3002", "\ub808\uc774\uc5b4\ub97c \uc544\ubc14\ud0c0\uc758 FX \ucee8\ud2b8\ub864\ub7ec\uc5d0 \uc9c1\uc811 \ubcd1\ud569\ud558\ub294 \uacbd\uc6b0\uc5d0 \uc0ac\uc6a9\ud558\uc138\uc694. \uacbd\ub85c\ub294 \uc544\ubc14\ud0c0 \ub8e8\ud2b8\uc5d0\uc11c \uc2dc\uc791\ud558\ubbc0\ub85c \uba3c\uc800 \uae30\uae30\ub97c \ub458 \uc704\uce58\uc5d0 \ub193\uc740 \ub2e4\uc74c, \uc52c\uc5d0\uc11c \uc544\ubc14\ud0c0 \ub8e8\ud2b8\uc640 \uae30\uae30\ub97c \uc774 \uce78\ub4e4\ub85c \ub4dc\ub798\uadf8\ud558\uc138\uc694. \ub458 \ub2e4 \ube44\uc6cc \ub450\uba74 \ub8e8\ud2b8 \uc544\ub798\uc758 \ud504\ub9ac\ud339\uc73c\ub85c \uac04\uc8fc\ud569\ub2c8\ub2e4.", "Use se voc\u00ea mesclar as camadas direto no controlador FX do seu avatar. Os caminhos come\u00e7am na raiz do avatar: coloque primeiro o dispositivo onde ele ficar\u00e1 e arraste a raiz do avatar e o dispositivo da cena para estes campos. Deixe ambos vazios para usar o prefab na raiz.", "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435, \u0435\u0441\u043b\u0438 \u0432\u044b \u0441\u043b\u0438\u0432\u0430\u0435\u0442\u0435 \u0441\u043b\u043e\u0438 \u043f\u0440\u044f\u043c\u043e \u0441 FX-\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440\u043e\u043c \u0430\u0432\u0430\u0442\u0430\u0440\u0430. \u041f\u0443\u0442\u0438 \u043d\u0430\u0447\u0438\u043d\u0430\u044e\u0442\u0441\u044f \u043e\u0442 \u043a\u043e\u0440\u043d\u044f \u0430\u0432\u0430\u0442\u0430\u0440\u0430: \u0441\u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u043e\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u043d\u0430 \u043c\u0435\u0441\u0442\u043e, \u0437\u0430\u0442\u0435\u043c \u043f\u0435\u0440\u0435\u0442\u0430\u0449\u0438\u0442\u0435 \u043a\u043e\u0440\u0435\u043d\u044c \u0430\u0432\u0430\u0442\u0430\u0440\u0430 \u0438 \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u0438\u0437 \u0441\u0446\u0435\u043d\u044b \u0432 \u044d\u0442\u0438 \u043f\u043e\u043b\u044f. \u0415\u0441\u043b\u0438 \u043e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u043e\u0431\u0430 \u043f\u0443\u0441\u0442\u044b\u043c\u0438, \u043f\u0440\u0435\u0444\u0430\u0431 \u0441\u0447\u0438\u0442\u0430\u0435\u0442\u0441\u044f \u043b\u0435\u0436\u0430\u0449\u0438\u043c \u0432 \u043a\u043e\u0440\u043d\u0435." } },
            { "avatar_root", new[] { "Avatar root", "Racine de l'avatar", "Ra\u00edz del avatar", "Avatar-Wurzel", "\u30a2\u30d0\u30bf\u30fc\u306e\u30eb\u30fc\u30c8", "Avatar \u6839\u5bf9\u8c61", "Avatar \u6839\u7269\u4ef6", "\uc544\ubc14\ud0c0 \ub8e8\ud2b8", "Raiz do avatar", "\u041a\u043e\u0440\u0435\u043d\u044c \u0430\u0432\u0430\u0442\u0430\u0440\u0430" } },
            { "device_in_scene", new[] { "Device in scene", "Appareil dans la sc\u00e8ne", "Dispositivo en la escena", "Ger\u00e4t in der Szene", "\u30b7\u30fc\u30f3\u5185\u306e\u30c7\u30d0\u30a4\u30b9", "\u573a\u666f\u4e2d\u7684\u8bbe\u5907", "\u5834\u666f\u4e2d\u7684\u88dd\u7f6e", "\uc52c\uc758 \uae30\uae30", "Dispositivo na cena", "\u0423\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u0432 \u0441\u0446\u0435\u043d\u0435" } },
            { "anim_path", new[] { "Animation path:", "Chemin d'animation :", "Ruta de animaci\u00f3n:", "Animationspfad:", "\u30a2\u30cb\u30e1\u30fc\u30b7\u30e7\u30f3\u30d1\u30b9:", "\u52a8\u753b\u8def\u5f84\uff1a", "\u52d5\u756b\u8def\u5f91\uff1a", "\uc560\ub2c8\uba54\uc774\uc158 \uacbd\ub85c:", "Caminho da anima\u00e7\u00e3o:", "\u041f\u0443\u0442\u044c \u0430\u043d\u0438\u043c\u0430\u0446\u0438\u0438:" } },
            { "rel_prop", new[] { "(relative to the prop)", "(relatif \u00e0 l'objet)", "(relativa al objeto)", "(relativ zum Prop)", "\uff08\u30d7\u30ed\u30c3\u30d7\u57fa\u6e96\uff09", "\uff08\u76f8\u5bf9\u4e8e\u9053\u5177\uff09", "\uff08\u76f8\u5c0d\u65bc\u9053\u5177\uff09", "(\ud504\ub86d \uae30\uc900)", "(relativo ao objeto)", "(\u043e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u043e \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u0430)" } },
            { "not_inside", new[] { "(device is not inside the avatar root)", "(l'appareil n'est pas dans la racine de l'avatar)", "(el dispositivo no est\u00e1 dentro de la ra\u00edz del avatar)", "(Ger\u00e4t liegt nicht in der Avatar-Wurzel)", "\uff08\u30c7\u30d0\u30a4\u30b9\u304c\u30a2\u30d0\u30bf\u30fc\u306e\u30eb\u30fc\u30c8\u5185\u306b\u3042\u308a\u307e\u305b\u3093\uff09", "\uff08\u8bbe\u5907\u4e0d\u5728 Avatar \u6839\u5bf9\u8c61\u5185\uff09", "\uff08\u88dd\u7f6e\u4e0d\u5728 Avatar \u6839\u7269\u4ef6\u5167\uff09", "(\uae30\uae30\uac00 \uc544\ubc14\ud0c0 \ub8e8\ud2b8 \uc548\uc5d0 \uc5c6\uc2b5\ub2c8\ub2e4)", "(o dispositivo n\u00e3o est\u00e1 dentro da raiz do avatar)", "(\u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u043e \u043d\u0435 \u043d\u0430\u0445\u043e\u0434\u0438\u0442\u0441\u044f \u0432\u043d\u0443\u0442\u0440\u0438 \u043a\u043e\u0440\u043d\u044f \u0430\u0432\u0430\u0442\u0430\u0440\u0430)" } },
            { "options", new[] { "Options", "Options", "Opciones", "Optionen", "\u30aa\u30d7\u30b7\u30e7\u30f3", "\u9009\u9879", "\u9078\u9805", "\uc635\uc158", "Op\u00e7\u00f5es", "\u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b" } },
            { "wd", new[] { "Write Defaults ON", "Write Defaults ACTIV\u00c9", "Write Defaults ACTIVADO", "Write Defaults AN", "Write Defaults ON", "Write Defaults \u5f00\u542f", "Write Defaults \u958b\u555f", "Write Defaults \ucf1c\uae30", "Write Defaults ATIVADO", "Write Defaults \u0412\u041a\u041b" } },
            { "wd_tip", new[] { "Leave OFF unless the rest of your FX controller uses Write Defaults ON. The layers work either way.", "Laissez d\u00e9sactiv\u00e9 sauf si le reste de votre contr\u00f4leur FX utilise Write Defaults activ\u00e9. Les couches fonctionnent dans les deux cas.", "D\u00e9jalo desactivado salvo que el resto de tu controlador FX use Write Defaults activado. Las capas funcionan en ambos casos.", "Aus lassen, au\u00dfer der Rest deines FX-Controllers nutzt Write Defaults AN. Die Layer funktionieren in beiden F\u00e4llen.", "FX\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc\u306e\u4ed6\u306e\u90e8\u5206\u304c Write Defaults ON \u3067\u306a\u3044\u9650\u308a OFF \u306e\u307e\u307e\u306b\u3057\u3066\u304f\u3060\u3055\u3044\u3002\u3069\u3061\u3089\u3067\u3082\u52d5\u4f5c\u3057\u307e\u3059\u3002", "\u9664\u975e\u60a8\u7684 FX \u63a7\u5236\u5668\u5176\u4f59\u90e8\u5206\u4f7f\u7528 Write Defaults \u5f00\u542f\uff0c\u5426\u5219\u8bf7\u4fdd\u6301\u5173\u95ed\u3002\u4e24\u79cd\u65b9\u5f0f\u90fd\u80fd\u5de5\u4f5c\u3002", "\u9664\u975e FX \u63a7\u5236\u5668\u7684\u5176\u4ed6\u90e8\u5206\u4f7f\u7528 Write Defaults \u958b\u555f\uff0c\u5426\u5247\u8acb\u4fdd\u6301\u95dc\u9589\u3002\u5169\u7a2e\u8a2d\u5b9a\u4e0b\u5716\u5c64\u90fd\u80fd\u904b\u4f5c\u3002", "FX \ucee8\ud2b8\ub864\ub7ec\uc758 \ub098\uba38\uc9c0 \ubd80\ubd84\uc774 Write Defaults \ucf1c\uc9d0\uc744 \uc4f0\uc9c0 \uc54a\ub294\ub2e4\uba74 \uaebc \ub450\uc138\uc694. \uc5b4\ub290 \ucabd\uc774\ub4e0 \ub808\uc774\uc5b4\ub294 \ub3d9\uc791\ud569\ub2c8\ub2e4.", "Deixe DESATIVADO, a menos que o restante do seu controlador FX use Write Defaults ATIVADO. As camadas funcionam nos dois casos.", "\u041e\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u043d\u044b\u043c, \u0435\u0441\u043b\u0438 \u043e\u0441\u0442\u0430\u043b\u044c\u043d\u0430\u044f \u0447\u0430\u0441\u0442\u044c \u0432\u0430\u0448\u0435\u0433\u043e FX-\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440\u0430 \u043d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 Write Defaults \u0412\u041a\u041b. \u0421\u043b\u043e\u0438 \u0440\u0430\u0431\u043e\u0442\u0430\u044e\u0442 \u0432 \u043e\u0431\u043e\u0438\u0445 \u0441\u043b\u0443\u0447\u0430\u044f\u0445." } },
            { "timeout", new[] { "No-data timeout (s)", "D\u00e9lai sans donn\u00e9es (s)", "Tiempo sin datos (s)", "Timeout ohne Daten (s)", "\u30c7\u30fc\u30bf\u306a\u3057\u30bf\u30a4\u30e0\u30a2\u30a6\u30c8\uff08\u79d2\uff09", "\u65e0\u6570\u636e\u8d85\u65f6\uff08\u79d2\uff09", "\u7121\u8cc7\u6599\u903e\u6642\uff08\u79d2\uff09", "\ub370\uc774\ud130 \uc5c6\uc74c \uc81c\ud55c \uc2dc\uac04(\ucd08)", "Tempo limite sem dados (s)", "\u0422\u0430\u0439\u043c-\u0430\u0443\u0442 \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u044f \u0434\u0430\u043d\u043d\u044b\u0445 (\u0441)" } },
            { "timeout_tip", new[] { "How long the heartbeat may stay silent before the screen is covered with '--'.", "Dur\u00e9e pendant laquelle le signal de vie peut rester muet avant que l'\u00e9cran affiche '--'.", "Cu\u00e1nto tiempo puede callar el latido antes de cubrir la pantalla con '--'.", "Wie lange der Heartbeat ausbleiben darf, bevor der Bildschirm mit '--' abgedeckt wird.", "\u30cf\u30fc\u30c8\u30d3\u30fc\u30c8\u304c\u9014\u7d76\u3048\u3066\u304b\u3089\u753b\u9762\u3092\u300c--\u300d\u3067\u8986\u3046\u307e\u3067\u306e\u6642\u9593\u3067\u3059\u3002", "\u5fc3\u8df3\u4fe1\u53f7\u4e2d\u65ad\u591a\u4e45\u540e\uff0c\u5c4f\u5e55\u4f1a\u88ab\u201c--\u201d\u8986\u76d6\u3002", "\u5fc3\u8df3\u8a0a\u865f\u53ef\u975c\u9ed8\u591a\u4e45\uff0c\u8d85\u904e\u5f8c\u756b\u9762\u6703\u88ab\u300c--\u300d\u8986\u84cb\u3002", "\ud558\ud2b8\ube44\ud2b8 \uc2e0\ud638\uac00 \uc774 \uc2dc\uac04 \ub3d9\uc548 \ub04a\uae30\uba74 \ud654\uba74\uc774 '--'\ub85c \ub36e\uc785\ub2c8\ub2e4.", "Por quanto tempo o sinal de vida pode ficar em sil\u00eancio antes de a tela ser coberta por '--'.", "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0441\u0438\u0433\u043d\u0430\u043b \u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u0438 \u043c\u043e\u0436\u0435\u0442 \u043c\u043e\u043b\u0447\u0430\u0442\u044c, \u043f\u0440\u0435\u0436\u0434\u0435 \u0447\u0435\u043c \u044d\u043a\u0440\u0430\u043d \u0437\u0430\u043a\u0440\u043e\u0435\u0442\u0441\u044f \u0437\u043d\u0430\u0447\u043a\u043e\u043c '--'." } },
            { "words_lang", new[] { "Simple-mode language", "Langue du mode simple", "Idioma del modo simple", "Sprache im einfachen Modus", "\u304b\u3093\u305f\u3093\u30e2\u30fc\u30c9\u306e\u8a00\u8a9e", "\u7b80\u6613\u6a21\u5f0f\u8bed\u8a00", "\u7c21\u6613\u6a21\u5f0f\u8a9e\u8a00", "\uac04\ub2e8 \ubaa8\ub4dc \uc5b8\uc5b4", "Idioma do modo simples", "\u042f\u0437\u044b\u043a \u043f\u0440\u043e\u0441\u0442\u043e\u0433\u043e \u0440\u0435\u0436\u0438\u043c\u0430" } },
            { "words_lang_tip", new[] { "Language of the plain-words panel. Numbers, LO/HI and units are the same in every language.", "Langue du panneau de mots simples. Les chiffres, LO/HI et les unit\u00e9s sont identiques dans toutes les langues.", "Idioma del panel de palabras sencillas. Los n\u00fameros, LO/HI y las unidades son iguales en todos los idiomas.", "Sprache des Klartext-Panels. Zahlen, LO/HI und Einheiten sind in allen Sprachen gleich.", "\u304b\u3093\u305f\u3093\u30e2\u30fc\u30c9\u306e\u6587\u8a00\u306e\u8a00\u8a9e\u3067\u3059\u3002\u6570\u5b57\u3001LO/HI\u3001\u5358\u4f4d\u306f\u3069\u306e\u8a00\u8a9e\u3067\u3082\u5171\u901a\u3067\u3059\u3002", "\u7b80\u6613\u6a21\u5f0f\u6587\u5b57\u9762\u677f\u7684\u8bed\u8a00\u3002\u6570\u5b57\u3001LO/HI \u548c\u5355\u4f4d\u5728\u6240\u6709\u8bed\u8a00\u4e2d\u90fd\u76f8\u540c\u3002", "\u6587\u5b57\u9762\u677f\u7684\u8a9e\u8a00\u3002\u6578\u5b57\u3001LO/HI \u8207\u55ae\u4f4d\u5728\u6240\u6709\u8a9e\u8a00\u4e2d\u90fd\u76f8\u540c\u3002", "\ubb38\uad6c \ud328\ub110\uc758 \uc5b8\uc5b4\uc785\ub2c8\ub2e4. \uc22b\uc790, LO/HI, \ub2e8\uc704\ub294 \ubaa8\ub4e0 \uc5b8\uc5b4\uc5d0\uc11c \uac19\uc2b5\ub2c8\ub2e4.", "Idioma do painel de palavras. N\u00fameros, LO/HI e unidades s\u00e3o iguais em todos os idiomas.", "\u042f\u0437\u044b\u043a \u043f\u0430\u043d\u0435\u043b\u0438 \u0441\u043e \u0441\u043b\u043e\u0432\u0430\u043c\u0438. \u0426\u0438\u0444\u0440\u044b, LO/HI \u0438 \u0435\u0434\u0438\u043d\u0438\u0446\u044b \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u043e\u0434\u0438\u043d\u0430\u043a\u043e\u0432\u044b \u0432\u043e \u0432\u0441\u0435\u0445 \u044f\u0437\u044b\u043a\u0430\u0445." } },
            { "bridge_words", new[] { "Let the bridge app rotate to the words panel (+1 sync bit)", "", "", "", "", "", "\u8b93\u6a4b\u63a5\u7a0b\u5f0f\u8f2a\u64ad\u5230\u6587\u5b57\u9762\u677f\uff08+1 \u540c\u6b65\u4f4d\u5143\uff09", "\ube0c\ub9ac\uc9c0 \uc571\uc774 \ubb38\uad6c \ud328\ub110\ub85c \uc21c\ud658\ud558\ub3c4\ub85d \ud5c8\uc6a9(\ub3d9\uae30\ud654 \ube44\ud2b8 +1)", "Deixar o app ponte revezar para o painel de palavras (+1 bit de sincroniza\u00e7\u00e3o)", "\u0420\u0430\u0437\u0440\u0435\u0448\u0438\u0442\u044c \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044e-\u043c\u043e\u0441\u0442\u0443 \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u0442\u044c\u0441\u044f \u043d\u0430 \u043f\u0430\u043d\u0435\u043b\u044c \u0441\u043b\u043e\u0432 (+1 \u0431\u0438\u0442 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438)" } },
            { "bridge_words_tip", new[] { "Adds a BG_Words Bool and lets the bridge's 'rotate' mode (mmol/L, mg/dL, words) switch the screen to the plain words. The panel's language is still set here or by the menu dial. Off = the bridge can only alternate the two units.", "", "", "", "", "", "\u65b0\u589e\u4e00\u500b BG_Words Bool \u53c3\u6578\uff0c\u8b93\u6a4b\u63a5\u7a0b\u5f0f\u7684\u300c\u8f2a\u64ad\u300d\u6a21\u5f0f\uff08mmol/L\u3001mg/dL\u3001\u6587\u5b57\uff09\u80fd\u628a\u756b\u9762\u5207\u63db\u5230\u6587\u5b57\u9762\u677f\u3002\u9762\u677f\u7684\u8a9e\u8a00\u4ecd\u5728\u6b64\u8655\u6216\u7531\u9078\u55ae\u8f49\u76e4\u8a2d\u5b9a\u3002\u95dc\u9589\u6642\uff0c\u6a4b\u63a5\u7a0b\u5f0f\u53ea\u80fd\u5728\u5169\u7a2e\u55ae\u4f4d\u4e4b\u9593\u4ea4\u66ff\u3002", "BG_Words Bool \ud30c\ub77c\ubbf8\ud130\ub97c \ucd94\uac00\ud558\uc5ec \ube0c\ub9ac\uc9c0 \uc571\uc758 '\uc21c\ud658' \ubaa8\ub4dc(mmol/L, mg/dL, \ubb38\uad6c)\uac00 \ud654\uba74\uc744 \ubb38\uad6c \ud328\ub110\ub85c \uc804\ud658\ud560 \uc218 \uc788\uac8c \ud569\ub2c8\ub2e4. \ud328\ub110 \uc5b8\uc5b4\ub294 \uc5ec\uae30\uc11c \ub610\ub294 \uba54\ub274 \ub2e4\uc774\uc5bc\ub85c \uc815\ud569\ub2c8\ub2e4. \ub044\uba74 \ube0c\ub9ac\uc9c0\ub294 \ub450 \ub2e8\uc704\ub9cc \ubc88\uac08\uc544 \ud45c\uc2dc\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4.", "Adiciona um Bool BG_Words e permite que o modo 'revezar' do app ponte (mmol/L, mg/dL, palavras) troque a tela para as palavras simples. O idioma do painel continua sendo definido aqui ou pelo seletor no menu. Desativado = o app s\u00f3 pode alternar as duas unidades.", "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440 BG_Words (Bool) \u0438 \u043f\u043e\u0437\u0432\u043e\u043b\u044f\u0435\u0442 \u0440\u0435\u0436\u0438\u043c\u0443 \u00ab\u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f\u00bb \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f-\u043c\u043e\u0441\u0442\u0430 (mmol/L, mg/dL, \u0441\u043b\u043e\u0432\u0430) \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0430\u0442\u044c \u044d\u043a\u0440\u0430\u043d \u043d\u0430 \u043f\u0430\u043d\u0435\u043b\u044c \u0441\u043b\u043e\u0432. \u042f\u0437\u044b\u043a \u043f\u0430\u043d\u0435\u043b\u0438 \u043f\u043e-\u043f\u0440\u0435\u0436\u043d\u0435\u043c\u0443 \u0437\u0430\u0434\u0430\u0451\u0442\u0441\u044f \u0437\u0434\u0435\u0441\u044c \u0438\u043b\u0438 \u0434\u0438\u0441\u043a\u043e\u043c \u0432 \u043c\u0435\u043d\u044e. \u0415\u0441\u043b\u0438 \u0432\u044b\u043a\u043b\u044e\u0447\u0435\u043d\u043e, \u043c\u043e\u0441\u0442 \u043c\u043e\u0436\u0435\u0442 \u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0435\u0440\u0435\u0434\u043e\u0432\u0430\u0442\u044c \u0434\u0432\u0435 \u0435\u0434\u0438\u043d\u0438\u0446\u044b." } },
            { "menu_lang", new[] { "Language dial in the VRChat menu (+8 sync bits)", "", "", "", "", "", "\u5728 VRChat \u9078\u55ae\u4e2d\u52a0\u5165\u8a9e\u8a00\u8f49\u76e4\uff08+8 \u540c\u6b65\u4f4d\u5143\uff09", "VRChat \uba54\ub274\uc5d0 \uc5b8\uc5b4 \ub2e4\uc774\uc5bc \ucd94\uac00(\ub3d9\uae30\ud654 \ube44\ud2b8 +8)", "Seletor de idioma no menu do VRChat (+8 bits de sincroniza\u00e7\u00e3o)", "\u0414\u0438\u0441\u043a \u0432\u044b\u0431\u043e\u0440\u0430 \u044f\u0437\u044b\u043a\u0430 \u0432 \u043c\u0435\u043d\u044e VRChat (+8 \u0431\u0438\u0442 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438)" } },
            { "menu_lang_tip", new[] { "Adds a Radial Puppet to your menu (BG_LangSel, a Float) and a layer. Turn the dial to change the plain-words language: each tenth is one language (en, fr, es, de, ja, zh-Hans, zh-Hant, ko, pt-BR, ru).", "", "", "", "", "", "\u5728\u9078\u55ae\u4e2d\u52a0\u5165\u4e00\u500b Radial Puppet\uff08BG_LangSel\uff0cFloat \u53c3\u6578\uff09\u548c\u4e00\u500b\u5716\u5c64\u3002\u8f49\u52d5\u8f49\u76e4\u5373\u53ef\u5207\u63db\u6587\u5b57\u9762\u677f\u7684\u8a9e\u8a00\uff1a\u6bcf\u5341\u5206\u4e4b\u4e00\u5c0d\u61c9\u4e00\u7a2e\u8a9e\u8a00\uff08en\u3001fr\u3001es\u3001de\u3001ja\u3001zh-Hans\u3001zh-Hant\u3001ko\u3001pt-BR\u3001ru\uff09\u3002", "\uba54\ub274\uc5d0 Radial Puppet(BG_LangSel, Float)\uacfc \ub808\uc774\uc5b4\ub97c \ucd94\uac00\ud569\ub2c8\ub2e4. \ub2e4\uc774\uc5bc\uc744 \ub3cc\ub824 \ubb38\uad6c \ud328\ub110\uc758 \uc5b8\uc5b4\ub97c \ubc14\uafc9\ub2c8\ub2e4. 10\ubd84\uc758 1 \uad6c\uac04\ub9c8\ub2e4 \ud55c \uc5b8\uc5b4\uc785\ub2c8\ub2e4(en, fr, es, de, ja, zh-Hans, zh-Hant, ko, pt-BR, ru).", "Adiciona um Radial Puppet ao seu menu (BG_LangSel, um Float) e uma camada. Gire o seletor para mudar o idioma do painel de palavras: cada d\u00e9cimo \u00e9 um idioma (en, fr, es, de, ja, zh-Hans, zh-Hant, ko, pt-BR, ru).", "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0432 \u043c\u0435\u043d\u044e Radial Puppet (BG_LangSel, Float) \u0438 \u0441\u043b\u043e\u0439. \u041f\u043e\u0432\u043e\u0440\u0430\u0447\u0438\u0432\u0430\u0439\u0442\u0435 \u0434\u0438\u0441\u043a, \u0447\u0442\u043e\u0431\u044b \u043c\u0435\u043d\u044f\u0442\u044c \u044f\u0437\u044b\u043a \u043f\u0430\u043d\u0435\u043b\u0438 \u0441\u043b\u043e\u0432: \u043a\u0430\u0436\u0434\u0430\u044f \u0434\u0435\u0441\u044f\u0442\u0430\u044f \u0447\u0430\u0441\u0442\u044c \u2014 \u043e\u0434\u0438\u043d \u044f\u0437\u044b\u043a (en, fr, es, de, ja, zh-Hans, zh-Hant, ko, pt-BR, ru)." } },
            { "step3", new[] { "3. Build the animator layers", "3. Cr\u00e9er les couches d'animation", "3. Crear las capas del animador", "3. Animator-Layer erstellen", "3. \u30a2\u30cb\u30e1\u30fc\u30bf\u30fc\u30ec\u30a4\u30e4\u30fc\u3092\u4f5c\u6210", "3. \u751f\u6210\u52a8\u753b\u5c42", "3. \u5efa\u7acb\u52d5\u756b\u5716\u5c64", "3. \uc560\ub2c8\uba54\uc774\ud130 \ub808\uc774\uc5b4 \ub9cc\ub4e4\uae30", "3. Criar as camadas do animator", "3. \u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0441\u043b\u043e\u0438 \u0430\u043d\u0438\u043c\u0430\u0442\u043e\u0440\u0430" } },
            { "btn_standalone", new[] { "Create a standalone controller (safe, for testing)", "Cr\u00e9er un contr\u00f4leur autonome (s\u00fbr, pour tester)", "Crear un controlador independiente (seguro, para pruebas)", "Eigenst\u00e4ndigen Controller erstellen (sicher, zum Testen)", "\u5358\u72ec\u306e\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc\u3092\u4f5c\u6210\uff08\u5b89\u5168\u30fb\u30c6\u30b9\u30c8\u7528\uff09", "\u521b\u5efa\u72ec\u7acb\u63a7\u5236\u5668\uff08\u5b89\u5168\uff0c\u7528\u4e8e\u6d4b\u8bd5\uff09", "\u5efa\u7acb\u7368\u7acb\u63a7\u5236\u5668\uff08\u5b89\u5168\uff0c\u4f9b\u6e2c\u8a66\u7528\uff09", "\ub3c5\ub9bd \ucee8\ud2b8\ub864\ub7ec \ub9cc\ub4e4\uae30(\uc548\uc804, \ud14c\uc2a4\ud2b8\uc6a9)", "Criar um controlador independente (seguro, para testes)", "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u044b\u0439 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440 (\u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u043e, \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u043e\u0432)" } },
            { "your_fx", new[] { "Your FX controller", "Votre contr\u00f4leur FX", "Tu controlador FX", "Dein FX-Controller", "\u3042\u306a\u305f\u306eFX\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc", "\u60a8\u7684 FX \u63a7\u5236\u5668", "\u60a8\u7684 FX \u63a7\u5236\u5668", "\ub0b4 FX \ucee8\ud2b8\ub864\ub7ec", "Seu controlador FX", "\u0412\u0430\u0448 FX-\u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440" } },
            { "backup", new[] { "Make a backup copy first", "Faire d'abord une copie de sauvegarde", "Hacer primero una copia de seguridad", "Zuerst eine Sicherungskopie anlegen", "\u5148\u306b\u30d0\u30c3\u30af\u30a2\u30c3\u30d7\u3092\u4f5c\u6210", "\u5148\u521b\u5efa\u5907\u4efd\u526f\u672c", "\u5148\u5efa\u7acb\u5099\u4efd", "\uba3c\uc800 \ubc31\uc5c5\ubcf8 \ub9cc\ub4e4\uae30", "Fazer uma c\u00f3pia de backup antes", "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0440\u0435\u0437\u0435\u0440\u0432\u043d\u0443\u044e \u043a\u043e\u043f\u0438\u044e" } },
            { "btn_add", new[] { "Add layers + parameters to my controller", "Ajouter les couches + param\u00e8tres \u00e0 mon contr\u00f4leur", "A\u00f1adir capas + par\u00e1metros a mi controlador", "Layer + Parameter zu meinem Controller hinzuf\u00fcgen", "\u81ea\u5206\u306e\u30b3\u30f3\u30c8\u30ed\u30fc\u30e9\u30fc\u306b\u30ec\u30a4\u30e4\u30fc\u3068\u30d1\u30e9\u30e1\u30fc\u30bf\u30fc\u3092\u8ffd\u52a0", "\u5411\u6211\u7684\u63a7\u5236\u5668\u6dfb\u52a0\u5c42\u548c\u53c2\u6570", "\u5c07\u5716\u5c64\u8207\u53c3\u6578\u52a0\u5165\u6211\u7684\u63a7\u5236\u5668", "\ub0b4 \ucee8\ud2b8\ub864\ub7ec\uc5d0 \ub808\uc774\uc5b4\uc640 \ud30c\ub77c\ubbf8\ud130 \ucd94\uac00", "Adicionar camadas e par\u00e2metros ao meu controlador", "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0441\u043b\u043e\u0438 \u0438 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0432 \u043c\u043e\u0439 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u043b\u0435\u0440" } },
            { "help_layers", new[] { "Adds the layers named BG_... and the BG_ parameters. Existing BG_ layers are replaced, so you can rebuild after moving the device. Your other layers are not touched.", "Ajoute les couches BG_... et les param\u00e8tres BG_. Les couches BG_ existantes sont remplac\u00e9es : vous pouvez reconstruire apr\u00e8s avoir d\u00e9plac\u00e9 l'appareil. Vos autres couches ne sont pas modifi\u00e9es.", "A\u00f1ade las capas BG_... y los par\u00e1metros BG_. Las capas BG_ existentes se reemplazan, as\u00ed que puedes regenerar tras mover el dispositivo. Tus dem\u00e1s capas no se tocan.", "F\u00fcgt die Layer BG_... und die BG_-Parameter hinzu. Vorhandene BG_-Layer werden ersetzt, du kannst also nach dem Verschieben neu erstellen. Deine anderen Layer bleiben unber\u00fchrt.", "BG_ \u3067\u59cb\u307e\u308b\u30ec\u30a4\u30e4\u30fc\u3068\u30d1\u30e9\u30e1\u30fc\u30bf\u30fc\u3092\u8ffd\u52a0\u3057\u307e\u3059\u3002\u65e2\u5b58\u306e BG_ \u30ec\u30a4\u30e4\u30fc\u306f\u7f6e\u304d\u63db\u3048\u3089\u308c\u308b\u305f\u3081\u3001\u30c7\u30d0\u30a4\u30b9\u3092\u52d5\u304b\u3057\u305f\u5f8c\u306b\u518d\u4f5c\u6210\u3067\u304d\u307e\u3059\u3002\u305d\u306e\u4ed6\u306e\u30ec\u30a4\u30e4\u30fc\u306b\u306f\u89e6\u308c\u307e\u305b\u3093\u3002", "\u6dfb\u52a0\u4ee5 BG_ \u5f00\u5934\u7684\u5c42\u548c\u53c2\u6570\u3002\u5df2\u6709\u7684 BG_ \u5c42\u4f1a\u88ab\u66ff\u6362\uff0c\u56e0\u6b64\u79fb\u52a8\u8bbe\u5907\u540e\u53ef\u91cd\u65b0\u751f\u6210\u3002\u60a8\u7684\u5176\u4ed6\u5c42\u4e0d\u4f1a\u88ab\u6539\u52a8\u3002", "\u52a0\u5165\u540d\u70ba BG_... \u7684\u5716\u5c64\u548c BG_ \u53c3\u6578\u3002\u65e2\u6709\u7684 BG_ \u5716\u5c64\u6703\u88ab\u53d6\u4ee3\uff0c\u56e0\u6b64\u79fb\u52d5\u88dd\u7f6e\u5f8c\u53ef\u4ee5\u91cd\u65b0\u5efa\u7acb\u3002\u60a8\u7684\u5176\u4ed6\u5716\u5c64\u4e0d\u6703\u88ab\u66f4\u52d5\u3002", "BG_...\ub77c\ub294 \uc774\ub984\uc758 \ub808\uc774\uc5b4\uc640 BG_ \ud30c\ub77c\ubbf8\ud130\ub97c \ucd94\uac00\ud569\ub2c8\ub2e4. \uae30\uc874 BG_ \ub808\uc774\uc5b4\ub294 \uad50\uccb4\ub418\ubbc0\ub85c \uae30\uae30\ub97c \uc62e\uae34 \ub4a4 \ub2e4\uc2dc \ub9cc\ub4e4 \uc218 \uc788\uc2b5\ub2c8\ub2e4. \ub2e4\ub978 \ub808\uc774\uc5b4\ub294 \uac74\ub4dc\ub9ac\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.", "Adiciona as camadas chamadas BG_... e os par\u00e2metros BG_. As camadas BG_ existentes s\u00e3o substitu\u00eddas, ent\u00e3o voc\u00ea pode refazer depois de mover o dispositivo. Suas outras camadas n\u00e3o s\u00e3o alteradas.", "\u0414\u043e\u0431\u0430\u0432\u043b\u044f\u0435\u0442 \u0441\u043b\u043e\u0438 \u0441 \u0438\u043c\u0435\u043d\u0430\u043c\u0438 BG_... \u0438 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b BG_. \u0421\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u044e\u0449\u0438\u0435 \u0441\u043b\u043e\u0438 BG_ \u0437\u0430\u043c\u0435\u043d\u044f\u044e\u0442\u0441\u044f, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u043c\u043e\u0436\u043d\u043e \u043f\u0435\u0440\u0435\u0441\u043e\u0431\u0440\u0430\u0442\u044c \u043f\u043e\u0441\u043b\u0435 \u043f\u0435\u0440\u0435\u043c\u0435\u0449\u0435\u043d\u0438\u044f \u0443\u0441\u0442\u0440\u043e\u0439\u0441\u0442\u0432\u0430. \u041e\u0441\u0442\u0430\u043b\u044c\u043d\u044b\u0435 \u0432\u0430\u0448\u0438 \u0441\u043b\u043e\u0438 \u043d\u0435 \u0437\u0430\u0442\u0440\u0430\u0433\u0438\u0432\u0430\u044e\u0442\u0441\u044f." } },
            { "step4", new[] { "4. Expression Parameters", "4. Param\u00e8tres d'expression", "4. Par\u00e1metros de expresi\u00f3n", "4. Expression Parameters", "4. \u30a8\u30af\u30b9\u30d7\u30ec\u30c3\u30b7\u30e7\u30f3\u30d1\u30e9\u30e1\u30fc\u30bf\u30fc", "4. \u8868\u60c5\u53c2\u6570", "4. Expression Parameters", "4. Expression Parameters", "4. Expression Parameters", "4. Expression Parameters" } },
            { "step4_help", new[] { "Add these to your avatar's Expression Parameters. Use the button below to make ready-made assets, or copy the list, or see PARAMETERS.txt.", "Ajoutez-les aux Expression Parameters de votre avatar. Utilisez le bouton ci-dessous pour cr\u00e9er des assets pr\u00eats \u00e0 l'emploi, ou copiez la liste, ou consultez PARAMETERS.txt.", "A\u00f1\u00e1delos a los Expression Parameters de tu avatar. Usa el bot\u00f3n de abajo para crear los assets, o copia la lista, o mira PARAMETERS.txt.", "F\u00fcge sie den Expression Parameters deines Avatars hinzu. Mit der Schaltfl\u00e4che unten entstehen fertige Assets; oder kopiere die Liste, oder siehe PARAMETERS.txt.", "\u30a2\u30d0\u30bf\u30fc\u306eExpression Parameters\u306b\u8ffd\u52a0\u3057\u3066\u304f\u3060\u3055\u3044\u3002\u4e0b\u306e\u30dc\u30bf\u30f3\u3067\u7528\u610f\u6e08\u307f\u306e\u30a2\u30bb\u30c3\u30c8\u3092\u4f5c\u6210\u3059\u308b\u304b\u3001\u30ea\u30b9\u30c8\u3092\u30b3\u30d4\u30fc\u3001\u307e\u305f\u306fPARAMETERS.txt\u3092\u53c2\u7167\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "\u8bf7\u628a\u5b83\u4eec\u6dfb\u52a0\u5230 Avatar \u7684 Expression Parameters\u3002\u53ef\u7528\u4e0b\u65b9\u6309\u94ae\u751f\u6210\u73b0\u6210\u8d44\u6e90\uff0c\u4e5f\u53ef\u590d\u5236\u5217\u8868\u6216\u67e5\u770b PARAMETERS.txt\u3002", "\u8acb\u628a\u9019\u4e9b\u52a0\u5165\u60a8 Avatar \u7684 Expression Parameters\u3002\u53ef\u4f7f\u7528\u4e0b\u65b9\u6309\u9215\u5efa\u7acb\u73fe\u6210\u7684\u8cc7\u7522\uff0c\u6216\u8907\u88fd\u6e05\u55ae\uff0c\u6216\u53c3\u95b1 PARAMETERS.txt\u3002", "\uc774 \ud56d\ubaa9\ub4e4\uc744 \uc544\ubc14\ud0c0\uc758 Expression Parameters\uc5d0 \ucd94\uac00\ud558\uc138\uc694. \uc544\ub798 \ubc84\ud2bc\uc73c\ub85c \ubc14\ub85c \uc4f8 \uc218 \uc788\ub294 \uc5d0\uc14b\uc744 \ub9cc\ub4e4\uac70\ub098, \ubaa9\ub85d\uc744 \ubcf5\uc0ac\ud558\uac70\ub098, PARAMETERS.txt\ub97c \ucc38\uace0\ud558\uc138\uc694.", "Adicione-os aos Expression Parameters do seu avatar. Use o bot\u00e3o abaixo para gerar os assets prontos, copie a lista ou consulte o PARAMETERS.txt.", "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0438\u0445 \u0432 Expression Parameters \u0432\u0430\u0448\u0435\u0433\u043e \u0430\u0432\u0430\u0442\u0430\u0440\u0430. \u041a\u043d\u043e\u043f\u043a\u0430 \u043d\u0438\u0436\u0435 \u0441\u043e\u0437\u0434\u0430\u0451\u0442 \u0433\u043e\u0442\u043e\u0432\u044b\u0435 \u0430\u0441\u0441\u0435\u0442\u044b; \u043c\u043e\u0436\u043d\u043e \u0442\u0430\u043a\u0436\u0435 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u0438\u043b\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u044c PARAMETERS.txt." } },
            { "btn_vrc", new[] { "Create Expression Parameters + Menu assets (for VRCFury / MA)", "Cr\u00e9er les assets Expression Parameters + Menu (pour VRCFury / MA)", "Crear assets de Expression Parameters + Men\u00fa (para VRCFury / MA)", "Expression-Parameters- und Men\u00fc-Assets erstellen (f\u00fcr VRCFury / MA)", "Expression Parameters \u3068\u30e1\u30cb\u30e5\u30fc\u306e\u30a2\u30bb\u30c3\u30c8\u3092\u4f5c\u6210\uff08VRCFury / MA \u7528\uff09", "\u521b\u5efa Expression Parameters \u548c\u83dc\u5355\u8d44\u6e90\uff08\u7528\u4e8e VRCFury / MA\uff09", "\u5efa\u7acb Expression Parameters \u8207\u9078\u55ae\u8cc7\u7522\uff08\u4f9b VRCFury / MA \u4f7f\u7528\uff09", "Expression Parameters \ubc0f \uba54\ub274 \uc5d0\uc14b \ub9cc\ub4e4\uae30(VRCFury / MA\uc6a9)", "Criar assets de Expression Parameters e Menu (para VRCFury / MA)", "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u0430\u0441\u0441\u0435\u0442\u044b Expression Parameters \u0438 \u043c\u0435\u043d\u044e (\u0434\u043b\u044f VRCFury / MA)" } },
            { "no_sdk", new[] { "VRChat SDK not found in this project, so the ready-made Expression Parameters asset cannot be made here. Use the copy button below.", "SDK VRChat introuvable dans ce projet : impossible de cr\u00e9er l'asset Expression Parameters ici. Utilisez le bouton de copie ci-dessous.", "No se encontr\u00f3 el SDK de VRChat en este proyecto, as\u00ed que no se puede crear aqu\u00ed el asset de Expression Parameters. Usa el bot\u00f3n de copiar de abajo.", "VRChat-SDK in diesem Projekt nicht gefunden, daher kann das Expression-Parameters-Asset hier nicht erstellt werden. Nutze die Kopieren-Schaltfl\u00e4che unten.", "\u3053\u306e\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306b VRChat SDK \u304c\u898b\u3064\u304b\u3089\u306a\u3044\u305f\u3081\u3001Expression Parameters \u30a2\u30bb\u30c3\u30c8\u306f\u4f5c\u6210\u3067\u304d\u307e\u305b\u3093\u3002\u4e0b\u306e\u30b3\u30d4\u30fc\u30dc\u30bf\u30f3\u3092\u4f7f\u3063\u3066\u304f\u3060\u3055\u3044\u3002", "\u6b64\u9879\u76ee\u4e2d\u672a\u627e\u5230 VRChat SDK\uff0c\u65e0\u6cd5\u5728\u8fd9\u91cc\u751f\u6210 Expression Parameters \u8d44\u6e90\u3002\u8bf7\u4f7f\u7528\u4e0b\u65b9\u7684\u590d\u5236\u6309\u94ae\u3002", "\u6b64\u5c08\u6848\u4e2d\u627e\u4e0d\u5230 VRChat SDK\uff0c\u56e0\u6b64\u7121\u6cd5\u5728\u9019\u88e1\u5efa\u7acb\u73fe\u6210\u7684 Expression Parameters \u8cc7\u7522\u3002\u8acb\u4f7f\u7528\u4e0b\u65b9\u7684\u8907\u88fd\u6309\u9215\u3002", "\uc774 \ud504\ub85c\uc81d\ud2b8\uc5d0\uc11c VRChat SDK\ub97c \ucc3e\uc744 \uc218 \uc5c6\uc5b4 \ubc14\ub85c \uc4f8 \uc218 \uc788\ub294 Expression Parameters \uc5d0\uc14b\uc744 \ub9cc\ub4e4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. \uc544\ub798 \ubcf5\uc0ac \ubc84\ud2bc\uc744 \uc0ac\uc6a9\ud558\uc138\uc694.", "O VRChat SDK n\u00e3o foi encontrado neste projeto, ent\u00e3o o asset pronto de Expression Parameters n\u00e3o pode ser criado aqui. Use o bot\u00e3o de copiar abaixo.", "\u0412 \u044d\u0442\u043e\u043c \u043f\u0440\u043e\u0435\u043a\u0442\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d VRChat SDK, \u043f\u043e\u044d\u0442\u043e\u043c\u0443 \u0433\u043e\u0442\u043e\u0432\u044b\u0439 \u0430\u0441\u0441\u0435\u0442 Expression Parameters \u0437\u0434\u0435\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u043d\u0435\u043b\u044c\u0437\u044f. \u0412\u043e\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435\u0441\u044c \u043a\u043d\u043e\u043f\u043a\u043e\u0439 \u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f \u043d\u0438\u0436\u0435." } },
            { "btn_copy", new[] { "Copy parameter list to clipboard", "Copier la liste des param\u00e8tres dans le presse-papiers", "Copiar la lista de par\u00e1metros al portapapeles", "Parameterliste in die Zwischenablage kopieren", "\u30d1\u30e9\u30e1\u30fc\u30bf\u30fc\u30ea\u30b9\u30c8\u3092\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc", "\u590d\u5236\u53c2\u6570\u5217\u8868\u5230\u526a\u8d34\u677f", "\u8907\u88fd\u53c3\u6578\u6e05\u55ae\u5230\u526a\u8cbc\u7c3f", "\ud30c\ub77c\ubbf8\ud130 \ubaa9\ub85d\uc744 \ud074\ub9bd\ubcf4\ub4dc\uc5d0 \ubcf5\uc0ac", "Copiar lista de par\u00e2metros para a \u00e1rea de transfer\u00eancia", "\u0421\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u043f\u0438\u0441\u043e\u043a \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u043e\u0432 \u0432 \u0431\u0443\u0444\u0435\u0440 \u043e\u0431\u043c\u0435\u043d\u0430" } },
            { "copied", new[] { "Parameter list copied to the clipboard.", "Liste des param\u00e8tres copi\u00e9e dans le presse-papiers.", "Lista de par\u00e1metros copiada al portapapeles.", "Parameterliste in die Zwischenablage kopiert.", "\u30d1\u30e9\u30e1\u30fc\u30bf\u30fc\u30ea\u30b9\u30c8\u3092\u30af\u30ea\u30c3\u30d7\u30dc\u30fc\u30c9\u306b\u30b3\u30d4\u30fc\u3057\u307e\u3057\u305f\u3002", "\u53c2\u6570\u5217\u8868\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f\u3002", "\u53c3\u6578\u6e05\u55ae\u5df2\u8907\u88fd\u5230\u526a\u8cbc\u7c3f\u3002", "\ud30c\ub77c\ubbf8\ud130 \ubaa9\ub85d\uc744 \ud074\ub9bd\ubcf4\ub4dc\uc5d0 \ubcf5\uc0ac\ud588\uc2b5\ub2c8\ub2e4.", "Lista de par\u00e2metros copiada para a \u00e1rea de transfer\u00eancia.", "\u0421\u043f\u0438\u0441\u043e\u043a \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u043e\u0432 \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d \u0432 \u0431\u0443\u0444\u0435\u0440 \u043e\u0431\u043c\u0435\u043d\u0430." } },
            { "error_title", new[] { "Something went wrong", "Un probl\u00e8me est survenu", "Algo sali\u00f3 mal", "Etwas ist schiefgelaufen", "\u554f\u984c\u304c\u767a\u751f\u3057\u307e\u3057\u305f", "\u51fa\u9519\u4e86", "\u767c\u751f\u932f\u8aa4", "\ubb38\uc81c\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4", "Algo deu errado", "\u0427\u0442\u043e-\u0442\u043e \u043f\u043e\u0448\u043b\u043e \u043d\u0435 \u0442\u0430\u043a" } },
            { "error_console", new[] { "See the Console for details.", "Voir la Console pour les d\u00e9tails.", "Consulta la Consola para m\u00e1s detalles.", "Details siehe Konsole.", "\u8a73\u7d30\u306f\u30b3\u30f3\u30bd\u30fc\u30eb\u3092\u53c2\u7167\u3057\u3066\u304f\u3060\u3055\u3044\u3002", "\u8be6\u60c5\u8bf7\u67e5\u770b\u63a7\u5236\u53f0\u3002", "\u8a73\u60c5\u8acb\u898b Console\u3002", "\uc790\uc138\ud55c \ub0b4\uc6a9\uc740 Console\uc744 \ud655\uc778\ud558\uc138\uc694.", "Veja o Console para mais detalhes.", "\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u043e\u0441\u0442\u0438 \u0441\u043c. \u0432 Console." } },
        };

        // ------------------------------------------------------------------ folders
        const string Root = "Assets/GlucoseDevice";
        const string GenDir = Root + "/Generated";
        const string MatDir = GenDir + "/Materials";
        const string ClipRoot = GenDir + "/Clips";
        const string PrefabPath = GenDir + "/GlucoseDevice.prefab";
        const string StandaloneControllerPath = GenDir + "/GlucoseDevice_FX.controller";

        // ------------------------------------------------------------------ strip sizes (must match the PNGs)
        const int DigitFrames = 11;   // 0-9 plus a blank frame
        const int ArrowFrames = 3;    // blank, single arrow, double arrow (the arrow points right and is rotated)
        const int StateFrames = 4;    // blank, LO, HI, --
        const int UnitFrames = 2;     // mmol/L, mg/dL
        const int BlankDigit = 10;

        // ------------------------------------------------------------------ colour rows
        // Every glyph texture holds four stacked rows, one per colour. The screen is black and the glyphs are
        // bright; the State layer picks the row by moving the texture offset. No colour is ever animated, so
        // any shader that has a main texture will do. Row order (v offset = row / 4): ok, low, high, stale.
        const int Rows = 4;
        const int RowOk = 0;
        const int RowLow = 1;
        const int RowHigh = 2;
        const int RowStale = 3;

        // ------------------------------------------------------------------ object names (the animation paths use these)
        const string NScreen = "Screen";
        const string NBacklight = "Backlight";
        const string NDigit1 = "Digit1";
        const string NDigit2 = "Digit2";
        const string NDigit3 = "Digit3";
        const string NDot = "Dot";
        const string NArrow = "Arrow";
        const string NState = "StateLabel";
        const string NUnit = "UnitLabel";
        const string NCover = "Cover";
        const string NNumbers = "Numbers";   // container: digits, dot, unit label, state label
        const string NWords = "Words";       // plain-language panel for simple mode
        const string NShell = "Shell";
        const string DefaultDeviceName = "GlucoseDevice";

        // ------------------------------------------------------------------ parameter names (match the bridge app)
        const string PD1 = "BG_D1";
        const string PD2 = "BG_D2";
        const string PD3 = "BG_D3";
        const string PTrend = "BG_Trend";
        const string PStale = "BG_Stale";
        const string PLow = "BG_Low";
        const string PHigh = "BG_High";
        const string PMgdl = "BG_Mgdl";
        const string PBeat = "BG_Beat";
        const string PShow = "BG_Show";
        const string PSimple = "BG_Simple";
        const string PLangSel = "BG_LangSel";
        const string PWords = "BG_Words";

        // ------------------------------------------------------------------ window state
        GameObject avatarRoot;
        GameObject deviceInScene;
        AnimatorController targetController;
        int uiLang = -1;
        int wordLang = 0;
        bool menuLang = false;        // language chosen with a radial puppet in the VRChat menu (float)
        bool bridgeWords = false;     // the bridge app's "rotate" mode can show the words panel (one Bool)
        int pathMode = 0;             // 0 = prop-relative (VRCFury / Modular Avatar), 1 = avatar-relative
        bool writeDefaults = false;
        bool backupFirst = true;
        float timeoutSeconds = 90f;
        Vector2 scroll;

        [MenuItem("Tools/Glucose Device/Open Builder")]
        static void Open()
        {
            var window = GetWindow<GlucoseDeviceBuilder>("Glucose Device");
            window.minSize = new Vector2(380, 520);
        }

        // ================================================================== window
        void OnEnable()
        {
            if (uiLang < 0)
            {
                int saved = EditorPrefs.GetInt("GlucoseDevice.UiLang", -1);
                uiLang = saved >= 0 && saved < UiLangNames.Length ? saved : GuessLanguage();
                wordLang = Mathf.Clamp(WordIndexForUi(uiLang), 0, WordLangCount - 1);
            }
        }

        static int GuessLanguage()
        {
            switch (Application.systemLanguage)
            {
                case SystemLanguage.French: return 1;
                case SystemLanguage.Spanish: return 2;
                case SystemLanguage.German: return 3;
                case SystemLanguage.Japanese: return 4;
                case SystemLanguage.ChineseSimplified: return 5;
                case SystemLanguage.ChineseTraditional: return 6;
                case SystemLanguage.Korean: return 7;
                case SystemLanguage.Portuguese: return 8;
                case SystemLanguage.Russian: return 9;
                default: return 0;
            }
        }

        // UI language index -> words-panel language index (both lists use the same 10 positions).
        static int WordIndexForUi(int ui)
        {
            return ui;
        }

        string T(string key)
        {
            string[] values;
            if (Strings.TryGetValue(key, out values))
            {
                int i = uiLang < 0 ? 0 : uiLang;
                return i >= values.Length || string.IsNullOrEmpty(values[i]) ? values[0] : values[i];
            }
            return key;
        }

        GUIContent TT(string key, string tipKey)
        {
            return new GUIContent(T(key), T(tipKey));
        }

        void OnGUI()
        {
            scroll = EditorGUILayout.BeginScrollView(scroll);

            int newLang = EditorGUILayout.Popup(T("language"), uiLang, UiLangNames);
            if (newLang != uiLang)
            {
                uiLang = newLang;
                EditorPrefs.SetInt("GlucoseDevice.UiLang", uiLang);
            }

            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("title"), EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(T("disclaimer"), MessageType.Info);

            // ---- step 1
            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("step1"), EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(T("step1_help"), MessageType.None);
            if (GUILayout.Button(T("btn_build")))
            {
                Run(BuildPrefab);
            }

            // ---- step 2
            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("step2"), EditorStyles.boldLabel);
            pathMode = EditorGUILayout.Popup(T("path_style"), pathMode, new[] { T("path_prop"), T("path_avatar") });
            if (pathMode == 0)
            {
                EditorGUILayout.HelpBox(T("help_prop"), MessageType.None);
            }
            else
            {
                EditorGUILayout.HelpBox(T("help_avatar"), MessageType.None);
                avatarRoot = (GameObject)EditorGUILayout.ObjectField(T("avatar_root"), avatarRoot, typeof(GameObject), true);
                deviceInScene = (GameObject)EditorGUILayout.ObjectField(T("device_in_scene"), deviceInScene, typeof(GameObject), true);
            }
            EditorGUILayout.LabelField(T("anim_path"), pathMode == 0 ? T("rel_prop") : ComputeDevicePath());

            // ---- options
            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("options"), EditorStyles.boldLabel);
            writeDefaults = EditorGUILayout.Toggle(TT("wd", "wd_tip"), writeDefaults);
            timeoutSeconds = EditorGUILayout.Slider(TT("timeout", "timeout_tip"), timeoutSeconds, 20f, 300f);
            wordLang = EditorGUILayout.Popup(TT("words_lang", "words_lang_tip"), wordLang, WordLangNames);
            menuLang = EditorGUILayout.Toggle(TT("menu_lang", "menu_lang_tip"), menuLang);
            bridgeWords = EditorGUILayout.Toggle(TT("bridge_words", "bridge_words_tip"), bridgeWords);

            // ---- step 3
            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("step3"), EditorStyles.boldLabel);
            if (GUILayout.Button(T("btn_standalone")))
            {
                Run(BuildStandalone);
            }

            EditorGUILayout.Space();
            targetController = (AnimatorController)EditorGUILayout.ObjectField(T("your_fx"), targetController,
                typeof(AnimatorController), false);
            backupFirst = EditorGUILayout.Toggle(T("backup"), backupFirst);
            using (new EditorGUI.DisabledScope(targetController == null))
            {
                if (GUILayout.Button(T("btn_add")))
                {
                    Run(BuildIntoExisting);
                }
            }
            EditorGUILayout.HelpBox(T("help_layers"), MessageType.None);

            // ---- step 4
            EditorGUILayout.Space();
            EditorGUILayout.LabelField(T("step4"), EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(T("step4_help"), MessageType.None);
#if VRC_SDK_VRCSDK3
            if (GUILayout.Button(T("btn_vrc")))
            {
                Run(BuildVrcAssets);
            }
#else
            EditorGUILayout.HelpBox(T("no_sdk"), MessageType.None);
#endif
            if (GUILayout.Button(T("btn_copy")))
            {
                EditorGUIUtility.systemCopyBuffer = ParameterListText();
                Debug.Log("[Glucose Device] " + T("copied"));
            }

            EditorGUILayout.EndScrollView();
        }

        void Run(Action action)
        {
            try
            {
                action();
            }
            catch (Exception e)
            {
                Debug.LogError("[Glucose Device] " + e);
                EditorUtility.DisplayDialog("Glucose Device", T("error_title") + ":\n\n" + e.Message +
                    "\n\n" + T("error_console"), "OK");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
            }
        }

        string ComputeDevicePath()
        {
            if (pathMode == 0)
            {
                return "";
            }
            if (avatarRoot != null && deviceInScene != null)
            {
                if (!deviceInScene.transform.IsChildOf(avatarRoot.transform))
                {
                    return T("not_inside");
                }
                return AnimationUtility.CalculateTransformPath(deviceInScene.transform, avatarRoot.transform);
            }
            return DefaultDeviceName;
        }

        // ================================================================== parameter list
        string ParameterListText()
        {
            var sb = new StringBuilder();
            sb.AppendLine("Name        Type   Default  Synced  Saved");
            sb.AppendLine(PD1 + "      Int    10       yes     no");
            sb.AppendLine(PD2 + "      Int    10       yes     no");
            sb.AppendLine(PD3 + "      Int    10       yes     no");
            sb.AppendLine(PTrend + "   Int    0        yes     no");
            sb.AppendLine(PStale + "   Bool   0        yes     no");
            sb.AppendLine(PLow + "     Bool   0        yes     no");
            sb.AppendLine(PHigh + "    Bool   0        yes     no");
            sb.AppendLine(PMgdl + "    Bool   0        yes     no");
            sb.AppendLine(PBeat + "    Bool   0        yes     no");
            sb.AppendLine(PShow + "    Bool   1        yes     yes   (menu toggle: show the numbers to other players)");
            sb.AppendLine(PSimple + "  Bool   0        yes     yes   (menu toggle: plain words instead of numbers)");
            if (bridgeWords)
            {
                sb.AppendLine(PWords + "   Bool   0        yes     no    (sent by the bridge app in 'rotate' mode: show the plain words now)");
            }
            if (menuLang)
            {
                sb.AppendLine(PLangSel + " Float  " + LangDefault().ToString("0.00") + "     yes     yes   (menu radial puppet: language of the plain-words panel)");
            }
            return sb.ToString();
        }

        // Starting value of the language dial: the middle of the chosen language's tenth.
        float LangDefault()
        {
            return (wordLang + 0.5f) / WordLangCount;
        }

        // ================================================================== prefab
        void BuildPrefab()
        {
            EnsureFolder(MatDir);

            Material matBlack = MakeMaterial("GD_Black", "Unlit/Color", null, 1, 1, 0, Color.black);
            Material matShell = MakeMaterial("GD_Shell", "Standard", null, 1, 1, 0, new Color(0.12f, 0.13f, 0.15f, 1f));
            Material matDigits = MakeMaterial("GD_Digits", "Unlit/Transparent", FindTexture("lcd_digits"), DigitFrames, Rows, BlankDigit, null);
            Material matArrow = MakeMaterial("GD_Arrow", "Unlit/Transparent", FindTexture("lcd_arrow"), ArrowFrames, Rows, 1, null);
            Material matState = MakeMaterial("GD_State", "Unlit/Transparent", FindTexture("lcd_state"), StateFrames, Rows, 0, null);
            Material matUnits = MakeMaterial("GD_Units", "Unlit/Transparent", FindTexture("lcd_units"), UnitFrames, Rows, 0, null);
            Material matDot = MakeMaterial("GD_Dot", "Unlit/Transparent", FindTexture("lcd_dot"), 1, Rows, 0, null);
            Material matWords = MakeMaterial("GD_Words", "Unlit/Transparent", FindTexture("lcd_words"), WordLangCount, Rows, wordLang, null);
            Material matNoData = MakeMaterial("GD_NoData", "Unlit/Transparent", FindTexture("lcd_nodata"), 1, 1, 0, null);

            var root = new GameObject(DefaultDeviceName);
            try
            {
                BuildShell(root.transform, matShell);

                // The screen faces -Z. Rotate the device so that side faces you.
                var screen = new GameObject(NScreen);
                screen.transform.SetParent(root.transform, false);

                const float zBack = 0f;
                const float zFront = -0.0008f;
                const float zCover = -0.0016f;

                MakeQuad(NBacklight, screen.transform, new Vector3(0f, 0f, zBack), new Vector2(0.060f, 0.040f), matBlack);

                // Numbers mode.
                var numbers = new GameObject(NNumbers);
                numbers.transform.SetParent(screen.transform, false);
                var digitSize = new Vector2(0.011f, 0.0165f);
                MakeQuad(NDigit1, numbers.transform, new Vector3(-0.017f, 0.0055f, zFront), digitSize, matDigits);
                MakeQuad(NDigit2, numbers.transform, new Vector3(-0.005f, 0.0055f, zFront), digitSize, matDigits);
                MakeQuad(NDigit3, numbers.transform, new Vector3(0.011f, 0.0055f, zFront), digitSize, matDigits);
                MakeQuad(NDot, numbers.transform, new Vector3(0.003f, -0.001f, zFront), new Vector2(0.003f, 0.003f), matDot);
                MakeQuad(NState, numbers.transform, new Vector3(-0.0225f, -0.0135f, zFront), new Vector2(0.014f, 0.007f), matState);
                MakeQuad(NUnit, numbers.transform, new Vector3(0.0185f, -0.0135f, zFront), new Vector2(0.020f, 0.005f), matUnits);

                // Simple mode: plain words instead of numbers. Starts hidden.
                var words = MakeQuad(NWords, screen.transform, new Vector3(-0.0055f, 0.002f, zFront), new Vector2(0.044f, 0.030f), matWords);
                words.SetActive(false);

                // The trend arrow is shown in both modes.
                MakeQuad(NArrow, screen.transform, new Vector3(0.0235f, 0.005f, zFront), new Vector2(0.011f, 0.011f), matArrow);

                // Cover: shown when the bridge stops sending. Black plate with a grey "--". Starts hidden.
                var cover = MakeQuad(NCover, screen.transform, new Vector3(0f, 0f, zCover), new Vector2(0.060f, 0.040f), matNoData);
                cover.SetActive(false);

                var prefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                AssetDatabase.SaveAssets();
                AssetDatabase.Refresh();
                EditorGUIUtility.PingObject(prefab);
                Debug.Log("[Glucose Device] Prefab built: " + PrefabPath);
                EditorUtility.DisplayDialog("Glucose Device",
                    "Prefab built:\n" + PrefabPath + "\n\nDrag it into a scene to look at it. The screen faces the -Z side.", "OK");
            }
            finally
            {
                DestroyImmediate(root);
            }
        }

        // Uses Models/GD_Shell (.obj or .fbx, any folder) if it exists, otherwise a plain grey box.
        static void BuildShell(Transform parent, Material shellMaterial)
        {
            GameObject model = null;
            foreach (string guid in AssetDatabase.FindAssets("GD_Shell t:Model"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(path) == "GD_Shell")
                {
                    FixModelImport(path);
                    model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                    break;
                }
            }

            if (model != null)
            {
                var instance = (GameObject)PrefabUtility.InstantiatePrefab(model);
                instance.name = NShell;
                instance.transform.SetParent(parent, false);
                foreach (Renderer r in instance.GetComponentsInChildren<Renderer>())
                {
                    r.sharedMaterial = shellMaterial;
                }
                return;
            }

            var shell = GameObject.CreatePrimitive(PrimitiveType.Cube);
            shell.name = NShell;
            DestroyImmediate(shell.GetComponent<Collider>());
            shell.transform.SetParent(parent, false);
            shell.transform.localPosition = new Vector3(0f, 0f, 0.0075f);
            shell.transform.localScale = new Vector3(0.070f, 0.050f, 0.014f);
            ConfigureRenderer(shell.GetComponent<MeshRenderer>(), shellMaterial);
        }

        // Read/Write on, normals calculated, no imported materials (the builder assigns its own).
        static void FixModelImport(string path)
        {
            var importer = AssetImporter.GetAtPath(path) as ModelImporter;
            if (importer == null)
            {
                return;
            }
            bool changed = !importer.isReadable
                || importer.importNormals != ModelImporterNormals.Calculate
                || importer.materialImportMode != ModelImporterMaterialImportMode.None;
            if (!changed)
            {
                return;
            }
            importer.isReadable = true;
            importer.importNormals = ModelImporterNormals.Calculate;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.SaveAndReimport();
        }

        static GameObject MakeQuad(string name, Transform parent, Vector3 pos, Vector2 size, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = name;
            DestroyImmediate(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = new Vector3(size.x, size.y, 1f);
            ConfigureRenderer(go.GetComponent<MeshRenderer>(), mat);
            return go;
        }

        static void ConfigureRenderer(MeshRenderer renderer, Material mat)
        {
            renderer.sharedMaterial = mat;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.lightProbeUsage = LightProbeUsage.Off;
            renderer.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }

        static Material MakeMaterial(string fileName, string shaderName, Texture2D tex, int frames, int rows, int defaultFrame, Color? color)
        {
            Shader shader = Shader.Find(shaderName);
            if (shader == null)
            {
                throw new Exception("Shader not found: " + shaderName);
            }

            string path = MatDir + "/" + fileName + ".mat";
            Material mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null)
            {
                mat = new Material(shader);
                AssetDatabase.CreateAsset(mat, path);
            }
            mat.shader = shader;
            if (tex != null)
            {
                mat.mainTexture = tex;
                mat.mainTextureScale = new Vector2(1f / frames, 1f / rows);
                mat.mainTextureOffset = new Vector2(defaultFrame / (float)frames, 0f);
            }
            if (color.HasValue)
            {
                mat.color = color.Value;
            }
            EditorUtility.SetDirty(mat);
            return mat;
        }

        static Texture2D FindTexture(string name)
        {
            string[] guids = AssetDatabase.FindAssets(name + " t:Texture2D");
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (Path.GetFileNameWithoutExtension(path) == name)
                {
                    FixTextureImport(path);
                    return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                }
            }
            throw new Exception("Texture not found: " + name + ".png. Is the whole GlucoseDevice folder inside Assets?");
        }

        static void FixTextureImport(string path)
        {
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
            {
                return;
            }
            importer.textureType = TextureImporterType.Default;
            importer.mipmapEnabled = false;            // mip levels would blur neighbouring frames together
            importer.filterMode = FilterMode.Bilinear;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.alphaIsTransparency = true;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.maxTextureSize = 2048;
            importer.SaveAndReimport();
        }

#if VRC_SDK_VRCSDK3
        // ================================================================== VRChat assets
        static VRCExpressionParameters.Parameter Param(string name, VRCExpressionParameters.ValueType type, float def, bool saved)
        {
            return new VRCExpressionParameters.Parameter
            {
                name = name,
                valueType = type,
                defaultValue = def,
                saved = saved,
                networkSynced = true
            };
        }

        void BuildVrcAssets()
        {
            EnsureFolder(GenDir);
            string paramPath = GenDir + "/GlucoseDevice_Parameters.asset";
            string menuPath = GenDir + "/GlucoseDevice_Menu.asset";
            AssetDatabase.DeleteAsset(paramPath);
            AssetDatabase.DeleteAsset(menuPath);

            var ps = ScriptableObject.CreateInstance<VRCExpressionParameters>();
            var list = new List<VRCExpressionParameters.Parameter>
            {
                Param(PD1, VRCExpressionParameters.ValueType.Int, 10f, false),
                Param(PD2, VRCExpressionParameters.ValueType.Int, 10f, false),
                Param(PD3, VRCExpressionParameters.ValueType.Int, 10f, false),
                Param(PTrend, VRCExpressionParameters.ValueType.Int, 0f, false),
                Param(PStale, VRCExpressionParameters.ValueType.Bool, 0f, false),
                Param(PLow, VRCExpressionParameters.ValueType.Bool, 0f, false),
                Param(PHigh, VRCExpressionParameters.ValueType.Bool, 0f, false),
                Param(PMgdl, VRCExpressionParameters.ValueType.Bool, 0f, false),
                Param(PBeat, VRCExpressionParameters.ValueType.Bool, 0f, false),
                Param(PShow, VRCExpressionParameters.ValueType.Bool, 1f, true),
                Param(PSimple, VRCExpressionParameters.ValueType.Bool, 0f, true),
            };
            if (bridgeWords)
            {
                list.Add(Param(PWords, VRCExpressionParameters.ValueType.Bool, 0f, false));
            }
            if (menuLang)
            {
                list.Add(Param(PLangSel, VRCExpressionParameters.ValueType.Float, LangDefault(), true));
            }
            ps.parameters = list.ToArray();
            AssetDatabase.CreateAsset(ps, paramPath);

            var menu = ScriptableObject.CreateInstance<VRCExpressionsMenu>();
            var toggle = new VRCExpressionsMenu.Control();
            toggle.name = "Show glucose";
            toggle.type = VRCExpressionsMenu.Control.ControlType.Toggle;
            toggle.parameter = new VRCExpressionsMenu.Control.Parameter { name = PShow };
            toggle.value = 1f;
            menu.controls.Add(toggle);
            var simple = new VRCExpressionsMenu.Control();
            simple.name = "Simple mode (words)";
            simple.type = VRCExpressionsMenu.Control.ControlType.Toggle;
            simple.parameter = new VRCExpressionsMenu.Control.Parameter { name = PSimple };
            simple.value = 1f;
            menu.controls.Add(simple);
            if (menuLang)
            {
                var dial = new VRCExpressionsMenu.Control();
                dial.name = "Words language (dial)";
                dial.type = VRCExpressionsMenu.Control.ControlType.RadialPuppet;
                dial.subParameters = new[] { new VRCExpressionsMenu.Control.Parameter { name = PLangSel } };
                menu.controls.Add(dial);
            }
            AssetDatabase.CreateAsset(menu, menuPath);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EditorGUIUtility.PingObject(ps);
            Debug.Log("[Glucose Device] Made " + paramPath + " and " + menuPath);
            EditorUtility.DisplayDialog("Glucose Device",
                "Made:\n" + paramPath + "\n" + menuPath +
                "\n\nDrag them into the Parameters and Menu lists of your VRCFury Full Controller.", "OK");
        }
#endif

        // ================================================================== controllers
        void BuildStandalone()
        {
            EnsureFolder(GenDir);
            AssetDatabase.DeleteAsset(StandaloneControllerPath);
            AnimatorController controller = AnimatorController.CreateAnimatorControllerAtPath(StandaloneControllerPath);
            BuildLayers(controller, "GlucoseDevice_FX");
            Finish(controller, "Standalone controller built: " + StandaloneControllerPath);
        }

        void BuildIntoExisting()
        {
            if (targetController == null)
            {
                return;
            }
            string controllerPath = AssetDatabase.GetAssetPath(targetController);
            if (backupFirst)
            {
                string stamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                string backup = controllerPath.Replace(".controller", "_backup_" + stamp + ".controller");
                if (!AssetDatabase.CopyAsset(controllerPath, backup))
                {
                    throw new Exception("Could not make a backup copy, so nothing was changed.");
                }
                Debug.Log("[Glucose Device] Backup made: " + backup);
            }
            BuildLayers(targetController, targetController.name);
            Finish(targetController, "Layers added to: " + controllerPath);
        }

        static void Finish(AnimatorController controller, string message)
        {
            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            EditorGUIUtility.PingObject(controller);
            Debug.Log("[Glucose Device] " + message);
            EditorUtility.DisplayDialog("Glucose Device", message + "\n\nNow add the parameters from the list (step 4).", "OK");
        }

        void BuildLayers(AnimatorController controller, string clipFolderName)
        {
            string devicePath = ComputeDevicePath();
            if (devicePath.StartsWith("("))
            {
                throw new Exception("The device is not inside the avatar root. Check step 2.");
            }
            string clipDir = ClipRoot + "/" + clipFolderName;

            EditorUtility.DisplayProgressBar("Glucose Device", "Setting up parameters", 0.05f);
            EnsureParameters(controller);
            RemoveOldLayers(controller);

            // Remove clips from any earlier build for this controller, then recreate them.
            if (AssetDatabase.IsValidFolder(clipDir))
            {
                AssetDatabase.DeleteAsset(clipDir);
            }
            EnsureFolder(clipDir);

            string screen = Join(devicePath, NScreen);

            EditorUtility.DisplayProgressBar("Glucose Device", "Digit layers", 0.2f);
            string numbers = Join(screen, NNumbers);
            BuildDigitLayer(controller, clipDir, 1, PD1, Join(numbers, NDigit1));
            BuildDigitLayer(controller, clipDir, 2, PD2, Join(numbers, NDigit2));
            BuildDigitLayer(controller, clipDir, 3, PD3, Join(numbers, NDigit3));

            EditorUtility.DisplayProgressBar("Glucose Device", "Trend, colour and unit layers", 0.5f);
            BuildTrendLayer(controller, clipDir, Join(screen, NArrow));
            BuildStateLayer(controller, clipDir, screen);
            BuildUnitsLayer(controller, clipDir, numbers);

            EditorUtility.DisplayProgressBar("Glucose Device", "Privacy, simple mode and watchdog layers", 0.8f);
            BuildPrivacyLayer(controller, clipDir, screen);
            BuildSimpleLayer(controller, clipDir, screen);
            if (menuLang)
            {
                BuildLanguageDialLayer(controller, clipDir, Join(screen, NWords));
            }
            BuildWatchdogLayer(controller, clipDir, Join(screen, NCover));
        }

        // ------------------------------------------------------------------ parameters and layers
        void EnsureParameters(AnimatorController controller)
        {
            EnsureParameter(controller, PD1, AnimatorControllerParameterType.Int, false);
            EnsureParameter(controller, PD2, AnimatorControllerParameterType.Int, false);
            EnsureParameter(controller, PD3, AnimatorControllerParameterType.Int, false);
            EnsureParameter(controller, PTrend, AnimatorControllerParameterType.Int, false);
            EnsureParameter(controller, PStale, AnimatorControllerParameterType.Bool, false);
            EnsureParameter(controller, PLow, AnimatorControllerParameterType.Bool, false);
            EnsureParameter(controller, PHigh, AnimatorControllerParameterType.Bool, false);
            EnsureParameter(controller, PMgdl, AnimatorControllerParameterType.Bool, false);
            EnsureParameter(controller, PBeat, AnimatorControllerParameterType.Bool, false);
            EnsureParameter(controller, PShow, AnimatorControllerParameterType.Bool, true);
            EnsureParameter(controller, PSimple, AnimatorControllerParameterType.Bool, false);
            if (bridgeWords)
            {
                EnsureParameter(controller, PWords, AnimatorControllerParameterType.Bool, false);
            }
            if (menuLang)
            {
                EnsureParameter(controller, PLangSel, AnimatorControllerParameterType.Float, false, LangDefault());
            }
        }

        static void EnsureParameter(AnimatorController controller, string name, AnimatorControllerParameterType type, bool defaultBool, float defaultFloat = 0f)
        {
            foreach (AnimatorControllerParameter existing in controller.parameters)
            {
                if (existing.name == name)
                {
                    if (existing.type != type)
                    {
                        throw new Exception("Your controller already has a parameter called " + name +
                            " with a different type (" + existing.type + "). Rename or delete it, then try again.");
                    }
                    return;
                }
            }
            var p = new AnimatorControllerParameter
            {
                name = name,
                type = type,
                defaultBool = defaultBool,
                defaultFloat = defaultFloat
            };
            controller.AddParameter(p);
        }

        static void RemoveOldLayers(AnimatorController controller)
        {
            for (int i = controller.layers.Length - 1; i >= 0; i--)
            {
                if (controller.layers[i].name.StartsWith("BG_"))
                {
                    controller.RemoveLayer(i);
                }
            }
        }

        static AnimatorStateMachine NewLayer(AnimatorController controller, string name)
        {
            controller.AddLayer(name);
            AnimatorControllerLayer[] layers = controller.layers;
            layers[layers.Length - 1].defaultWeight = 1f;
            controller.layers = layers;
            return controller.layers[controller.layers.Length - 1].stateMachine;
        }

        AnimatorState AddState(AnimatorStateMachine sm, string name, Motion motion, int row, int column)
        {
            AnimatorState state = sm.AddState(name, new Vector3(280f + column * 280f, row * 55f, 0f));
            state.motion = motion;
            state.writeDefaultValues = writeDefaults;
            return state;
        }

        static void AnyTo(AnimatorStateMachine sm, AnimatorState to, params (AnimatorConditionMode mode, float threshold, string parameter)[] conditions)
        {
            AnimatorStateTransition t = sm.AddAnyStateTransition(to);
            t.hasExitTime = false;
            t.hasFixedDuration = true;
            t.duration = 0f;
            t.exitTime = 0f;
            t.canTransitionToSelf = false;
            foreach (var c in conditions)
            {
                t.AddCondition(c.mode, c.threshold, c.parameter);
            }
        }

        static void Move(AnimatorState from, AnimatorState to, params (AnimatorConditionMode mode, float threshold, string parameter)[] conditions)
        {
            AnimatorStateTransition t = from.AddTransition(to);
            t.hasExitTime = false;
            t.hasFixedDuration = true;
            t.duration = 0f;
            t.exitTime = 0f;
            foreach (var c in conditions)
            {
                t.AddCondition(c.mode, c.threshold, c.parameter);
            }
        }

        static void TimeoutMove(AnimatorState from, AnimatorState to)
        {
            AnimatorStateTransition t = from.AddTransition(to);
            t.hasExitTime = true;
            t.exitTime = 1f;
            t.hasFixedDuration = true;
            t.duration = 0f;
        }

        // ------------------------------------------------------------------ the layers
        // Property ownership (so layers never fight): digit layers own _MainTex_ST x/z of their digit,
        // the trend layer owns x/z + rotation of the arrow, the units layer owns x/z of the unit label,
        // and the State layer owns y/w (the colour row) of every glyph.
        void BuildDigitLayer(AnimatorController controller, string clipDir, int digit, string parameter, string path)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_D" + digit);
            AnimatorState blank = null;
            for (int k = 0; k < DigitFrames; k++)
            {
                string label = k == BlankDigit ? "blank" : k.ToString();
                AnimationClip clip = NewClip(clipDir, "BG_D" + digit + "_" + label);
                SetFrame(clip, path, DigitFrames, k);
                AnimatorState state = AddState(sm, "D" + digit + " = " + label, clip, k, 0);
                AnyTo(sm, state, (AnimatorConditionMode.Equals, (float)k, parameter));
                if (k == BlankDigit)
                {
                    blank = state;
                }
            }
            sm.defaultState = blank;
        }

        // The arrow texture points right. Each state picks single/double arrow and turns the quad.
        void BuildTrendLayer(AnimatorController controller, string clipDir, string arrowPath)
        {
            // frame: 0 blank, 1 single, 2 double.  angle: degrees, positive = counter-clockwise seen from the front.
            int[] frames = { 0, 2, 1, 1, 1, 2 };
            float[] angles = { 0f, 90f, 45f, 0f, -45f, -90f };
            string[] names = { "none", "rising fast", "rising", "flat", "falling", "falling fast" };

            AnimatorStateMachine sm = NewLayer(controller, "BG_Trend");
            AnimatorState first = null;
            for (int k = 0; k < 6; k++)
            {
                AnimationClip clip = NewClip(clipDir, "BG_Trend_" + k);
                SetFrame(clip, arrowPath, ArrowFrames, frames[k]);
                SetRotationZ(clip, arrowPath, angles[k]);
                AnimatorState state = AddState(sm, "Trend " + k + " = " + names[k], clip, k, 0);
                AnyTo(sm, state, (AnimatorConditionMode.Equals, (float)k, PTrend));
                if (k == 0)
                {
                    first = state;
                }
            }
            sm.defaultState = first;
        }

        // Picks the colour row for every glyph and the LO / HI / -- label.
        // Priority: stale, then low, then high, then in range.
        void BuildStateLayer(AnimatorController controller, string clipDir, string screen)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_State");

            AnimatorState normal = AddState(sm, "In range", RowClip(clipDir, "BG_State_Normal", screen, RowOk, 0), 0, 0);
            AnimatorState low = AddState(sm, "Low", RowClip(clipDir, "BG_State_Low", screen, RowLow, 1), 1, 0);
            AnimatorState high = AddState(sm, "High", RowClip(clipDir, "BG_State_High", screen, RowHigh, 2), 2, 0);
            AnimatorState stale = AddState(sm, "Stale", RowClip(clipDir, "BG_State_Stale", screen, RowStale, 3), 3, 0);
            sm.defaultState = normal;

            // The conditions never overlap.
            AnyTo(sm, stale, (AnimatorConditionMode.If, 0f, PStale));
            AnyTo(sm, low, (AnimatorConditionMode.IfNot, 0f, PStale), (AnimatorConditionMode.If, 0f, PLow));
            AnyTo(sm, high, (AnimatorConditionMode.IfNot, 0f, PStale), (AnimatorConditionMode.IfNot, 0f, PLow), (AnimatorConditionMode.If, 0f, PHigh));
            AnyTo(sm, normal, (AnimatorConditionMode.IfNot, 0f, PStale), (AnimatorConditionMode.IfNot, 0f, PLow), (AnimatorConditionMode.IfNot, 0f, PHigh));
        }

        AnimationClip RowClip(string clipDir, string name, string screen, int row, int labelFrame)
        {
            AnimationClip clip = NewClip(clipDir, name);
            string numbers = Join(screen, NNumbers);
            SetRow(clip, Join(numbers, NDigit1), row);
            SetRow(clip, Join(numbers, NDigit2), row);
            SetRow(clip, Join(numbers, NDigit3), row);
            SetRow(clip, Join(numbers, NDot), row);
            SetRow(clip, Join(numbers, NUnit), row);
            SetRow(clip, Join(screen, NArrow), row);
            SetRow(clip, Join(screen, NWords), row);
            // The label is only ever touched by this layer, so it gets frame and row together.
            string label = Join(numbers, NState);
            SetFrame(clip, label, StateFrames, labelFrame);
            SetRow(clip, label, row);
            return clip;
        }

        void BuildUnitsLayer(AnimatorController controller, string clipDir, string numbersPath)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_Units");

            string dotPath = Join(numbersPath, NDot);
            string unitPath = Join(numbersPath, NUnit);

            AnimationClip mmolClip = NewClip(clipDir, "BG_Units_mmol");
            SetActive(mmolClip, dotPath, true, 1f / 60f);
            SetFrame(mmolClip, dotPath, 1, 0);   // the dot has one frame; write its x scale so it is never left at 0
            SetFrame(mmolClip, unitPath, UnitFrames, 0);
            AnimationClip mgdlClip = NewClip(clipDir, "BG_Units_mgdl");
            SetActive(mgdlClip, dotPath, false, 1f / 60f);
            SetFrame(mgdlClip, dotPath, 1, 0);
            SetFrame(mgdlClip, unitPath, UnitFrames, 1);

            AnimatorState mmol = AddState(sm, "mmol/L (decimal point on)", mmolClip, 0, 0);
            AnimatorState mgdl = AddState(sm, "mg/dL (decimal point off)", mgdlClip, 1, 0);
            sm.defaultState = mmol;
            AnyTo(sm, mgdl, (AnimatorConditionMode.If, 0f, PMgdl));
            AnyTo(sm, mmol, (AnimatorConditionMode.IfNot, 0f, PMgdl));
        }

        // Simple mode: show the plain-language panel instead of the numbers.
        // BG_Simple is the wearer's menu toggle. BG_Words (optional) is set by the bridge app's rotate mode.
        // Either one switches the panel on.
        void BuildSimpleLayer(AnimatorController controller, string clipDir, string screen)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_Simple");

            string numbersPath = Join(screen, NNumbers);
            string wordsPath = Join(screen, NWords);
            bool fixedLang = !menuLang;

            AnimationClip numbersClip = SimpleClip(clipDir, "BG_Simple_Numbers", numbersPath, wordsPath, false, fixedLang, 1f / 60f);
            AnimationClip wordsClip = SimpleClip(clipDir, "BG_Simple_Words", numbersPath, wordsPath, true, fixedLang, 1f / 60f);

            AnimatorState numbers = AddState(sm, "Numbers", numbersClip, 0, 0);
            AnimatorState words = AddState(sm, "Words (simple mode)", wordsClip, 1, 0);
            sm.defaultState = numbers;

            AnyTo(sm, words, (AnimatorConditionMode.If, 0f, PSimple));
            if (bridgeWords)
            {
                AnyTo(sm, words, (AnimatorConditionMode.If, 0f, PWords));
                AnyTo(sm, numbers, (AnimatorConditionMode.IfNot, 0f, PSimple), (AnimatorConditionMode.IfNot, 0f, PWords));
            }
            else
            {
                AnyTo(sm, numbers, (AnimatorConditionMode.IfNot, 0f, PSimple));
            }
        }

        AnimationClip SimpleClip(string clipDir, string name, string numbersPath, string wordsPath, bool showWords, bool fixedLang, float length)
        {
            AnimationClip clip = NewClip(clipDir, name);
            SetActive(clip, numbersPath, !showWords, length);
            SetActive(clip, wordsPath, showWords, length);
            if (fixedLang)
            {
                // No layer owns the words panel's frame, so write it here (an unwritten x scale stays 0 = invisible).
                SetFrame(clip, wordsPath, WordLangCount, wordLang);
            }
            return clip;
        }

        // Optional: a radial puppet (float 0..1) in the VRChat menu. Each tenth of the dial is one language.
        void BuildLanguageDialLayer(AnimatorController controller, string clipDir, string wordsPath)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_Language");
            AnimatorState chosen = null;
            for (int k = 0; k < WordLangCount; k++)
            {
                AnimationClip clip = NewClip(clipDir, "BG_Language_" + k);
                SetFrame(clip, wordsPath, WordLangCount, k);
                AnimatorState state = AddState(sm, WordLangNames[k], clip, k, 0);

                var conditions = new List<(AnimatorConditionMode mode, float threshold, string parameter)>();
                if (k > 0)
                {
                    conditions.Add((AnimatorConditionMode.Greater, k / (float)WordLangCount, PLangSel));
                }
                if (k < WordLangCount - 1)
                {
                    conditions.Add((AnimatorConditionMode.Less, (k + 1) / (float)WordLangCount, PLangSel));
                }
                AnyTo(sm, state, conditions.ToArray());
                if (k == wordLang)
                {
                    chosen = state;
                }
            }
            sm.defaultState = chosen;
        }

        void BuildPrivacyLayer(AnimatorController controller, string clipDir, string screenPath)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_Privacy");

            AnimationClip shownClip = NewClip(clipDir, "BG_Privacy_Shown");
            SetActive(shownClip, screenPath, true, 1f / 60f);
            AnimationClip hiddenClip = NewClip(clipDir, "BG_Privacy_Hidden");
            SetActive(hiddenClip, screenPath, false, 1f / 60f);

            AnimatorState shown = AddState(sm, "Screen shown", shownClip, 0, 0);
            AnimatorState hidden = AddState(sm, "Screen hidden", hiddenClip, 1, 0);
            sm.defaultState = shown;
            AnyTo(sm, hidden, (AnimatorConditionMode.IfNot, 0f, PShow));
            AnyTo(sm, shown, (AnimatorConditionMode.If, 0f, PShow));
        }

        // Watchdog: the bridge flips BG_Beat every few seconds. If it stops flipping for the timeout,
        // the grey "--" cover is switched on. Level checks alone cannot spot "no change", so there are
        // two Live states (beat true / beat false) and two Dead states, and only a flip moves between them.
        void BuildWatchdogLayer(AnimatorController controller, string clipDir, string coverPath)
        {
            AnimatorStateMachine sm = NewLayer(controller, "BG_Watchdog");

            AnimationClip deadClip = NewClip(clipDir, "BG_Watchdog_Dead");
            SetActive(deadClip, coverPath, true, 1f);
            AnimationClip liveClip = NewClip(clipDir, "BG_Watchdog_Live");
            SetActive(liveClip, coverPath, false, timeoutSeconds);

            AnimatorState deadF = AddState(sm, "Dead (beat was false)", deadClip, 0, 0);
            AnimatorState deadT = AddState(sm, "Dead (beat was true)", deadClip, 1, 0);
            AnimatorState liveA = AddState(sm, "Live A (beat true)", liveClip, 0, 1);
            AnimatorState liveB = AddState(sm, "Live B (beat false)", liveClip, 1, 1);
            sm.defaultState = deadF;

            Move(deadF, liveA, (AnimatorConditionMode.If, 0f, PBeat));
            Move(deadT, liveB, (AnimatorConditionMode.IfNot, 0f, PBeat));
            Move(liveA, liveB, (AnimatorConditionMode.IfNot, 0f, PBeat));
            Move(liveB, liveA, (AnimatorConditionMode.If, 0f, PBeat));
            TimeoutMove(liveA, deadT);
            TimeoutMove(liveB, deadF);
        }

        // ================================================================== clips
        static AnimationClip NewClip(string dir, string name)
        {
            string path = dir + "/" + name + ".anim";
            var clip = new AnimationClip { name = name, frameRate = 60f };
            AssetDatabase.CreateAsset(clip, path);
            return clip;
        }

        static void SetConst(AnimationClip clip, string path, Type type, string property, float value, float length)
        {
            var binding = new EditorCurveBinding { path = path, type = type, propertyName = property };
            AnimationUtility.SetEditorCurve(clip, binding, AnimationCurve.Constant(0f, length, value));
            EditorUtility.SetDirty(clip);
        }

        // Horizontal frame of a strip: only the x scale and x offset are written.
        static void SetFrame(AnimationClip clip, string path, int frames, int frame)
        {
            const float len = 1f / 60f;
            SetConst(clip, path, typeof(MeshRenderer), "material._MainTex_ST.x", 1f / frames, len);
            SetConst(clip, path, typeof(MeshRenderer), "material._MainTex_ST.z", frame / (float)frames, len);
        }

        // Colour row of the atlas: only the y scale and y offset are written.
        static void SetRow(AnimationClip clip, string path, int row)
        {
            const float len = 1f / 60f;
            SetConst(clip, path, typeof(MeshRenderer), "material._MainTex_ST.y", 1f / Rows, len);
            SetConst(clip, path, typeof(MeshRenderer), "material._MainTex_ST.w", row / (float)Rows, len);
        }

        // Rotation about Z, written as a quaternion (all four components).
        static void SetRotationZ(AnimationClip clip, string path, float degrees)
        {
            const float len = 1f / 60f;
            Quaternion q = Quaternion.Euler(0f, 0f, degrees);
            SetConst(clip, path, typeof(Transform), "m_LocalRotation.x", q.x, len);
            SetConst(clip, path, typeof(Transform), "m_LocalRotation.y", q.y, len);
            SetConst(clip, path, typeof(Transform), "m_LocalRotation.z", q.z, len);
            SetConst(clip, path, typeof(Transform), "m_LocalRotation.w", q.w, len);
        }

        static void SetActive(AnimationClip clip, string path, bool active, float length)
        {
            SetConst(clip, path, typeof(GameObject), "m_IsActive", active ? 1f : 0f, length);
        }

        // ================================================================== small helpers
        static string Join(string a, string b)
        {
            return string.IsNullOrEmpty(a) ? b : a + "/" + b;
        }

        static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path))
            {
                return;
            }
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            string leaf = Path.GetFileName(path);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }
    }
}

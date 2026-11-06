#!/usr/bin/env python3
"""
GlucOSC - Blood Sugar Meter to OSC translation software
=======================================================
Reads your latest glucose from the xDrip+ web service on your phone and sends it
to VRChat as OSC avatar parameters, so an avatar can show the digits, a trend
arrow, a colour state and a "this data stopped" watchdog signal.

DISPLAY ONLY. CGM readings lag, and this adds more delay. Keep your normal CGM
alarms and never make treatment decisions from an avatar.

Run the Qt6 window:      python3 glucose_osc_bridge.py
Run without a window:    python3 glucose_osc_bridge.py --cli --host 192.168.1.50
Send one test set:       python3 glucose_osc_bridge.py --cli --host 192.168.1.50 --once
Show mg/dL instead:      add  --show-units mg/dL
Flip between both:       add  --show-units alternate  (every 15 s, --alternate-sec to change)
Rotate through all:      add  --show-units rotate  (mmol/L, mg/dL, then the avatar's plain-words panel,
                         10 s each, --rotate-sec to change)

Requirements: Python 3.9+. The window needs PySide6 (pip install PySide6).
The --cli mode needs nothing beyond the standard library.

xDrip+ setup (phone): Settings > Inter-app settings > enable "xDrip Web Service",
enable "Open Web Service", and set an "xDrip Web Service Secret". Use that same
secret here. Give the phone a fixed IP on your router.

Avatar parameters sent (names are editable in the window). To let other players
see the display, tick "Synced" for all of them in your Expression Parameters.
Synced parameters count against VRChat's 256-bit limit: 3 Ints + 1 Int + 5 Bools
is about 37 bits (+1 if you use BG_Words).

    BG_D1      Int 0-10  left digit.   10 = blank (used to hide leading zeros)
    BG_D2      Int 0-10  middle digit. 10 = blank
    BG_D3      Int 0-10  right digit.  10 = blank
    BG_Trend   Int 0-5   0 unknown, 1 rising fast, 2 rising, 3 flat, 4 falling, 5 falling fast
    BG_Stale   Bool      newest reading is older than the stale limit, or no data at all
    BG_Low     Bool      below your low limit  (default 4.0 mmol/L)
    BG_High    Bool      above your high limit (default 10.0 mmol/L)
    BG_Mgdl    Bool      true when the digits are mg/dL (show no decimal point / "mg/dL" label)
    BG_Words   Bool      true while the avatar should show its plain-words panel. Only used in "rotate"
                         mode, and only if the avatar was built with the BG_Words option; otherwise ignored.
                         (The panel's language is NOT sent by the bridge: it is set on the avatar.)
    BG_Beat    Bool      flips every ~5 s while the bridge is running. An animator layer can
                         treat "no flip for a minute or two" as stale, so a crash, sleeping PC
                         or lost network can't leave a reassuring green number on screen.

How digits are laid out:
    mmol/L  5.6  -> D1=blank D2=5 D3=6   (decimal point is fixed on the device)
            12.4 -> D1=1     D2=2 D3=4
    mg/dL   112  -> D1=1     D2=1 D3=2
            95   -> D1=blank D2=9 D3=5

VRChat must have OSC enabled: Action Menu > Options > OSC > Enabled.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import socket
import struct
import sys
import time
import urllib.request
from dataclasses import dataclass, fields
from typing import List, Optional, Tuple

MGDL_PER_MMOL = 18.0156
OSC_PREFIX = "/avatar/parameters/"
BLANK = 10

TREND_FROM_DIRECTION = {
    "DoubleUp": 1,
    "SingleUp": 1,
    "FortyFiveUp": 2,
    "Flat": 3,
    "FortyFiveDown": 4,
    "SingleDown": 5,
    "DoubleDown": 5,
}
TREND_ARROW = {0: "?", 1: "↑↑", 2: "↗", 3: "→", 4: "↘", 5: "↓↓"}


# --------------------------------------------------------------------------
# Core logic (standard library only)
# --------------------------------------------------------------------------

@dataclass
class Settings:
    phone_host: str = "192.168.1.50"
    phone_port: int = 17580
    secret: str = ""
    poll_seconds: int = 60
    units: str = "auto"              # what xDrip+ sends: "auto", "mg/dL" or "mmol/L"
    display_units: str = "mmol/L"    # what the avatar shows: "mmol/L", "mg/dL", "alternate" or "rotate"
    alternate_seconds: int = 15      # in "alternate" mode, how long each unit stays up
    rotate_seconds: int = 10         # in "rotate" mode, how long each of mmol/L, mg/dL and words stays up
    osc_host: str = "127.0.0.1"
    osc_port: int = 9000
    stale_minutes: int = 15
    low_mmol: float = 4.0            # limits are always entered in mmol/L
    high_mmol: float = 10.0
    p_d1: str = "BG_D1"
    p_d2: str = "BG_D2"
    p_d3: str = "BG_D3"
    p_trend: str = "BG_Trend"
    p_stale: str = "BG_Stale"
    p_low: str = "BG_Low"
    p_high: str = "BG_High"
    p_mgdl: str = "BG_Mgdl"
    p_beat: str = "BG_Beat"
    p_words: str = "BG_Words"        # "show the plain-words panel now" (Bool, optional, used by rotate mode)
    ui_language: str = "auto"        # this app's window language: "auto" or a code from UI_LANGS


@dataclass
class Reading:
    mmol: float
    when: float  # epoch seconds
    trend: int   # 0-5, see module docstring


# ---------------------------------------------------------------- languages
# Window languages. More can be added: put a new code here and a translation for each key below.
# Translations are machine-written and should be reviewed by native speakers.
UI_LANGS = ['en', 'fr', 'es', 'de', 'ja', 'zh-Hans', 'zh-Hant', 'ko', 'pt-BR', 'ru']

APP_STRINGS = {
    'en': {
        'window_title': 'GlucOSC',
        'not_running': 'Not running',
        'waiting': 'Waiting for a reading...',
        'stopped': 'Stopped',
        'started': 'Started. Checking http://{host}:{port}/sgv.json',
        'note': 'Display only. Readings lag. Keep your normal CGM alarms.',
        'group_app': 'Language',
        'group_xdrip': 'xDrip+ on your phone',
        'group_osc': 'VRChat OSC',
        'group_params': 'Avatar parameter names',
        'ui_language': 'App language',
        'phone_address': 'Phone address',
        'port': 'Port',
        'secret': 'Secret',
        'check_every': 'Check every (s)',
        'xdrip_sends': 'xDrip+ sends',
        'osc_address': 'OSC address',
        'osc_port': 'OSC port',
        'avatar_shows': 'Avatar shows',
        'alternate_every': 'Alternate every (s)',
        'rotate_every': 'Rotate every (s)',
        'stale_after': 'Stale after (min)',
        'low_below': 'Low below (mmol/L)',
        'high_above': 'High above (mmol/L)',
        'p_d1': 'Left digit (Int)',
        'p_d2': 'Middle digit (Int)',
        'p_d3': 'Right digit (Int)',
        'p_trend': 'Trend (Int)',
        'p_stale': 'Stale (Bool)',
        'p_low': 'Low (Bool)',
        'p_high': 'High (Bool)',
        'p_mgdl': 'mg/dL flag (Bool)',
        'p_beat': 'Heartbeat (Bool)',
        'p_words': 'Words panel (Bool)',
        'start': 'Start',
        'stop': 'Stop',
        'send_test': 'Send test values',
        'no_readings': 'xDrip+ answered but sent no readings',
        'unreachable': 'Could not reach xDrip+: {err}',
        'reading_age': '{units} · reading is {age} min old',
        'stale_flag': 'STALE',
        'sent_test': 'Sent test values: {value} {units}, flat, not stale',
    },
    'fr': {
        'window_title': 'GlucOSC',
        'not_running': "À l'arrêt",
        'waiting': "En attente d'une mesure...",
        'stopped': 'Arrêté',
        'started': 'Démarré. Interrogation de http://{host}:{port}/sgv.json',
        'note': 'Affichage seulement. Les mesures sont en retard. Gardez vos alarmes CGM habituelles.',
        'group_app': 'Langue',
        'group_xdrip': 'xDrip+ sur votre téléphone',
        'group_osc': 'VRChat OSC',
        'group_params': "Noms des paramètres de l'avatar",
        'ui_language': "Langue de l'application",
        'phone_address': 'Adresse du téléphone',
        'port': 'Port',
        'secret': 'Secret',
        'check_every': 'Vérifier toutes les (s)',
        'xdrip_sends': 'xDrip+ envoie',
        'osc_address': 'Adresse OSC',
        'osc_port': 'Port OSC',
        'avatar_shows': "L'avatar affiche",
        'alternate_every': 'Alterner toutes les (s)',
        'rotate_every': 'Alterner (3 vues) toutes les (s)',
        'stale_after': 'Périmé après (min)',
        'low_below': 'Bas sous (mmol/L)',
        'high_above': 'Haut au-dessus de (mmol/L)',
        'p_d1': 'Chiffre de gauche (Int)',
        'p_d2': 'Chiffre du milieu (Int)',
        'p_d3': 'Chiffre de droite (Int)',
        'p_trend': 'Tendance (Int)',
        'p_stale': 'Périmé (Bool)',
        'p_low': 'Bas (Bool)',
        'p_high': 'Haut (Bool)',
        'p_mgdl': 'Indicateur mg/dL (Bool)',
        'p_beat': 'Signal de vie (Bool)',
        'p_words': 'Panneau de mots (Bool)',
        'start': 'Démarrer',
        'stop': 'Arrêter',
        'send_test': 'Envoyer des valeurs de test',
        'no_readings': "xDrip+ a répondu mais n'a envoyé aucune mesure",
        'unreachable': 'Impossible de joindre xDrip+ : {err}',
        'reading_age': '{units} · mesure vieille de {age} min',
        'stale_flag': 'PÉRIMÉ',
        'sent_test': 'Valeurs de test envoyées : {value} {units}, stable, non périmé',
    },
    'es': {
        'window_title': 'GlucOSC',
        'not_running': 'Detenido',
        'waiting': 'Esperando una lectura...',
        'stopped': 'Detenido',
        'started': 'Iniciado. Consultando http://{host}:{port}/sgv.json',
        'note': 'Solo para mostrar. Las lecturas tienen retraso. Mantén tus alarmas habituales del CGM.',
        'group_app': 'Idioma',
        'group_xdrip': 'xDrip+ en tu teléfono',
        'group_osc': 'VRChat OSC',
        'group_params': 'Nombres de parámetros del avatar',
        'ui_language': 'Idioma de la aplicación',
        'phone_address': 'Dirección del teléfono',
        'port': 'Puerto',
        'secret': 'Secreto',
        'check_every': 'Comprobar cada (s)',
        'xdrip_sends': 'xDrip+ envía',
        'osc_address': 'Dirección OSC',
        'osc_port': 'Puerto OSC',
        'avatar_shows': 'El avatar muestra',
        'alternate_every': 'Alternar cada (s)',
        'rotate_every': 'Rotar cada (s)',
        'stale_after': 'Obsoleto tras (min)',
        'low_below': 'Bajo menos de (mmol/L)',
        'high_above': 'Alto por encima de (mmol/L)',
        'p_d1': 'Dígito izquierdo (Int)',
        'p_d2': 'Dígito central (Int)',
        'p_d3': 'Dígito derecho (Int)',
        'p_trend': 'Tendencia (Int)',
        'p_stale': 'Obsoleto (Bool)',
        'p_low': 'Bajo (Bool)',
        'p_high': 'Alto (Bool)',
        'p_mgdl': 'Indicador mg/dL (Bool)',
        'p_beat': 'Latido (Bool)',
        'p_words': 'Panel de palabras (Bool)',
        'start': 'Iniciar',
        'stop': 'Detener',
        'send_test': 'Enviar valores de prueba',
        'no_readings': 'xDrip+ respondió pero no envió lecturas',
        'unreachable': 'No se pudo conectar con xDrip+: {err}',
        'reading_age': '{units} · lectura de hace {age} min',
        'stale_flag': 'OBSOLETO',
        'sent_test': 'Valores de prueba enviados: {value} {units}, estable, no obsoleto',
    },
    'de': {
        'window_title': 'GlucOSC',
        'not_running': 'Nicht aktiv',
        'waiting': 'Warte auf einen Messwert ...',
        'stopped': 'Gestoppt',
        'started': 'Gestartet. Abfrage von http://{host}:{port}/sgv.json',
        'note': 'Nur Anzeige. Messwerte sind verzögert. Behalte deine normalen CGM-Alarme bei.',
        'group_app': 'Sprache',
        'group_xdrip': 'xDrip+ auf deinem Handy',
        'group_osc': 'VRChat OSC',
        'group_params': 'Parameternamen des Avatars',
        'ui_language': 'App-Sprache',
        'phone_address': 'Adresse des Handys',
        'port': 'Port',
        'secret': 'Secret',
        'check_every': 'Prüfen alle (s)',
        'xdrip_sends': 'xDrip+ sendet',
        'osc_address': 'OSC-Adresse',
        'osc_port': 'OSC-Port',
        'avatar_shows': 'Avatar zeigt',
        'alternate_every': 'Wechseln alle (s)',
        'rotate_every': 'Rotation alle (s)',
        'stale_after': 'Veraltet nach (min)',
        'low_below': 'Niedrig unter (mmol/L)',
        'high_above': 'Hoch über (mmol/L)',
        'p_d1': 'Linke Ziffer (Int)',
        'p_d2': 'Mittlere Ziffer (Int)',
        'p_d3': 'Rechte Ziffer (Int)',
        'p_trend': 'Trend (Int)',
        'p_stale': 'Veraltet (Bool)',
        'p_low': 'Niedrig (Bool)',
        'p_high': 'Hoch (Bool)',
        'p_mgdl': 'mg/dL-Flag (Bool)',
        'p_beat': 'Heartbeat (Bool)',
        'p_words': 'Wortanzeige (Bool)',
        'start': 'Starten',
        'stop': 'Stoppen',
        'send_test': 'Testwerte senden',
        'no_readings': 'xDrip+ hat geantwortet, aber keine Messwerte gesendet',
        'unreachable': 'xDrip+ nicht erreichbar: {err}',
        'reading_age': '{units} · Messwert {age} Min. alt',
        'stale_flag': 'VERALTET',
        'sent_test': 'Testwerte gesendet: {value} {units}, gleichbleibend, nicht veraltet',
    },
    'ja': {
        'window_title': 'GlucOSC',
        'not_running': '停止中',
        'waiting': '測定値を待っています…',
        'stopped': '停止しました',
        'started': '開始しました。http://{host}:{port}/sgv.json を確認中',
        'note': '表示専用です。数値には遅れがあります。通常のCGMアラームは必ず使い続けてください。',
        'group_app': '言語',
        'group_xdrip': 'スマートフォンのxDrip+',
        'group_osc': 'VRChat OSC',
        'group_params': 'アバターのパラメーター名',
        'ui_language': 'アプリの言語',
        'phone_address': 'スマートフォンのアドレス',
        'port': 'ポート',
        'secret': 'シークレット',
        'check_every': '確認間隔（秒）',
        'xdrip_sends': 'xDrip+の単位',
        'osc_address': 'OSCアドレス',
        'osc_port': 'OSCポート',
        'avatar_shows': 'アバターの表示単位',
        'alternate_every': '切り替え間隔（秒）',
        'rotate_every': 'ローテーション間隔（秒）',
        'stale_after': '古いとみなす時間（分）',
        'low_below': '低値のしきい値（mmol/L）',
        'high_above': '高値のしきい値（mmol/L）',
        'p_d1': '左の桁 (Int)',
        'p_d2': '中央の桁 (Int)',
        'p_d3': '右の桁 (Int)',
        'p_trend': 'トレンド (Int)',
        'p_stale': '古い (Bool)',
        'p_low': '低 (Bool)',
        'p_high': '高 (Bool)',
        'p_mgdl': 'mg/dLフラグ (Bool)',
        'p_beat': 'ハートビート (Bool)',
        'p_words': '文字パネル (Bool)',
        'start': '開始',
        'stop': '停止',
        'send_test': 'テスト値を送信',
        'no_readings': 'xDrip+ は応答しましたが、測定値がありません',
        'unreachable': 'xDrip+ に接続できません: {err}',
        'reading_age': '{units} · {age}分前の測定値',
        'stale_flag': '古い',
        'sent_test': 'テスト値を送信: {value} {units}、横ばい、古くない',
    },
    'zh-Hans': {
        'window_title': 'GlucOSC',
        'not_running': '未运行',
        'waiting': '正在等待读数…',
        'stopped': '已停止',
        'started': '已启动。正在检查 http://{host}:{port}/sgv.json',
        'note': '仅用于显示。读数存在延迟。请保留您原有的CGM报警。',
        'group_app': '语言',
        'group_xdrip': '手机上的 xDrip+',
        'group_osc': 'VRChat OSC',
        'group_params': 'Avatar 参数名称',
        'ui_language': '应用语言',
        'phone_address': '手机地址',
        'port': '端口',
        'secret': '密钥',
        'check_every': '检查间隔（秒）',
        'xdrip_sends': 'xDrip+ 发送的单位',
        'osc_address': 'OSC 地址',
        'osc_port': 'OSC 端口',
        'avatar_shows': 'Avatar 显示单位',
        'alternate_every': '切换间隔（秒）',
        'rotate_every': '轮换间隔（秒）',
        'stale_after': '过期时间（分钟）',
        'low_below': '低于此值为低（mmol/L）',
        'high_above': '高于此值为高（mmol/L）',
        'p_d1': '左侧数字 (Int)',
        'p_d2': '中间数字 (Int)',
        'p_d3': '右侧数字 (Int)',
        'p_trend': '趋势 (Int)',
        'p_stale': '过期 (Bool)',
        'p_low': '低 (Bool)',
        'p_high': '高 (Bool)',
        'p_mgdl': 'mg/dL 标志 (Bool)',
        'p_beat': '心跳 (Bool)',
        'p_words': '文字面板 (Bool)',
        'start': '开始',
        'stop': '停止',
        'send_test': '发送测试值',
        'no_readings': 'xDrip+ 已响应，但没有返回读数',
        'unreachable': '无法连接 xDrip+：{err}',
        'reading_age': '{units} · 读数已有 {age} 分钟',
        'stale_flag': '已过期',
        'sent_test': '已发送测试值：{value} {units}，平稳，未过期',
    },
    'zh-Hant': {
        'window_title': 'GlucOSC',
        'not_running': '未執行',
        'waiting': '正在等待讀數…',
        'stopped': '已停止',
        'started': '已啟動。正在檢查 http://{host}:{port}/sgv.json',
        'note': '僅供顯示。讀數存在延遲。請保留您原有的 CGM 警報。',
        'group_app': '語言',
        'group_xdrip': '手機上的 xDrip+',
        'group_osc': 'VRChat OSC',
        'group_params': 'Avatar 參數名稱',
        'ui_language': '應用程式語言',
        'phone_address': '手機位址',
        'port': '連接埠',
        'secret': '金鑰',
        'check_every': '檢查間隔（秒）',
        'xdrip_sends': 'xDrip+ 傳送的單位',
        'osc_address': 'OSC 位址',
        'osc_port': 'OSC 連接埠',
        'avatar_shows': 'Avatar 顯示',
        'alternate_every': '交替間隔（秒）',
        'rotate_every': '輪播間隔（秒）',
        'stale_after': '過期時間（分鐘）',
        'low_below': '低於此值為低（mmol/L）',
        'high_above': '高於此值為高（mmol/L）',
        'p_d1': '左側數字 (Int)',
        'p_d2': '中間數字 (Int)',
        'p_d3': '右側數字 (Int)',
        'p_trend': '趨勢 (Int)',
        'p_stale': '過期 (Bool)',
        'p_low': '低 (Bool)',
        'p_high': '高 (Bool)',
        'p_mgdl': 'mg/dL 旗標 (Bool)',
        'p_beat': '心跳 (Bool)',
        'p_words': '文字面板 (Bool)',
        'start': '開始',
        'stop': '停止',
        'send_test': '傳送測試值',
        'no_readings': 'xDrip+ 已回應，但沒有傳回讀數',
        'unreachable': '無法連線至 xDrip+：{err}',
        'reading_age': '{units} · 讀數已有 {age} 分鐘',
        'stale_flag': '已過期',
        'sent_test': '已傳送測試值：{value} {units}，平穩，未過期',
    },
    'ko': {
        'window_title': 'GlucOSC',
        'not_running': '실행 중 아님',
        'waiting': '측정값을 기다리는 중…',
        'stopped': '중지됨',
        'started': '시작했습니다. http://{host}:{port}/sgv.json 확인 중',
        'note': '표시 전용입니다. 측정값에는 지연이 있습니다. 평소 사용하는 CGM 알람을 꼭 유지하세요.',
        'group_app': '언어',
        'group_xdrip': '휴대폰의 xDrip+',
        'group_osc': 'VRChat OSC',
        'group_params': '아바타 파라미터 이름',
        'ui_language': '앱 언어',
        'phone_address': '휴대폰 주소',
        'port': '포트',
        'secret': '시크릿',
        'check_every': '확인 간격(초)',
        'xdrip_sends': 'xDrip+ 전송 단위',
        'osc_address': 'OSC 주소',
        'osc_port': 'OSC 포트',
        'avatar_shows': '아바타 표시',
        'alternate_every': '전환 간격(초)',
        'rotate_every': '순환 간격(초)',
        'stale_after': '오래됨 기준(분)',
        'low_below': '이 값 미만이면 낮음(mmol/L)',
        'high_above': '이 값 초과면 높음(mmol/L)',
        'p_d1': '왼쪽 숫자 (Int)',
        'p_d2': '가운데 숫자 (Int)',
        'p_d3': '오른쪽 숫자 (Int)',
        'p_trend': '추세 (Int)',
        'p_stale': '오래됨 (Bool)',
        'p_low': '낮음 (Bool)',
        'p_high': '높음 (Bool)',
        'p_mgdl': 'mg/dL 플래그 (Bool)',
        'p_beat': '하트비트 (Bool)',
        'p_words': '문구 패널 (Bool)',
        'start': '시작',
        'stop': '중지',
        'send_test': '테스트 값 보내기',
        'no_readings': 'xDrip+가 응답했지만 측정값이 없습니다',
        'unreachable': 'xDrip+에 연결할 수 없습니다: {err}',
        'reading_age': '{units} · 측정값이 {age}분 지났습니다',
        'stale_flag': '오래됨',
        'sent_test': '테스트 값을 보냈습니다: {value} {units}, 변화 없음, 오래되지 않음',
    },
    'pt-BR': {
        'window_title': 'GlucOSC',
        'not_running': 'Não está em execução',
        'waiting': 'Aguardando uma leitura...',
        'stopped': 'Parado',
        'started': 'Iniciado. Consultando http://{host}:{port}/sgv.json',
        'note': 'Somente exibição. As leituras têm atraso. Mantenha seus alarmes normais do CGM.',
        'group_app': 'Idioma',
        'group_xdrip': 'xDrip+ no seu celular',
        'group_osc': 'VRChat OSC',
        'group_params': 'Nomes dos parâmetros do avatar',
        'ui_language': 'Idioma do aplicativo',
        'phone_address': 'Endereço do celular',
        'port': 'Porta',
        'secret': 'Segredo',
        'check_every': 'Verificar a cada (s)',
        'xdrip_sends': 'xDrip+ envia',
        'osc_address': 'Endereço OSC',
        'osc_port': 'Porta OSC',
        'avatar_shows': 'Avatar mostra',
        'alternate_every': 'Alternar a cada (s)',
        'rotate_every': 'Revezar a cada (s)',
        'stale_after': 'Desatualizado após (min)',
        'low_below': 'Baixa abaixo de (mmol/L)',
        'high_above': 'Alta acima de (mmol/L)',
        'p_d1': 'Dígito esquerdo (Int)',
        'p_d2': 'Dígito do meio (Int)',
        'p_d3': 'Dígito direito (Int)',
        'p_trend': 'Tendência (Int)',
        'p_stale': 'Desatualizado (Bool)',
        'p_low': 'Baixa (Bool)',
        'p_high': 'Alta (Bool)',
        'p_mgdl': 'Sinalizador mg/dL (Bool)',
        'p_beat': 'Batimento (Bool)',
        'p_words': 'Painel de palavras (Bool)',
        'start': 'Iniciar',
        'stop': 'Parar',
        'send_test': 'Enviar valores de teste',
        'no_readings': 'O xDrip+ respondeu, mas não enviou leituras',
        'unreachable': 'Não foi possível acessar o xDrip+: {err}',
        'reading_age': '{units} · leitura com {age} min',
        'stale_flag': 'DESATUALIZADO',
        'sent_test': 'Valores de teste enviados: {value} {units}, estável, não desatualizado',
    },
    'ru': {
        'window_title': 'GlucOSC',
        'not_running': 'Не запущено',
        'waiting': 'Ожидание показания...',
        'stopped': 'Остановлено',
        'started': 'Запущено. Проверка http://{host}:{port}/sgv.json',
        'note': 'Только отображение. Показания запаздывают. Не отключайте обычные сигналы вашего CGM.',
        'group_app': 'Язык',
        'group_xdrip': 'xDrip+ на телефоне',
        'group_osc': 'VRChat OSC',
        'group_params': 'Имена параметров аватара',
        'ui_language': 'Язык приложения',
        'phone_address': 'Адрес телефона',
        'port': 'Порт',
        'secret': 'Секрет',
        'check_every': 'Проверять каждые (с)',
        'xdrip_sends': 'xDrip+ передаёт',
        'osc_address': 'Адрес OSC',
        'osc_port': 'Порт OSC',
        'avatar_shows': 'Аватар показывает',
        'alternate_every': 'Чередовать каждые (с)',
        'rotate_every': 'Переключать каждые (с)',
        'stale_after': 'Устарело через (мин)',
        'low_below': 'Низкий ниже (mmol/L)',
        'high_above': 'Высокий выше (mmol/L)',
        'p_d1': 'Левая цифра (Int)',
        'p_d2': 'Средняя цифра (Int)',
        'p_d3': 'Правая цифра (Int)',
        'p_trend': 'Тренд (Int)',
        'p_stale': 'Устарело (Bool)',
        'p_low': 'Низкий (Bool)',
        'p_high': 'Высокий (Bool)',
        'p_mgdl': 'Флаг mg/dL (Bool)',
        'p_beat': 'Сигнал активности (Bool)',
        'p_words': 'Панель слов (Bool)',
        'start': 'Старт',
        'stop': 'Стоп',
        'send_test': 'Отправить тестовые значения',
        'no_readings': 'xDrip+ ответил, но не прислал показаний',
        'unreachable': 'Не удалось связаться с xDrip+: {err}',
        'reading_age': '{units} · показанию {age} мин',
        'stale_flag': 'УСТАРЕЛО',
        'sent_test': 'Отправлены тестовые значения: {value} {units}, стабильно, не устарело',
    },
}


def detect_language() -> str:
    """Best guess at the user's language from the environment ("en" when unsure)."""
    raw = ""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        raw = os.environ.get(name, "")
        if raw:
            break
    if not raw and sys.platform == "win32":
        # Windows: locale.getlocale() gives names like "French_France", so ask Windows for "fr-FR".
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, len(buf)):
                raw = buf.value
        except Exception:
            raw = ""
    if not raw:
        try:
            import locale
            raw = locale.getlocale()[0] or ""
        except Exception:
            raw = ""
    raw = raw.replace("-", "_").split(".")[0]
    base = raw.split("_")[0].lower()
    if base == "zh":
        return "zh-Hant" if any(t in raw for t in ("TW", "HK", "MO", "Hant")) else "zh-Hans"
    if base == "pt":
        return "pt-BR"
    return base or "en"


def resolve_ui_language(code: str) -> str:
    """Window language actually used (the closest one we have a translation for)."""
    code = detect_language() if code in ("", "auto") else code
    if code in UI_LANGS:
        return code
    if code.startswith("zh"):
        return "zh-Hant" if any(t in code for t in ("TW", "HK", "MO", "Hant")) else "zh-Hans"
    if code.startswith("pt"):
        return "pt-BR"
    return "en"


def tr(lang: str, key: str, **fmt) -> str:
    text = APP_STRINGS.get(lang, {}).get(key) or APP_STRINGS["en"][key]
    return text.format(**fmt) if fmt else text


def to_mmol(value: float, units: str = "auto") -> float:
    """Convert an xDrip+ sgv value to mmol/L.

    Nightscout-style sgv values are normally mg/dL. In "auto" mode anything under
    35 is treated as already being mmol/L, since no real mg/dL reading is that low.
    """
    if units == "mmol/L" or (units == "auto" and value < 35):
        return float(value)
    return float(value) / MGDL_PER_MMOL


def slope_to_trend(mmol_per_min: float) -> int:
    if mmol_per_min >= 0.11:
        return 1
    if mmol_per_min >= 0.055:
        return 2
    if mmol_per_min <= -0.11:
        return 5
    if mmol_per_min <= -0.055:
        return 4
    return 3


def parse_sgv(payload, units: str = "auto", now: Optional[float] = None) -> Optional[Reading]:
    """Turn xDrip+ /sgv.json output into the newest Reading (or None)."""
    now = time.time() if now is None else now
    data = json.loads(payload)
    if isinstance(data, dict):
        data = [data]
    entries = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        try:
            sgv = float(entry.get("sgv"))
        except (TypeError, ValueError):
            continue
        if sgv <= 0:
            continue
        try:
            when = float(entry.get("date"))
            if when > 1e11:  # milliseconds
                when /= 1000.0
        except (TypeError, ValueError):
            when = now
        entries.append((when, sgv, entry.get("direction")))
    if not entries:
        return None
    entries.sort(key=lambda e: e[0], reverse=True)
    when, sgv, direction = entries[0]
    mmol = to_mmol(sgv, units)
    trend = TREND_FROM_DIRECTION.get(direction) if isinstance(direction, str) else None
    if trend is None:
        trend = 0
        for older_when, older_sgv, _ in entries[1:]:
            minutes = (when - older_when) / 60.0
            if 1.0 <= minutes <= 20.0:
                trend = slope_to_trend((mmol - to_mmol(older_sgv, units)) / minutes)
                break
    return Reading(mmol=mmol, when=when, trend=trend)


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def digits_for(mmol: float, display_units: str) -> Tuple[int, int, int]:
    """Three digits (0-9, or BLANK) for the device. See the module docstring."""
    if display_units == "mg/dL":
        v = max(0, min(999, _round_half_up(mmol * MGDL_PER_MMOL)))
        d1, d2, d3 = v // 100, (v // 10) % 10, v % 10
        if v < 100:
            d1 = BLANK
        if v < 10:
            d2 = BLANK
    else:
        v = max(0, min(999, _round_half_up(mmol * 10)))  # tenths of a mmol/L
        d1, d2, d3 = v // 100, (v // 10) % 10, v % 10
        if v < 100:
            d1 = BLANK
    return d1, d2, d3


def effective_units(s: "Settings", now: Optional[float] = None) -> str:
    """The unit being shown right now. In "alternate" mode it flips every alternate_seconds.
    In "rotate" mode it follows display_phase (the words phase counts as mmol/L)."""
    if s.display_units == "alternate":
        now = time.time() if now is None else now
        slot = int(now // max(1, int(s.alternate_seconds)))
        return "mmol/L" if slot % 2 == 0 else "mg/dL"
    if s.display_units == "rotate":
        return "mg/dL" if display_phase(s, now) == "mg/dL" else "mmol/L"
    return s.display_units


def display_phase(s: "Settings", now: Optional[float] = None) -> str:
    """What the avatar should be showing right now: "mmol/L", "mg/dL" or "words".
    Only "rotate" mode ever returns "words"; it cycles mmol/L, mg/dL, words every rotate_seconds."""
    if s.display_units == "rotate":
        now = time.time() if now is None else now
        slot = int(now // max(1, int(s.rotate_seconds)))
        return ("mmol/L", "mg/dL", "words")[slot % 3]
    return effective_units(s, now)


def format_value(mmol: float, display_units: str) -> str:
    if display_units == "mg/dL":
        return str(max(0, _round_half_up(mmol * MGDL_PER_MMOL)))
    return f"{mmol:.1f}"


def state_tag(reading: Optional[Reading], s: Settings, stale: bool) -> str:
    """Short word to show next to the colour so it never depends on hue alone."""
    if reading is None or stale:
        return "--"
    if reading.mmol < s.low_mmol:
        return "LO"
    if reading.mmol > s.high_mmol:
        return "HI"
    return ""


Param = Tuple[str, object]


def build_params(reading: Optional[Reading], s: Settings, now: Optional[float] = None,
                 beat: bool = False) -> List[Param]:
    """The (name, value) pairs to send. With no reading, the device reads as stale and blank."""
    now = time.time() if now is None else now
    units = effective_units(s, now)
    mgdl = units == "mg/dL"
    words = s.display_units == "rotate" and display_phase(s, now) == "words"
    if reading is None:
        return [
            (s.p_d1, BLANK), (s.p_d2, BLANK), (s.p_d3, BLANK),
            (s.p_trend, 0), (s.p_stale, True),
            (s.p_low, False), (s.p_high, False),
            (s.p_mgdl, mgdl), (s.p_beat, bool(beat)),
            (s.p_words, words),
        ]
    age_minutes = max(0.0, (now - reading.when) / 60.0)
    d1, d2, d3 = digits_for(reading.mmol, units)
    return [
        (s.p_d1, d1), (s.p_d2, d2), (s.p_d3, d3),
        (s.p_trend, int(reading.trend)),
        (s.p_stale, age_minutes > s.stale_minutes),
        (s.p_low, reading.mmol < s.low_mmol),
        (s.p_high, reading.mmol > s.high_mmol),
        (s.p_mgdl, mgdl), (s.p_beat, bool(beat)),
        (s.p_words, words),
    ]


def _pad(raw: bytes) -> bytes:
    return raw + b"\0" * (4 - len(raw) % 4)


def osc_message(address: str, value) -> bytes:
    """Encode one OSC message (int32, float32 or bool)."""
    if isinstance(value, bool):
        tag, args = ("T" if value else "F"), b""
    elif isinstance(value, int):
        tag, args = "i", struct.pack(">i", value)
    elif isinstance(value, float):
        tag, args = "f", struct.pack(">f", value)
    else:
        raise TypeError(f"unsupported OSC value: {value!r}")
    return _pad(address.encode("utf-8")) + _pad(("," + tag).encode("ascii")) + args


class OscClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.addr = (host, int(port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, name: str, value) -> None:
        address = name if name.startswith("/") else OSC_PREFIX + name
        self.sock.sendto(osc_message(address, value), self.addr)

    def send_all(self, params: List[Param]) -> None:
        for name, value in params:
            self.send(name, value)

    def close(self) -> None:
        self.sock.close()


def fetch_sgv(s: Settings, timeout: float = 5.0) -> bytes:
    url = f"http://{s.phone_host}:{int(s.phone_port)}/sgv.json?count=3"
    request = urllib.request.Request(url)
    if s.secret:
        request.add_header("api-secret", hashlib.sha1(s.secret.encode("utf-8")).hexdigest())
    # Talk straight to the phone on the local network, ignoring any system proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return response.read()


def run_cli(s: Settings, once: bool = False) -> int:
    client = OscClient(s.osc_host, s.osc_port)
    reading: Optional[Reading] = None
    last_poll = 0.0
    beat = False
    try:
        while True:
            now = time.time()
            if last_poll == 0.0 or now - last_poll >= s.poll_seconds:
                last_poll = now
                try:
                    newest = parse_sgv(fetch_sgv(s), s.units)
                    if newest is None:
                        print("xDrip+ answered but sent no readings")
                    else:
                        reading = newest
                        age = (now - newest.when) / 60.0
                        print(f"{time.strftime('%H:%M:%S')}  {format_value(newest.mmol, effective_units(s))} "
                              f"{effective_units(s)} {TREND_ARROW[newest.trend]}  ({age:.0f} min old)")
                except Exception as exc:  # network problems are expected; keep going
                    print(f"Could not reach xDrip+: {exc}")
            beat = not beat
            client.send_all(build_params(reading, s, time.time(), beat))
            if once:
                return 0 if reading else 1
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        if not once:
            client.send_all(build_params(None, s, beat=not beat))  # tell the avatar the data stopped
        client.close()
    return 0


# --------------------------------------------------------------------------
# Qt6 window (PySide6)
# --------------------------------------------------------------------------

try:
    from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, QTimer, Qt, Signal
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
        QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
    )
    HAVE_QT = True
except ImportError:
    HAVE_QT = False

# Static colours, no pulsing. The LO / HI / -- word is shown alongside, so colour is never the only cue.
COLOR_OK = "#3cc8a0"     # green
COLOR_LOW = "#ff7eb6"    # pink
COLOR_HIGH = "#ff9a3c"   # orange
COLOR_STALE = "#8a8f98"  # grey


def load_settings() -> Settings:
    store = QSettings("GlucoseOscBridge", "GlucoseOscBridge")
    s = Settings()
    for f in fields(Settings):
        default = getattr(s, f.name)
        value = store.value(f.name, default)
        try:
            if isinstance(default, int):
                value = int(value)
            elif isinstance(default, float):
                value = float(value)
            else:
                value = str(value)
        except (TypeError, ValueError):
            value = default
        setattr(s, f.name, value)
    return s


def save_settings(s: Settings) -> None:
    store = QSettings("GlucoseOscBridge", "GlucoseOscBridge")
    for f in fields(Settings):
        store.setValue(f.name, getattr(s, f.name))


if HAVE_QT:

    class _Signals(QObject):
        done = Signal(object, str, str)  # Reading or None, error kind ("" when fine), detail

    class _PollTask(QRunnable):
        """Fetches from the phone off the UI thread."""

        def __init__(self, settings: Settings, signals: "_Signals"):
            super().__init__()
            self.settings = settings
            self.signals = signals

        def run(self):
            try:
                reading = parse_sgv(fetch_sgv(self.settings), self.settings.units)
                if reading is None:
                    self.signals.done.emit(None, "no_readings", "")
                else:
                    self.signals.done.emit(reading, "", "")
            except Exception as exc:
                self.signals.done.emit(None, "unreachable", str(exc))

    class MainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.s = load_settings()
            self.lang = resolve_ui_language(self.s.ui_language)
            self._boxes = []
            self._labels = []
            self.setWindowTitle(self.t("window_title"))
            self.reading: Optional[Reading] = None
            self.client: Optional[OscClient] = None
            self.running = False
            self.beat = False
            self.w = {}

            self.signals = _Signals()
            self.signals.done.connect(self._on_poll_done)
            self.pool = QThreadPool.globalInstance()
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self._poll)
            self.send_timer = QTimer(self)
            self.send_timer.setInterval(5000)  # resend + flip the heartbeat
            self.send_timer.timeout.connect(self._tick)

            root = QVBoxLayout(self)

            self.big = QLabel("--")
            self.big.setAlignment(Qt.AlignCenter)
            font = self.big.font()
            font.setPointSize(40)
            font.setBold(True)
            self.big.setFont(font)
            self.sub = QLabel(self.t("not_running"))
            self.sub.setAlignment(Qt.AlignCenter)
            root.addWidget(self.big)
            root.addWidget(self.sub)

            self.note = QLabel(self.t("note"))
            self.note.setWordWrap(True)
            self.note.setAlignment(Qt.AlignCenter)
            root.addWidget(self.note)

            root.addWidget(self._group("group_app", [
                ("ui_language", "ui_language", ("combo", ["auto"] + UI_LANGS)),
            ]))
            root.addWidget(self._group("group_xdrip", [
                ("phone_address", "phone_host", "line"),
                ("port", "phone_port", ("int", 1, 65535)),
                ("secret", "secret", "password"),
                ("check_every", "poll_seconds", ("int", 10, 600)),
                ("xdrip_sends", "units", ("combo", ["auto", "mg/dL", "mmol/L"])),
            ]))
            root.addWidget(self._group("group_osc", [
                ("osc_address", "osc_host", "line"),
                ("osc_port", "osc_port", ("int", 1, 65535)),
                ("avatar_shows", "display_units", ("combo", ["mmol/L", "mg/dL", "alternate", "rotate"])),
                ("alternate_every", "alternate_seconds", ("int", 5, 120)),
                ("rotate_every", "rotate_seconds", ("int", 5, 120)),
                ("stale_after", "stale_minutes", ("int", 1, 240)),
                ("low_below", "low_mmol", ("float", 1.0, 10.0)),
                ("high_above", "high_mmol", ("float", 5.0, 30.0)),
            ]))
            root.addWidget(self._group("group_params", [
                ("p_d1", "p_d1", "line"),
                ("p_d2", "p_d2", "line"),
                ("p_d3", "p_d3", "line"),
                ("p_trend", "p_trend", "line"),
                ("p_stale", "p_stale", "line"),
                ("p_low", "p_low", "line"),
                ("p_high", "p_high", "line"),
                ("p_mgdl", "p_mgdl", "line"),
                ("p_beat", "p_beat", "line"),
                ("p_words", "p_words", "line"),
            ]))

            buttons = QHBoxLayout()
            self.start_button = QPushButton(self.t("start"))
            self.start_button.clicked.connect(self._toggle)
            self.test_button = QPushButton(self.t("send_test"))
            self.test_button.clicked.connect(self._send_test)
            buttons.addWidget(self.start_button)
            buttons.addWidget(self.test_button)
            root.addLayout(buttons)

            self.log = QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(200)
            root.addWidget(self.log)

            self.w["ui_language"].currentTextChanged.connect(self._on_ui_language)

        def t(self, key: str, **fmt) -> str:
            return tr(self.lang, key, **fmt)

        def _on_ui_language(self, text):
            self.s.ui_language = text
            self.lang = resolve_ui_language(text)
            self._apply_language()

        def _apply_language(self):
            self.setWindowTitle(self.t("window_title"))
            self.note.setText(self.t("note"))
            for box, key in self._boxes:
                box.setTitle(self.t(key))
            for label, key in self._labels:
                label.setText(self.t(key))
            self.start_button.setText(self.t("stop" if self.running else "start"))
            self.test_button.setText(self.t("send_test"))
            self._refresh()

        # ----- building and reading the form -----

        def _group(self, title_key, rows):
            box = QGroupBox(self.t(title_key))
            self._boxes.append((box, title_key))
            form = QFormLayout(box)
            for label_key, name, kind in rows:
                value = getattr(self.s, name)
                if kind in ("line", "password"):
                    widget = QLineEdit(str(value))
                    if kind == "password":
                        widget.setEchoMode(QLineEdit.Password)
                elif kind[0] == "int":
                    widget = QSpinBox()
                    widget.setRange(kind[1], kind[2])
                    widget.setValue(int(value))
                elif kind[0] == "float":
                    widget = QDoubleSpinBox()
                    widget.setRange(kind[1], kind[2])
                    widget.setSingleStep(0.1)
                    widget.setDecimals(1)
                    widget.setValue(float(value))
                else:  # combo
                    widget = QComboBox()
                    widget.addItems(kind[1])
                    widget.setCurrentText(str(value))
                self.w[name] = widget
                label = QLabel(self.t(label_key))
                self._labels.append((label, label_key))
                form.addRow(label, widget)
            return box

        def _collect(self) -> Settings:
            s = Settings()
            for f in fields(Settings):
                widget = self.w[f.name]
                if isinstance(widget, QLineEdit):
                    value = widget.text().strip()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText()
                else:
                    value = widget.value()
                setattr(s, f.name, value)
            return s

        def _log(self, text: str):
            self.log.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

        # ----- running -----

        def _toggle(self):
            if self.running:
                self._stop()
            else:
                self._start()

        def _start(self):
            self.s = self._collect()
            save_settings(self.s)
            self.client = OscClient(self.s.osc_host, self.s.osc_port)
            self.running = True
            self.start_button.setText(self.t("stop"))
            self.poll_timer.start(self.s.poll_seconds * 1000)
            self.send_timer.start()
            self._log(self.t("started", host=self.s.phone_host, port=self.s.phone_port))
            self._poll()

        def _stop(self):
            self.running = False
            self.poll_timer.stop()
            self.send_timer.stop()
            if self.client:
                self.beat = not self.beat
                self.client.send_all(build_params(None, self.s, beat=self.beat))  # avatar shows "no data"
                self.client.close()
                self.client = None
            self.start_button.setText(self.t("start"))
            self.sub.setText(self.t("not_running"))
            self.big.setStyleSheet(f"color: {COLOR_STALE};")
            self._log(self.t("stopped"))

        def _poll(self):
            self.pool.start(_PollTask(self.s, self.signals))

        def _on_poll_done(self, reading, error: str, detail: str = ""):
            if error == "unreachable":
                self._log(self.t("unreachable", err=detail))
            elif error:
                self._log(self.t(error))
            elif reading is not None:
                self.reading = reading
                self._log(f"{format_value(reading.mmol, effective_units(self.s))} {effective_units(self.s)} "
                          f"{TREND_ARROW[reading.trend]}")
            self._refresh()

        def _tick(self):
            if self.client:
                self.beat = not self.beat
                self.client.send_all(build_params(self.reading, self.s, beat=self.beat))
            self._refresh()

        def _refresh(self):
            r = self.reading
            if r is None:
                self.big.setText("--")
                self.big.setStyleSheet(f"color: {COLOR_STALE};")
                self.sub.setText(self.t("waiting") if self.running else self.t("not_running"))
                return
            age = max(0.0, (time.time() - r.when) / 60.0)
            stale = age > self.s.stale_minutes
            tag = state_tag(r, self.s, stale)
            if stale:
                color = COLOR_STALE
            elif r.mmol < self.s.low_mmol:
                color = COLOR_LOW
            elif r.mmol > self.s.high_mmol:
                color = COLOR_HIGH
            else:
                color = COLOR_OK
            units_now = effective_units(self.s)
            value = format_value(r.mmol, units_now)
            self.big.setText(f"{value}  {TREND_ARROW[r.trend]}")
            self.big.setStyleSheet(f"color: {color};")
            tag_text = f" · {tag}" if tag else ""
            self.sub.setText(self.t("reading_age", units=units_now, age=f"{age:.0f}") + tag_text
                             + (" · " + self.t("stale_flag") if stale else ""))

        def _send_test(self):
            """Send one fixed set (6.0 mmol/L, flat) so you can check the avatar wiring."""
            s = self._collect()
            client = OscClient(s.osc_host, s.osc_port)
            sample = Reading(mmol=6.0, when=time.time(), trend=3)
            self.beat = not self.beat
            client.send_all(build_params(sample, s, beat=self.beat))
            client.close()
            self._log(self.t("sent_test", value=format_value(6.0, effective_units(s)), units=effective_units(s)))

        def closeEvent(self, event):
            self.s = self._collect()
            save_settings(self.s)
            if self.running:
                self._stop()
            event.accept()


def run_gui() -> int:
    if not HAVE_QT:
        print("The window needs PySide6 (Qt6 for Python). Install it with:\n"
              "    pip install PySide6\n"
              "or run without a window using --cli.", file=sys.stderr)
        return 2
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


def self_check() -> int:
    """Print what this build can do and exit 0 if every expected feature is present.
    Used by the build script on the finished AppImage / exe, so the check looks at the bundled code itself."""
    names = [n for n, _v in build_params(None, Settings(display_units="rotate"), now=0.0)]
    checks = [
        ("app languages", len(UI_LANGS) == 10 and set(UI_LANGS) >= {"zh-Hant", "ko", "pt-BR", "ru"}),
        ("every language has every label", all(set(APP_STRINGS["en"]) <= set(APP_STRINGS[c]) for c in UI_LANGS)),
        ("rotate display mode", display_phase(Settings(display_units="rotate", rotate_seconds=10), 25.0) == "words"),
        ("BG_Words parameter", "BG_Words" in names),
        ("no BG_Lang parameter (bridge does not set the avatar language)", "BG_Lang" not in names),
        ("parameter count", len(names) == 10),
    ]
    try:
        import PySide6  # noqa: F401
        checks.append(("Qt (PySide6) bundled", True))
    except Exception:
        checks.append(("Qt (PySide6) bundled", False))
    print("GlucOSC build self-check")
    for label, ok in checks:
        print(("  OK    " if ok else "  FAIL  ") + label)
    print("  languages: " + ", ".join(UI_LANGS))
    return 0 if all(ok for _l, ok in checks) else 1


def main() -> int:
    if "--self-check" in sys.argv[1:]:
        return self_check()
    parser = argparse.ArgumentParser(description="xDrip+ glucose to VRChat OSC bridge")
    parser.add_argument("--cli", action="store_true", help="run without the Qt window")
    parser.add_argument("--once", action="store_true", help="(cli) fetch once, send once, exit")
    parser.add_argument("--host", default=Settings.phone_host, help="phone address")
    parser.add_argument("--port", type=int, default=Settings.phone_port, help="xDrip+ web service port")
    parser.add_argument("--secret", default="", help="xDrip Web Service Secret")
    parser.add_argument("--interval", type=int, default=Settings.poll_seconds, help="seconds between checks")
    parser.add_argument("--units", default="auto", choices=["auto", "mg/dL", "mmol/L"],
                        help="units xDrip+ sends")
    parser.add_argument("--show-units", default="mmol/L", choices=["mmol/L", "mg/dL", "alternate", "rotate"],
                        help="what the avatar displays (alternate = flip between both units; "
                             "rotate = mmol/L, mg/dL, then the plain-words panel)")
    parser.add_argument("--alternate-sec", type=int, default=Settings.alternate_seconds,
                        help="seconds per unit in alternate mode")
    parser.add_argument("--rotate-sec", type=int, default=Settings.rotate_seconds,
                        help="seconds per step in rotate mode")
    parser.add_argument("--osc-host", default=Settings.osc_host)
    parser.add_argument("--osc-port", type=int, default=Settings.osc_port)
    parser.add_argument("--stale-min", type=int, default=Settings.stale_minutes)
    args = parser.parse_args()
    if args.cli:
        s = Settings(
            phone_host=args.host, phone_port=args.port, secret=args.secret,
            poll_seconds=args.interval, units=args.units, display_units=args.show_units, alternate_seconds=args.alternate_sec,
            rotate_seconds=args.rotate_sec,
            osc_host=args.osc_host, osc_port=args.osc_port, stale_minutes=args.stale_min,
        )
        return run_cli(s, once=args.once)
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())

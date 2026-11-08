#!/usr/bin/env python3
"""ExchangeKit — trading days & market holiday site for major exchanges.

Data: pandas_market_calendars sessions (2025-2028) joined with HolidayKit public
holiday names for readable labels. Output is a static site in dist/.

Usage:
  python build.py
  python build.py --site-url https://exchangekit.pages.dev
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

try:
    import qrcode  # type: ignore
except ImportError:  # pragma: no cover
    qrcode = None

import pandas_market_calendars as mcal

ROOT = Path(__file__).resolve().parent
HK = ROOT.parent / "holiday-kit"
sys.path.insert(0, str(HK / "scripts"))
from build_site import (COUNTRY_NAMES, flag_emoji, slugify,  # noqa: E402
    SISTER_CSS,
    sister_html,
                        deemoji, PAGE_SHARE_JS, SEARCH_CSS, SEARCH_JS,
                        support_strip, SUPPORT_CSS, hide_api, SHOW_API,
                          clean_links, faq_block, faq_json_ld)

SITE_NAME = "ExchangeKit"
SITE_URL = "https://exchangekit.pages.dev"
GOOGLE_VERIFY = "QfC8EpnSFGu7aWk17GyocmVaOBbTxTxy9lgJy3oYzfE"
BING_VERIFY = "B3A34B4B9EE2E3E70DA2BA8E04B03C88"
SITE_TAGLINE = "Trading days and market holidays for the world's exchanges."
_WEBSITE_LD = json.dumps({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": SITE_NAME,
    "url": SITE_URL + "/",
    "description": SITE_TAGLINE,
    "potentialAction": {
        "@type": "SearchAction",
        "target": {"@type": "EntryPoint",
                   "urlTemplate": SITE_URL + "/?q={search_term_string}"},
        "query-input": "required name=search_term_string",
    },
}, ensure_ascii=False)
YEARS = [2025, 2026, 2027, 2028]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

EXCHANGES = [
    ("XNYS", "New York Stock Exchange", "NYSE", "US", "New York", "America/New_York", "09:30", "16:00"),
    ("NASDAQ", "NASDAQ", "NASDAQ", "US", "New York", "America/New_York", "09:30", "16:00"),
    ("SSE", "Shanghai Stock Exchange", "SSE", "CN", "Shanghai", "Asia/Shanghai", "09:30", "15:00"),
    ("XHKG", "Hong Kong Stock Exchange", "HKEX", "HK", "Hong Kong", "Asia/Hong_Kong", "09:30", "16:00"),
    ("XTKS", "Tokyo Stock Exchange", "TSE", "JP", "Tokyo", "Asia/Tokyo", "09:00", "15:00"),
    ("XLON", "London Stock Exchange", "LSE", "GB", "London", "Europe/London", "08:00", "16:30"),
    ("XETR", "Xetra (Frankfurt)", "XETRA", "DE", "Frankfurt", "Europe/Berlin", "09:00", "17:30"),
    ("XPAR", "Euronext Paris", "EURONEXT", "FR", "Paris", "Europe/Paris", "09:00", "17:30"),
    ("XAMS", "Euronext Amsterdam", "AMS", "NL", "Amsterdam", "Europe/Amsterdam", "09:00", "17:30"),
    ("XMIL", "Borsa Italiana", "BIT", "IT", "Milan", "Europe/Rome", "09:00", "17:30"),
    ("XMAD", "Bolsa de Madrid", "BME", "ES", "Madrid", "Europe/Madrid", "09:00", "17:30"),
    ("XSWX", "SIX Swiss Exchange", "SIX", "CH", "Zurich", "Europe/Zurich", "09:00", "17:30"),
    ("XSTO", "Nasdaq Stockholm", "STO", "SE", "Stockholm", "Europe/Stockholm", "09:00", "17:30"),
    ("XOSL", "Oslo Børs", "OSL", "NO", "Oslo", "Europe/Oslo", "09:00", "16:30"),
    ("XCSE", "Nasdaq Copenhagen", "CPH", "DK", "Copenhagen", "Europe/Copenhagen", "09:00", "17:00"),
    ("XHEL", "Nasdaq Helsinki", "HEL", "FI", "Helsinki", "Europe/Helsinki", "10:00", "18:30"),
    ("XWAR", "Warsaw Stock Exchange", "WSE", "PL", "Warsaw", "Europe/Warsaw", "09:00", "17:00"),
    ("XTSE", "Toronto Stock Exchange", "TSX", "CA", "Toronto", "America/Toronto", "09:30", "16:00"),
    ("XASX", "Australian Securities Exchange", "ASX", "AU", "Sydney", "Australia/Sydney", "10:00", "16:00"),
    ("XNZE", "NZX", "NZX", "NZ", "Wellington", "Pacific/Auckland", "10:00", "16:45"),
    ("XNSE", "National Stock Exchange of India", "NSE", "IN", "Mumbai", "Asia/Kolkata", "09:15", "15:30"),
    ("XKRX", "Korea Exchange", "KRX", "KR", "Seoul", "Asia/Seoul", "09:00", "15:30"),
    ("XTAI", "Taiwan Stock Exchange", "TWSE", "TW", "Taipei", "Asia/Taipei", "09:00", "13:30"),
    ("XSES", "Singapore Exchange", "SGX", "SG", "Singapore", "Asia/Singapore", "09:00", "17:00"),
    ("XBKK", "Stock Exchange of Thailand", "SET", "TH", "Bangkok", "Asia/Bangkok", "10:00", "16:30"),
    ("XKLS", "Bursa Malaysia", "BURSA", "MY", "Kuala Lumpur", "Asia/Kuala_Lumpur", "09:00", "17:00"),
    ("B3", "B3 (Brasil Bolsa Balcão)", "B3", "BR", "São Paulo", "America/Sao_Paulo", "10:00", "17:00"),
    ("XJSE", "Johannesburg Stock Exchange", "JSE", "ZA", "Johannesburg", "Africa/Johannesburg", "09:00", "17:00"),
    ("XIST", "Borsa Istanbul", "BIST", "TR", "Istanbul", "Europe/Istanbul", "10:00", "18:00"),
    ("XMOS", "Moscow Exchange", "MOEX", "RU", "Moscow", "Europe/Moscow", "10:00", "18:40"),
    ("XTAE", "Tel Aviv Stock Exchange", "TASE", "IL", "Tel Aviv", "Asia/Jerusalem", "09:59", "17:14"),
    ("XIDX", "Indonesia Stock Exchange", "IDX", "ID", "Jakarta", "Asia/Jakarta", "09:00", "15:50"),
]

COORDS = {
    "XNYS": (40.7069, -74.0113), "NASDAQ": (40.7580, -73.9855),
    "SSE": (31.2358, 121.5075), "XHKG": (22.2840, 114.1620),
    "XTKS": (35.6812, 139.7671), "XLON": (51.5155, -0.0922),
    "XETR": (50.1109, 8.6821), "XPAR": (48.8566, 2.3522),
    "XAMS": (52.3676, 4.9041), "XMIL": (45.4642, 9.1900),
    "XMAD": (40.4168, -3.7038), "XSWX": (47.3769, 8.5417),
    "XSTO": (59.3293, 18.0686), "XOSL": (59.9139, 10.7522),
    "XCSE": (55.6761, 12.5683), "XHEL": (60.1699, 24.9384),
    "XWAR": (52.2297, 21.0122), "XTSE": (43.6487, -79.3817),
    "XASX": (-33.8688, 151.2093), "XNZE": (-41.2866, 174.7756),
    "XNSE": (19.0760, 72.8777), "XKRX": (37.5665, 126.9780),
    "XTAI": (25.0330, 121.5654), "XSES": (1.3521, 103.8198),
    "XBKK": (13.7563, 100.5018), "XKLS": (3.1390, 101.6869),
    "B3": (-23.5505, -46.6333), "XJSE": (-26.2041, 28.0473),
    "XIST": (41.0082, 28.9784), "XMOS": (55.7558, 37.6173),
    "XTAE": (32.0853, 34.7818), "XIDX": (-6.2088, 106.8456),
}

# country code -> approximate centre, used for "locate me"
COUNTRY_POS = {
    "US": (39.5, -98.4), "CA": (56.1, -106.3), "MX": (23.6, -102.6), "BR": (-14.2, -51.9),
    "AR": (-38.4, -63.6), "CL": (-35.7, -71.5), "CO": (4.6, -74.3), "PE": (-9.2, -75.0),
    "GB": (55.4, -3.4), "IE": (53.4, -8.2), "FR": (46.2, 2.2), "DE": (51.2, 10.4),
    "ES": (40.5, -3.7), "IT": (41.9, 12.6), "NL": (52.1, 5.3), "BE": (50.5, 4.5),
    "AT": (47.5, 14.6), "CH": (46.8, 8.2), "PT": (39.4, -8.2), "SE": (60.1, 18.6),
    "NO": (60.5, 8.5), "DK": (56.3, 9.5), "FI": (61.9, 25.7), "PL": (51.9, 19.1),
    "CZ": (49.8, 15.5), "HU": (47.2, 19.5), "GR": (39.1, 21.8), "RU": (61.5, 60.0),
    "UA": (48.4, 31.2), "TR": (39.0, 35.2), "IL": (31.0, 34.9), "SA": (23.9, 45.1),
    "AE": (23.4, 53.8), "EG": (26.8, 30.8), "ZA": (-30.6, 22.9), "NG": (9.1, 8.7),
    "KE": (0.0, 37.9), "CN": (35.9, 104.2), "JP": (36.2, 138.3), "KR": (35.9, 127.8),
    "TW": (23.7, 121.0), "HK": (22.3, 114.2), "SG": (1.35, 103.8), "MY": (4.2, 101.9),
    "TH": (15.9, 101.0), "VN": (14.1, 108.3), "ID": (-2.5, 118.0), "PH": (12.9, 121.8),
    "IN": (20.6, 78.9), "PK": (30.4, 69.3), "BD": (23.7, 90.4), "AU": (-25.3, 133.8),
    "NZ": (-41.0, 174.9), "SA_": (23.9, 45.1),
}

CSS = """
:root{--ink:#0f1115;--ink-soft:#2a2d36;--muted:#6b7080;--line:#e6e3da;--bg:#faf9f6;--surface:#fff;--soft:#f3f0e9;--accent:#0f6b5c;--accent-2:#0b4f44;--amber:#b5731a;--red:#b33a3a;--radius:20px;--radius-sm:14px;--ease:cubic-bezier(.16,1,.3,1);
--font-body:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;--font-display:ui-serif,Georgia,"Times New Roman","Songti SC",serif}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font-body);line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none;transition:color .15s}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 22px}
.site-head{position:sticky;top:0;z-index:30;background:rgba(250,249,246,.86);backdrop-filter:blur(16px);border-bottom:1px solid var(--line);transition:box-shadow .3s var(--ease)}
.site-head.scrolled{box-shadow:0 10px 34px rgba(15,17,21,.08)}
.head-inner{display:flex;align-items:center;justify-content:space-between;height:64px}
.brand{display:inline-flex;align-items:center;gap:9px;font-weight:700;color:var(--ink);font-size:1.05rem}
.brand-mark{display:inline-grid;place-items:center;width:29px;height:29px;border-radius:10px;background:linear-gradient(135deg,var(--accent),var(--accent-2));color:#fff;font-size:.8rem;box-shadow:0 6px 16px rgba(15,107,92,.28)}
nav{display:flex;gap:22px}nav a{color:var(--ink-soft);font-size:.9rem;font-weight:500;position:relative}
nav a::after{content:"";position:absolute;left:0;right:100%;bottom:-6px;height:2px;background:var(--accent);transition:right .25s var(--ease)}
nav a:hover::after{right:0}
.lang-select{border:1px solid var(--line);background:var(--surface);color:var(--ink-soft);border-radius:9px;padding:4px 8px;font-size:.8rem;margin-left:16px}
@media(max-width:640px){nav{flex-wrap:wrap;gap:10px}.lang-select{margin-left:0}}
.hero{padding:64px 0 12px;position:relative;overflow:hidden}
.hero::before{content:"";position:absolute;inset:-60% -10% auto -10%;height:140%;background:radial-gradient(620px 320px at 18% 8%,rgba(15,107,92,.10),transparent 62%),radial-gradient(520px 280px at 88% 0%,rgba(181,115,26,.10),transparent 60%);pointer-events:none}
.hero>*{position:relative}
.eyebrow{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--amber);font-weight:700;margin:0 0 12px}
h1{font-family:var(--font-display);font-size:clamp(2.1rem,4.8vw,3.4rem);line-height:1.08;letter-spacing:-.02em;margin:0 0 16px;font-weight:600}
.lede{font-size:1.06rem;color:var(--muted);max-width:40em;margin:0 0 24px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:var(--ink);color:#fff;border:1px solid var(--ink);border-radius:999px;padding:11px 22px;font-weight:600;font-size:.92rem;cursor:pointer;transition:transform .18s var(--ease),box-shadow .25s var(--ease),opacity .2s}
.btn:hover{transform:translateY(-1px);box-shadow:0 12px 28px rgba(15,17,21,.18);text-decoration:none}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-sm);padding:18px;transition:transform .28s var(--ease),box-shadow .28s var(--ease),border-color .28s}
.card:hover{transform:translateY(-3px);box-shadow:0 20px 48px rgba(15,17,21,.10)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:18px 0}
.grid a.card{display:block;color:var(--ink)}
.grid a.card:hover{text-decoration:none}
.grid h3{margin:6px 0 3px;font-size:.98rem}
.grid p{margin:0;color:var(--muted);font-size:.82rem}
.flag{font-size:1.25rem}
.sec{margin:44px 0}
.sec h2{font-family:var(--font-display);font-size:clamp(1.4rem,2.2vw,1.9rem);margin:0 0 8px}
.sec .sub{color:var(--muted);margin:0 0 18px;font-size:.95rem}
.status{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:5px 12px;font-size:.78rem;color:var(--ink-soft)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted)}
.dot.open{background:#1a9b63;animation:pulse 1.8s infinite}
.dot.closed{background:var(--red)}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(26,155,99,.45)}70%{box-shadow:0 0 0 7px rgba(26,155,99,0)}100%{box-shadow:0 0 0 0 rgba(26,155,99,0)}}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--surface)}
table{width:100%;border-collapse:collapse}
th,td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:left;font-size:.9rem}
th{background:var(--soft);font-size:.71rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700}
tr:last-child td{border-bottom:0}
tbody tr{transition:background .15s}
tbody tr:hover{background:#faf7f0}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.chip{font-size:.8rem;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:4px 12px}
.years{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 18px}
.years a{border:1px solid var(--line);border-radius:999px;padding:6px 14px;font-size:.86rem;color:var(--ink);transition:all .18s var(--ease)}
.years a:hover{border-color:var(--ink);text-decoration:none;transform:translateY(-1px)}
.years a.on{background:var(--ink);color:#fff;border-color:var(--ink)}
.bars{display:grid;gap:6px;margin:14px 0}
.bar-row{display:grid;grid-template-columns:52px 1fr 40px;gap:10px;align-items:center;font-size:.8rem;color:var(--muted)}
.bar{height:8px;border-radius:999px;background:var(--soft);overflow:hidden}
.bar i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--accent),#2f9d8a);width:0;transition:width .9s var(--ease)}
.reveal{opacity:0;transform:translateY(14px);transition:opacity .62s var(--ease),transform .62s var(--ease)}
.reveal.in{opacity:1;transform:none}
.ad{border:1px dashed #d8d3c7;background:#f7f4ee;color:#9a958a;border-radius:14px;padding:18px;min-height:90px;display:grid;place-items:center;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase;margin:28px 0}
.callout{border-left:3px solid var(--amber);background:#fdf6e9;padding:12px 16px;border-radius:10px;font-size:.9rem;margin:16px 0}
.faq dt{font-weight:650;margin-top:14px}.faq dd{margin:4px 0 0;color:var(--muted);font-size:.92rem}
.clock-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:10px}
.clock-head .sub{margin:4px 0 0}
.clock-badge{display:inline-flex;align-items:center;gap:8px;font-size:.8rem;border:1px solid var(--line);background:var(--surface);border-radius:999px;padding:5px 12px;white-space:nowrap}
.clock-badge b{font-variant-numeric:tabular-nums}
.clock-wrap{display:grid;grid-template-columns:1.45fr .55fr;gap:22px;align-items:start;margin-top:14px}
.mk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(196px,1fr));gap:12px}
.mk-card{display:block;border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:13px 14px;position:relative;overflow:hidden;transition:border-color .2s,box-shadow .2s,transform .2s;color:var(--ink)}
.mk-card:hover{text-decoration:none;transform:translateY(-2px);box-shadow:0 12px 26px -18px rgba(15,17,21,.35)}
.mk-card.is-open{border-color:rgba(26,155,99,.45)}
.mk-card.is-open:before{content:"";position:absolute;inset:0;pointer-events:none;background:radial-gradient(120% 90% at 100% 0%,rgba(52,211,153,.16),transparent 62%)}
.mk-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
.mk-code{font-weight:700;font-size:.82rem;letter-spacing:.07em;text-transform:uppercase}
.mk-city{font-size:.71rem;color:var(--muted);margin-top:2px}
.mk-state{display:inline-flex;align-items:center;gap:5px;font-size:.63rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;border-radius:999px;background:var(--soft);color:var(--muted);white-space:nowrap}
.mk-state.open{background:#e7f7ef;color:#0e7a4d}
.mk-state .dot{width:6px;height:6px}
.mk-time{font:700 1.3rem/1.15 ui-monospace,SFMono-Regular,Menlo,monospace;margin:10px 0 1px;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.mk-sub{font-size:.71rem;color:var(--muted);min-height:1.05em}
.mk-prog{height:5px;border-radius:999px;background:var(--soft);overflow:hidden;margin-top:9px}
.mk-prog i{display:block;height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,var(--accent),#2f9d8a);transition:width .55s linear}
.mk-card:not(.is-open) .mk-prog i{background:linear-gradient(90deg,#d9d2c4,#b9ad99)}
.mk-side{display:grid;gap:14px;position:sticky;top:78px}
.mk-panel{border:1px solid var(--line);border-radius:14px;background:var(--surface);padding:14px 15px}
.mk-panel h3{margin:0 0 10px;font-size:.9rem;display:flex;align-items:center;justify-content:space-between;gap:8px}
.mk-panel h3 span{font-size:.64rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.07em}
.mk-list{display:grid;gap:6px;margin:0;padding:0;list-style:none}
.mk-item{display:grid;grid-template-columns:46px minmax(0,1fr) auto auto;gap:9px;align-items:center;font-size:.79rem;padding:7px 9px;border-radius:9px;background:var(--soft)}
.mk-item b{font-variant-numeric:tabular-nums;font-size:.77rem}
.mk-item .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.mk-item .tm{color:var(--muted);font-size:.7rem;font-weight:400;text-align:right}
.mk-empty{font-size:.79rem;color:var(--muted);margin:2px 0 0}
.clock-note{font-size:.78rem;color:var(--muted);margin-top:12px}
.live-count{color:var(--muted);font-size:.88rem}
@media(max-width:900px){.clock-wrap{grid-template-columns:1fr}.mk-side{position:static;grid-template-columns:1fr 1fr}}
@media(max-width:640px){.mk-side{grid-template-columns:1fr}.mk-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}.mk-time{font-size:1.15rem}}
.site-foot{border-top:1px solid var(--line);margin-top:60px;padding:28px 0 44px;font-size:.84rem;color:var(--muted)}
.muted{color:var(--muted)}
@media(max-width:640px){nav{gap:12px}nav a{font-size:.8rem}.head-inner{height:auto;min-height:56px;flex-wrap:wrap;padding:8px 0}.hero{padding-top:40px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}html{scroll-behavior:auto}}
.sub-actions{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0 18px}
.sub-help{display:grid;gap:8px;margin:10px 0 14px}
.sub-help details{border:1px solid var(--line);border-radius:12px;background:var(--surface);padding:10px 14px}
.sub-help summary{cursor:pointer;font-weight:600;font-size:.9rem}
.sub-help ol{margin:8px 0 2px 18px;padding:0;color:var(--ink-soft);font-size:.88rem}
.sub-help li{margin:4px 0}
.sub-help code{background:var(--soft);padding:1px 6px;border-radius:6px;font-size:.82rem;word-break:break-all}
"""

I18N_JS = """
(function(){
  var D={
    en:{'nav.ex':'Exchanges','nav.map':'Live map','nav.hol':'Holidays','nav.api':'API','nav.about':'About',
      'hero.eyebrow':'Trading days · market holidays · 2025–2028','hero.h1':'Market holidays and trading days.',
      'hero.lede':'Every closure day for the world\\'s major stock exchanges, with trading-day counts, monthly breakdowns, one-click .ics subscriptions and a free JSON API.',
      'map.h2':'Market map — live open / closed','map.sub':'Every exchange on one interactive map. Green pulsing dots are markets open right now; we locate you automatically. Drag to pan, scroll to zoom.',
      'map.open':'Open now','map.closed':'Closed','map.you':'You','map.badge':'{n} / {m} markets open now',
      'ex.h2':'Exchanges','ex.sub':'Trading days and the next closure for {year}.',
      'clock.h2':'Market clock — live open / closed','clock.sub':'Live countdown to every open and close. Green cards are trading right now.',
      'clock.closing':'Closing soon','clock.opening':'Opening soon',
      'clock.note':'Times are each market’s local time. Exchange holidays are skipped automatically.','clock.live':'live',
      'foot.note':'Calendar dates follow each exchange’s official holiday schedule. Always confirm critical dates with the exchange.'},
    zh:{'nav.ex':'交易所','nav.map':'实时地图','nav.hol':'休市日','nav.api':'API','nav.about':'关于',
      'hero.eyebrow':'交易日 · 休市日 · 2025–2028','hero.h1':'全球交易所休市与交易日',
      'hero.lede':'全球主要交易所的每个休市日，附交易日数量、月度分布、一键 .ics 订阅与免费 JSON API。',
      'map.h2':'交易所地图 —— 实时开市/闭市','map.sub':'所有交易所尽在交互地图上。绿色脉冲点是当前正在开市的市场；我们会自动定位你。拖拽平移，滚轮缩放。',
      'map.open':'开市中','map.closed':'已闭市','map.you':'你','map.badge':'{n} / {m} 个市场正在开市',
      'ex.h2':'交易所','ex.sub':'{year} 年交易日与下一次休市。',
      'clock.h2':'交易所时钟 —— 实时开市/休市','clock.sub':'每个市场的开市、收市倒计时；绿色卡片为正在交易。',
      'clock.closing':'即将收盘','clock.opening':'即将开市',
      'clock.note':'时间均为交易所当地时间，已自动跳过交易所假期。','clock.live':'实时',
      'foot.note':'日期依据各交易所官方休市安排，重要日期请以交易所公告为准。'},
    ja:{'nav.ex':'取引所','nav.map':'ライブマップ','nav.hol':'休場日','nav.api':'API','nav.about':'概要',
      'hero.eyebrow':'取引日 · 休場日 · 2025–2028','hero.h1':'市場の休場日と取引日',
      'hero.lede':'世界の主要取引所の休場日を、取引日数・月別内訳・.ics購読・無料JSON API付きで。',
      'map.h2':'市場マップ — リアルタイム開場/閉場','map.sub':'すべての取引所を1つのインタラクティブマップに。緑の点は現在開場中。現在地を自動検出します。ドラッグで移動、スクロールでズーム。',
      'map.open':'開場中','map.closed':'閉場','map.you':'あなた','map.badge':'{n} / {m} 市場が開場中',
      'ex.h2':'取引所','ex.sub':'{year}年の取引日と次の休場日。',
      'foot.note':'取引所の公式休場日に基づきます。重要な日付は取引所の発表でご確認ください。'},
    ko:{'nav.ex':'거래소','nav.map':'실시간 지도','nav.hol':'휴장일','nav.api':'API','nav.about':'소개',
      'hero.eyebrow':'거래일 · 휴장일 · 2025–2028','hero.h1':'시장 휴장일과 거래일',
      'hero.lede':'세계 주요 거래소의 모든 휴장일, 거래일 수·월별 분포·.ics 구독·무료 JSON API 포함.',
      'map.h2':'시장 지도 — 실시간 개장/폐장','map.sub':'모든 거래소를 하나의 인터랙티브 지도에. 초록 점은 현재 개장 중인 시장입니다. 위치를 자동 감지합니다. 드래그로 이동, 스크롤로 확대.',
      'map.open':'개장 중','map.closed':'폐장','map.you':'나','map.badge':'{n} / {m} 시장 개장 중',
      'ex.h2':'거래소','ex.sub':'{year}년 거래일과 다음 휴장일.',
      'foot.note':'거래소의 공식 휴장일 기준입니다. 중요한 날짜는 거래소 공지로 확인하세요.'},
    es:{'nav.ex':'Bolsas','nav.map':'Mapa en vivo','nav.hol':'Festivos','nav.api':'API','nav.about':'Acerca de',
      'hero.eyebrow':'Días de cotización · festivos · 2025–2028','hero.h1':'Festivos y días de cotización',
      'hero.lede':'Cada cierre de las principales bolsas, con días de cotización, desglose mensual, suscripción .ics y API JSON gratuita.',
      'map.h2':'Mapa de mercados — abierto / cerrado en vivo','map.sub':'Todas las bolsas en un mapa interactivo. Los puntos verdes son mercados abiertos ahora; te localizamos automáticamente. Arrastra para mover, rueda para zoom.',
      'map.open':'Abierto','map.closed':'Cerrado','map.you':'Tú','map.badge':'{n} / {m} mercados abiertos',
      'ex.h2':'Bolsas','ex.sub':'Días de cotización y próximo cierre en {year}.',
      'foot.note':'Basados en el calendario oficial de cada bolsa. Confirma las fechas críticas con la bolsa.'},
    fr:{'nav.ex':'Bourses','nav.map':'Carte live','nav.hol':'Fériés','nav.api':'API','nav.about':'À propos',
      'hero.eyebrow':'Jours de bourse · fériés · 2025–2028','hero.h1':'Jours fériés et jours de bourse',
      'hero.lede':'Chaque fermeture des grandes bourses, avec jours de cotation, détail mensuel, abonnement .ics et API JSON gratuite.',
      'map.h2':'Carte des marchés — ouvert / fermé en direct','map.sub':'Toutes les bourses sur une carte interactive. Les points verts sont ouverts ; nous vous localisons automatiquement. Glissez pour déplacer, molette pour zoomer.',
      'map.open':'Ouvert','map.closed':'Fermé','map.you':'Vous','map.badge':'{n} / {m} marchés ouverts',
      'ex.h2':'Bourses','ex.sub':'Jours de cotation et prochaine fermeture en {year}.',
      'foot.note':'Basés sur le calendrier officiel de chaque bourse. Vérifiez les dates critiques auprès de la bourse.'},
    de:{'nav.ex':'Börsen','nav.map':'Live-Karte','nav.hol':'Feiertage','nav.api':'API','nav.about':'Über',
      'hero.eyebrow':'Handelstage · Feiertage · 2025–2028','hero.h1':'Marktfeiertage und Handelstage',
      'hero.lede':'Jeder Schließtag der großen Börsen, mit Handelstagen, Monatsübersicht, .ics-Abo und kostenloser JSON-API.',
      'map.h2':'Marktkarte — live offen / geschlossen','map.sub':'Alle Börsen auf einer interaktiven Karte. Grüne Punkte sind jetzt offen; wir orten Sie automatisch. Ziehen zum Verschieben, Scrollen zum Zoomen.',
      'map.open':'Offen','map.closed':'Geschlossen','map.you':'Sie','map.badge':'{n} / {m} Märkte offen',
      'ex.h2':'Börsen','ex.sub':'Handelstage und nächste Schließung in {year}.',
      'foot.note':'Basierend auf dem offiziellen Handelskalender der jeweiligen Börse. Kritische Termine bitte bei der Börse prüfen.'}
  };
  var CC_LANG={CN:'zh',TW:'zh',HK:'zh',SG:'zh',JP:'ja',KR:'ko',ES:'es',MX:'es',AR:'es',CO:'es',CL:'es',PE:'es',FR:'fr',BE:'fr',CA:'fr',DE:'de',AT:'de',CH:'de'};
  var lang='en';
  try{ var saved=localStorage.getItem('ex_lang'); if(saved&&D[saved]) lang=saved; }catch(e){}
  function detect(){ var n=(navigator.language||'en').toLowerCase(), b=n.split('-')[0]; return D[b]?b:'en'; }
  function t(k){ var d=D[lang]||D.en; return d[k]||D.en[k]||k; }
  var YEAR=window.EX_FOCUS_YEAR||new Date().getFullYear();
  function apply(){
    document.documentElement.lang=lang;
    document.querySelectorAll('[data-i18n]').forEach(function(el){ el.textContent=t(el.getAttribute('data-i18n')).replace('{year}', YEAR); });
    document.querySelectorAll('[data-hk-lang]').forEach(function(s){ s.value=lang; });
    document.dispatchEvent(new CustomEvent('hk-lang-changed'));
  }
  function set(l){ if(!D[l]) return; lang=l; try{localStorage.setItem('ex_lang',l);}catch(e){} apply(); }
  window.HKI18N={t:t,set:set,lang:function(){return lang;},apply:apply};
  document.addEventListener('DOMContentLoaded',function(){
    apply();
    document.querySelectorAll('[data-hk-lang]').forEach(function(s){ s.addEventListener('change',function(){set(this.value);}); });
    if(!localStorage.getItem('ex_lang')){
      var auto=detect();
      fetch('/geo').then(function(r){return r.ok?r.json():null;}).then(function(d){
        var c=((d&&d.country)||'').toUpperCase();
        var l=CC_LANG[c]||auto;
        if(D[l]) set(l);
      }).catch(function(){ if(auto!=='en') set(auto); });
    }
  });
})();
"""


CLOCK_JS = """
(function(){
  var M=window.EX_MARKETS||[]; if(!M.length) return;
  var C=window.EX_CLOSURES||{};
  var TT={
    en:{open:'Open now',closed:'Closed',holiday:'Market holiday',closes:'closes in',opens:'opens in',
        count:'{n} of {t} markets open now',local:'your local time',openAt:'opens',
        none:'No markets open right now.',wait:'waiting for next session',openFor:'open for',
        all:'Show all {t} markets',less:'Show fewer markets',hide:'show fewer'},
    zh:{open:'开市中',closed:'已休市',holiday:'假期休市',closes:'距收盘',opens:'距开盘',
        count:'{t} 个市场中 {n} 个正在开市',local:'你的本地时间',openAt:'开盘',
        none:'当前没有开市的市场。',wait:'等待下一个交易时段',openFor:'已开市',
        all:'展开全部 {t} 个市场',less:'收起市场列表',hide:'收起'}
  };
  var WD={
    en:['Sun','Mon','Tue','Wed','Thu','Fri','Sat'],
    zh:['周日','周一','周二','周三','周四','周五','周六'],
    ja:['日','月','火','水','木','金','土'],
    ko:['일','월','화','수','목','금','토']
  };
  function wdName(i){ var l=lang(); return (WD[l]||WD.en)[i]; }
  function lang(){ try{ return (window.HKI18N&&window.HKI18N.lang&&window.HKI18N.lang())||(document.documentElement.lang||'en').slice(0,2); }catch(e){ return 'en'; } }
  function t(){ return TT[lang()]||TT.en; }
  function pad(n){ return (n<10?'0':'')+n; }
  function clock(sec){ if(sec<0) sec=0; var d=Math.floor(sec/86400),h=Math.floor(sec%86400/3600),m=Math.floor(sec%3600/60),s=sec%60; return (d? d+'d '+pad(h)+':':'')+pad(m)+':'+pad(s); }
  function short(sec){ if(sec<0) sec=0; if(sec<60) return '<1m'; if(sec<3600) return Math.round(sec/60)+'m'; var h=Math.floor(sec/3600),m=Math.round(sec%3600/60); return h+'h'+(m?' '+m+'m':''); }
  var FMT={};
  function parts(tz){
    var f=FMT[tz]; if(!f){ f=FMT[tz]=new Intl.DateTimeFormat('en-GB',{timeZone:tz,weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}); }
    var now=new Date(), p=f.formatToParts(now), m={}; p.forEach(function(x){ m[x.type]=x.value; });
    var ds=new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
    return {wd:m.weekday,hm:m.hour+':'+m.minute,min:(+m.hour)*60+ +m.minute,sec:+m.second,date:ds};
  }
  function isHol(code,iso){ var y=C[code]; if(!y) return false; var a=y[iso.slice(0,4)]; return !!a && a.indexOf(iso)>=0; }
  function state(m,p){
    var wk=(p.wd==='Sat'||p.wd==='Sun'), hol=isHol(m.code,p.date);
    var om=(+m.open.split(':')[0])*60+ +m.open.split(':')[1], cm=(+m.close.split(':')[0])*60+ +m.close.split(':')[1];
    var open=!wk && !hol && p.min>=om && p.min<cm;
    var nextOpen=null, dow=null, days=0;
    if(!open){
      var base=new Date(Date.UTC(+p.date.slice(0,4),+p.date.slice(5,7)-1,+p.date.slice(8,10)));
      for(var k=0;k<15&&nextOpen===null;k++){
        var d=new Date(base.getTime()+k*86400000), wd=d.getUTCDay();
        if(wd===0||wd===6) continue;
        var iso=d.toISOString().slice(0,10);
        if(isHol(m.code,iso)) continue;
        if(k===0 && p.min>=om) continue;
        nextOpen=(k*1440+om-p.min)*60-p.sec; dow=wd; days=k;
      }
    }
    return {open:open,wk:wk,hol:hol,om:om,cm:cm,nextOpen:nextOpen,dow:dow,days:days,
            elapsed: open ? (p.min-om)*60+p.sec : 0,
            toClose: open ? (cm-p.min)*60-p.sec : null,
            pct: open ? Math.min(100,Math.max(1.5,(p.min-om)/(cm-om)*100)) : 0};
  }
  function els(id){ return document.getElementById(id); }
  var expanded=false, COLLAPSED=12;
  function render(){
    var host=els('ex-clock'); if(!host) return;
    var T=t(), rows=M.map(function(m){ var p=parts(m.tz); return {m:m,p:p,s:state(m,p)}; });
    var open=rows.filter(function(r){ return r.s.open; }).sort(function(a,b){ return a.s.toClose-b.s.toClose; });
    var closed=rows.filter(function(r){ return !r.s.open; }).sort(function(a,b){ return (a.s.nextOpen===null?1e9:a.s.nextOpen)-(b.s.nextOpen===null?1e9:b.s.nextOpen); });
    var badge=els('ex-clock-badge');
    if(badge){
      var now=new Date();
      badge.innerHTML='<span class="dot '+(open.length?'open':'closed')+'"></span>'+
        T.count.replace('{n}',open.length).replace('{t}',rows.length)+' · '+
        now.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'})+' <span class="muted">'+T.local+'</span>';
    }
    var grid=els('ex-clock-grid');
    if(grid){
      var cards=open.concat(closed).map(function(r){
        var st=r.s.open?T.open:(r.s.hol?T.holiday:T.closed);
        var main=r.s.open?clock(r.s.toClose):(r.s.nextOpen===null?'—':clock(r.s.nextOpen));
        var sub=r.s.open
          ? (T.openFor+' '+short(r.s.elapsed)+' · '+T.closes+' '+short(r.s.toClose))
          : (T.openAt+(r.s.days>0?' '+wdName(r.s.dow):'')+' '+r.m.open);
        return '<a class="mk-card'+(r.s.open?' is-open':'')+'" href="'+r.m.slug+'/index.html">'+
          '<div class="mk-top"><div><div class="mk-code">'+r.m.short+'</div><div class="mk-city">'+r.m.city+' · '+r.p.hm+'</div></div>'+
          '<span class="mk-state'+(r.s.open?' open':'')+'"><span class="dot '+(r.s.open?'open':'closed')+'"></span>'+st+'</span></div>'+
          '<div class="mk-time">'+main+'</div><div class="mk-sub">'+sub+'</div>'+
          '<div class="mk-prog"><i style="width:'+r.s.pct.toFixed(1)+'%"></i></div></a>';
      });
      grid.innerHTML=(expanded? cards : cards.slice(0, COLLAPSED)).join('');
      var more=els('ex-clock-more');
      if(more){
        more.style.display = cards.length>COLLAPSED ? '' : 'none';
        more.textContent = expanded ? T.less : T.all.replace('{t}', cards.length);
      }
    }
    var cl=els('ex-closing');
    if(cl){ cl.innerHTML=open.slice(0,6).map(function(r){
      return '<li class="mk-item"><b>'+r.m.short+'</b><span class="nm">'+r.m.city+'</span><span class="tm">'+r.m.close+'</span><b>'+short(r.s.toClose)+'</b></li>';
    }).join('')||'<li class="mk-empty">'+T.none+'</li>'; }
    var op=els('ex-opening');
    if(op){ op.innerHTML=closed.slice(0,6).map(function(r){
      var n=r.s.nextOpen===null?T.wait:short(r.s.nextOpen);
      return '<li class="mk-item"><b>'+r.m.short+'</b><span class="nm">'+r.m.city+'</span><span class="tm">'+r.m.open+'</span><b>'+n+'</b></li>';
    }).join(''); }
  }
  render();
  var moreBtn=document.getElementById('ex-clock-more');
  if(moreBtn){ moreBtn.addEventListener('click', function(){ expanded=!expanded; render(); }); }
  setInterval(render, 1000);
  document.addEventListener('hk-lang-changed', render);
  document.addEventListener('visibilitychange', function(){ if(!document.hidden) render(); });
})();
"""


MAP_PATH = ""
try:
    MAP_PATH = json.loads((ROOT / "data" / "world_land.json").read_text(encoding="utf-8")).get("path") or ""
except (OSError, ValueError):
    MAP_PATH = ""

MAP_CSS = """
.map-badge{display:inline-flex;align-items:center;gap:7px;font-size:.8rem;color:var(--ink-soft);background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:4px 12px;margin-left:8px}
.map-wrap{position:relative;border:1px solid rgba(255,255,255,.08);border-radius:20px;overflow:hidden;background:radial-gradient(120% 90% at 30% 0%,#0e2b27 0%,#0a1420 55%,#060a11 100%);box-shadow:0 26px 70px rgba(10,16,24,.28)}
#exmap{display:block;width:100%;height:auto;cursor:grab;touch-action:none}
#exmap.dragging{cursor:grabbing}
.map-land{fill:#1d4a42;stroke:#2f6f64;stroke-width:.7;vector-effect:non-scaling-stroke}
.ex-dot{cursor:pointer}
.ex-dot .core{fill:#9aa3b2;transition:fill .3s;stroke:rgba(0,0,0,.35);stroke-width:.6}
.ex-dot .ring{fill:none;stroke:transparent;transform-box:fill-box;transform-origin:center}
.ex-dot.open .core{fill:#34d399}
.ex-dot.open .ring{stroke:#34d399;animation:exping 1.9s ease-out infinite}
.ex-dot.closed .core{fill:#f87171}
.ex-dot:hover .core{stroke:#fff;stroke-width:1.4}
@keyframes exping{0%{transform:scale(.5);opacity:.85}75%{transform:scale(2.4);opacity:0}100%{opacity:0}}
.you-dot .core{fill:#38bdf8}
.you-dot .ring{fill:none;stroke:#38bdf8;transform-box:fill-box;transform-origin:center;animation:youpulse 2.2s ease-out infinite}
@keyframes youpulse{0%{transform:scale(.6);opacity:.8}70%{transform:scale(3.2);opacity:0}100%{opacity:0}}
.map-tip{position:absolute;pointer-events:none;background:rgba(10,16,26,.95);color:#e8edf5;border:1px solid rgba(255,255,255,.16);border-radius:11px;padding:8px 12px;font-size:.78rem;line-height:1.45;opacity:0;transform:translate(-50%,-125%);transition:opacity .15s;white-space:nowrap;z-index:5;box-shadow:0 12px 30px rgba(0,0,0,.35)}
.map-tip.on{opacity:1}
.map-controls{position:absolute;right:12px;top:12px;display:flex;flex-direction:column;gap:6px}
.map-controls button{width:34px;height:34px;border-radius:10px;border:1px solid rgba(255,255,255,.18);background:rgba(10,16,26,.68);color:#e8edf5;cursor:pointer;font-size:1rem;line-height:1;backdrop-filter:blur(6px);transition:background .18s,transform .18s}
.map-controls button:hover{background:rgba(34,197,94,.22);transform:translateY(-1px)}
.map-legend{position:absolute;left:12px;bottom:12px;display:flex;gap:14px;color:#c7d2e0;font-size:.74rem;background:rgba(10,16,26,.62);border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:6px 12px;backdrop-filter:blur(6px)}
.map-legend .lg{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px}
.lg.open{background:#22c55e;box-shadow:0 0 8px #22c55e}
.lg.closed{background:#ef4444}
.lg.you{background:#38bdf8;box-shadow:0 0 8px #38bdf8}
@media(max-width:640px){.map-legend{font-size:.66rem;gap:10px}.map-controls button{width:30px;height:30px}}
"""

MAP_JS = """
(function(){
  var svg=document.getElementById('exmap'); if(!svg) return;
  var g=document.getElementById('map-g'), tip=document.getElementById('map-tip');
  var W=1000,H=500;
  var COUNTRY_POS=""" + json.dumps(COUNTRY_POS, separators=(",", ":")) + """;
  function px(lat,lon){ return [(lon+180)/360*W,(90-lat)/180*H]; }
  var markers=[].slice.call(document.querySelectorAll('.ex-dot'));
  markers.forEach(function(m){
    var p=px(parseFloat(m.getAttribute('data-lat')),parseFloat(m.getAttribute('data-lon')));
    m.setAttribute('transform','translate('+p[0].toFixed(1)+','+p[1].toFixed(1)+')');
  });
  function status(m){
    var tz=m.getAttribute('data-tz'), open=m.getAttribute('data-open'), close=m.getAttribute('data-close');
    try{
      var parts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(new Date());
      var map={}; parts.forEach(function(p){ map[p.type]=p.value; });
      var hm=map.hour+':'+map.minute, wd=map.weekday;
      var isOpen = (wd!=='Sat'&&wd!=='Sun') && hm>=open && hm<close;
      return {open:isOpen,local:hm};
    }catch(e){ return {open:false,local:'—'}; }
  }
  function applyStatus(){
    var openCount=0;
    markers.forEach(function(m){
      var s=status(m);
      m.classList.toggle('open',s.open); m.classList.toggle('closed',!s.open);
      if(s.open) openCount++;
    });
    var badge=document.getElementById('map-open-count');
    if(badge){
      var tpl=(window.HKI18N?window.HKI18N.t('map.badge'):'{n} / {m} markets open now');
      badge.textContent=tpl.replace('{n}',openCount).replace('{m}',markers.length);
    }
  }
  applyStatus(); setInterval(applyStatus,30000);
  document.addEventListener('hk-lang-changed', applyStatus);
  function showTip(m,ev){
    var s=status(m);
    var openTxt=(window.HKI18N?window.HKI18N.t(s.open?'map.open':'map.closed'):(s.open?'Open':'Closed'));
    tip.innerHTML='<strong>'+m.getAttribute('data-short')+'</strong> · '+m.getAttribute('data-city')+
      '<br><span style="color:'+(s.open?'#34d399':'#f87171')+'">'+openTxt+
      '</span> · '+s.local;
    tip.classList.add('on');
    var rect=svg.parentNode.getBoundingClientRect();
    tip.style.left=Math.max(70,Math.min(rect.width-70,ev.clientX-rect.left))+'px';
    tip.style.top=(ev.clientY-rect.top)+'px';
  }
  markers.forEach(function(m){
    m.addEventListener('pointerenter',function(e){ showTip(m,e); });
    m.addEventListener('pointermove',function(e){ showTip(m,e); });
    m.addEventListener('pointerleave',function(){ tip.classList.remove('on'); });
    m.addEventListener('click',function(){ location.href=m.getAttribute('data-href'); });
  });
  var view={x:0,y:0,k:1};
  function apply(){ g.setAttribute('transform','translate('+view.x.toFixed(2)+','+view.y.toFixed(2)+') scale('+view.k.toFixed(3)+')'); }
  apply();
  var drag=null;
  svg.addEventListener('pointerdown',function(e){ drag={x:e.clientX,y:e.clientY,vx:view.x,vy:view.y}; svg.classList.add('dragging'); try{svg.setPointerCapture(e.pointerId);}catch(err){} });
  svg.addEventListener('pointermove',function(e){ if(!drag) return; var r=svg.getBoundingClientRect(); var k=W/r.width; view.x=drag.vx+(e.clientX-drag.x)*k; view.y=drag.vy+(e.clientY-drag.y)*k; apply(); });
  function endDrag(){ drag=null; svg.classList.remove('dragging'); }
  svg.addEventListener('pointerup',endDrag); svg.addEventListener('pointercancel',endDrag);
  function zoomAt(factor,cx,cy){
    var nk=Math.min(9,Math.max(1,view.k*factor));
    view.x=cx-(cx-view.x)*nk/view.k; view.y=cy-(cy-view.y)*nk/view.k; view.k=nk; apply();
  }
  svg.addEventListener('wheel',function(e){ e.preventDefault(); var r=svg.getBoundingClientRect();
    zoomAt(e.deltaY<0?1.18:1/1.18,(e.clientX-r.left)*W/r.width,(e.clientY-r.top)*H/r.height); },{passive:false});
  var ctr=[W/2,H/2];
  svg.parentNode.querySelectorAll('[data-map-zoom]').forEach(function(b){
    b.addEventListener('click',function(){ zoomAt(b.getAttribute('data-map-zoom')==='in'?1.4:1/1.4,ctr[0],ctr[1]); });
  });
  var resetBtn=svg.parentNode.querySelector('[data-map-reset]');
  if(resetBtn) resetBtn.addEventListener('click',function(){ flyTo(0,0,1); });
  function animateTo(t,k){
    var s={x:view.x,y:view.y,k:view.k}, t0=performance.now(), dur=650;
    function step(now){
      var p=Math.min(1,(now-t0)/dur), e=1-Math.pow(1-p,3);
      view.x=s.x+(t.x-s.x)*e; view.y=s.y+(t.y-s.y)*e; view.k=s.k+(t.k-s.k)*e; apply();
      if(p<1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  function flyTo(lat,lon,k){
    var p=px(lat,lon); var nk=k||2.2;
    animateTo({x:W/2-p[0]*nk,y:H/2-p[1]*nk,k:nk});
  }
  function addYou(lat,lon){
    var p=px(lat,lon);
    var ns='http://www.w3.org/2000/svg';
    var yg=document.createElementNS(ns,'g');
    yg.setAttribute('class','you-dot'); yg.setAttribute('transform','translate('+p[0].toFixed(1)+','+p[1].toFixed(1)+')');
    var r1=document.createElementNS(ns,'circle'); r1.setAttribute('class','ring'); r1.setAttribute('r','10');
    var r2=document.createElementNS(ns,'circle'); r2.setAttribute('class','core'); r2.setAttribute('r','3.2');
    yg.appendChild(r1); yg.appendChild(r2); g.appendChild(yg);
    g.appendChild(yg);
  }
  function locate(){
    fetch('/geo').then(function(r){ return r.ok?r.json():null; }).then(function(d){
      var cc=d&&(d.country||''); cc=(cc||'').toUpperCase();
      var pos=COUNTRY_POS[cc];
      if(pos){ addYou(pos[0],pos[1]); flyTo(pos[0],pos[1],2.3); }
    }).catch(function(){
      try{ var tz=Intl.DateTimeFormat().resolvedOptions().timeZone||''; if(/Shanghai|Chongqing|Urumqi/.test(tz)){ var p=COUNTRY_POS['CN']; addYou(p[0],p[1]); flyTo(p[0],p[1],2.3); } }catch(e){}
    });
  }
  var locBtn=svg.parentNode.querySelector('[data-map-locate]');
  if(locBtn) locBtn.addEventListener('click',locate);
  locate();
})();
"""

MOTION_JS = """
(function(){
  var head=document.querySelector('.site-head');
  function onScroll(){ if(head) head.classList.toggle('scrolled', window.scrollY>8); }
  window.addEventListener('scroll', onScroll, {passive:true}); onScroll();
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduce && 'IntersectionObserver' in window) {
    var io=new IntersectionObserver(function(es){ es.forEach(function(en){ if(en.isIntersecting){ en.target.classList.add('in'); io.unobserve(en.target); } }); }, {rootMargin:'0px 0px -40px 0px', threshold:0.08});
    document.querySelectorAll('.sec,.card,.tbl-wrap,.bars,.hero').forEach(function(el){ el.classList.add('reveal'); io.observe(el); });
  }
  var bars=document.querySelectorAll('.bar i');
  if (bars.length) {
    var barIO=new IntersectionObserver(function(es){ es.forEach(function(en){ if(en.isIntersecting){ en.target.style.width=en.target.getAttribute('data-w'); barIO.unobserve(en.target); } }); }, {threshold:0.3});
    bars.forEach(function(b){ barIO.observe(b); });
  }
  // live market status + open/close countdown
  var EXC=window.EX_CLOSURES||{};
  function exZh(){
    try { if(window.HKI18N&&window.HKI18N.lang&&window.HKI18N.lang()==='zh') return true; } catch(e){}
    return (document.documentElement.lang||'').indexOf('zh')===0;
  }
  function exHol(code, iso){ if(!code) return false; var y=EXC[code]; if(!y) return false; var a=y[iso.slice(0,4)]; return !!a && a.indexOf(iso)>=0; }
  function exFmt(sec){
    if(sec===null) return '';
    sec=Math.max(0,Math.round(sec));
    if(sec<60) return '<1m';
    if(sec<3600) return Math.round(sec/60)+'m';
    var h=Math.floor(sec/3600), m=Math.round(sec%3600/60);
    return h+'h'+(m?' '+m+'m':'');
  }
  document.querySelectorAll('[data-live-market]').forEach(function(el){
    var tz=el.getAttribute('data-tz'), open=el.getAttribute('data-open'), close=el.getAttribute('data-close'), code=el.getAttribute('data-code');
    if (!tz) return;
    var om=(+open.split(':')[0])*60+ +open.split(':')[1], cm=(+close.split(':')[0])*60+ +close.split(':')[1];
    function update(){
      try {
        var now=new Date();
        var f=update._f||(update._f=new Intl.DateTimeFormat('en-GB',{timeZone:tz,weekday:'short',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}));
        var parts=f.formatToParts(now), map={}; parts.forEach(function(p){ map[p.type]=p.value; });
        var hm=map.hour+':'+map.minute;
        var min=(+map.hour)*60+ +map.minute, sec=+map.second;
        var iso=new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
        var isWeekend=(map.weekday==='Sat'||map.weekday==='Sun');
        var isHol=exHol(code, iso);
        var isOpen=!isWeekend && !isHol && min>=om && min<cm;
        var dot=el.querySelector('.dot'), label=el.querySelector('[data-live-label]'), cnt=el.querySelector('[data-live-count]');
        if(dot) dot.className='dot '+(isOpen?'open':'closed');
        var zh=exZh();
        if(label) label.textContent=isOpen?(zh?'开市中':'Market open now'):(isHol?(zh?'假期休市':'Market holiday'):(zh?'已休市':'Market closed'));
        if(cnt){
          if(isOpen){ cnt.textContent=(zh?' · 已开市 ':' · open for ')+exFmt((min-om)*60+sec)+(zh?' · 距收盘 ':' · closes in ')+exFmt((cm-min)*60-sec); }
          else {
            var base=new Date(Date.UTC(+iso.slice(0,4), +iso.slice(5,7)-1, +iso.slice(8,10))), nx=null;
            for(var k=0;k<15&&nx===null;k++){
              var d=new Date(base.getTime()+k*86400000), wd=d.getUTCDay();
              if(wd===0||wd===6) continue;
              var ds=d.toISOString().slice(0,10);
              if(exHol(code, ds)) continue;
              if(k===0 && min>=om) continue;
              nx=(k*1440+om-min)*60-sec;
            }
            cnt.textContent=nx===null?'':((zh?' · 距开盘 ':' · opens in ')+exFmt(nx));
          }
        }
      } catch(e){}
    }
    update(); setInterval(update, 1000);
  });
  var ua = navigator.userAgent || '';
  var isIOS = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && /Safari/.test(ua));
  var isAndroid = /Android/i.test(ua);
  document.body.className += (isAndroid ? ' is-android' : (isIOS ? ' is-ios' : ' is-desktop'));
  document.querySelectorAll('.sub-help details').forEach(function(d){
    var t = (d.querySelector('summary') || {}).textContent || '';
    var match = (isAndroid && t.indexOf('Android') >= 0) || (isIOS && (t.indexOf('iPhone') >= 0 || t.indexOf('Mac') >= 0));
    d.open = match;
  });
  document.querySelectorAll('[data-copy]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var text = btn.getAttribute('data-copy');
      function done(){ btn.textContent = 'Copied!'; setTimeout(function(){ btn.textContent = 'Copy .ics link'; }, 1600); }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function(){});
      } else {
        var ta = document.createElement('textarea'); ta.value = text;
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch (e) {}
        ta.parentNode.removeChild(ta); done();
      }
    });
  });
})();
"""



SHARE_CSS = """
.ic{display:inline-block;vertical-align:-0.14em;flex:none}
.kpi-ico .ic{width:20px;height:20px}
.sec-h-ico{display:inline-flex;align-items:center;justify-content:center;vertical-align:-2px}
.sec-h-ico .ic{width:18px;height:18px;stroke-width:1.9}
h3 .ic{width:.95em;height:.95em;vertical-align:-0.08em;opacity:.85}
.cd-ico .ic{width:18px;height:18px;color:#7dd3a8}
.flag{font-size:.66rem;font-weight:800;letter-spacing:.09em;color:var(--muted);
  background:rgba(15,23,42,.05);border:1px solid var(--line);border-radius:7px;
  padding:3px 7px;display:inline-block;line-height:1.2;vertical-align:2px;text-align:center;min-width:2.1em}
h1 .flag{font-size:.30em;letter-spacing:.10em;vertical-align:.55em;padding:3px 7px;opacity:.85}

.share-modal{position:fixed;inset:0;z-index:80;background:rgba(8,12,18,.66);backdrop-filter:blur(6px);display:none;align-items:center;justify-content:center;padding:20px}
.share-modal.on{display:flex}
.share-panel{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:18px;max-width:min(780px,96vw);max-height:94vh;overflow:auto;box-shadow:0 30px 80px rgba(10,16,24,.35)}
.share-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;font-size:.95rem}
.share-close{border:1px solid var(--line);background:var(--surface);width:32px;height:32px;border-radius:10px;cursor:pointer;font-size:1rem;line-height:1}
.share-canvas{display:block;width:100%;max-height:52vh;height:auto;border-radius:12px;background:#111;margin:0 auto}
.share-controls{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
.share-controls label{font-size:.72rem;color:var(--muted);display:flex;flex-direction:column;gap:4px;text-transform:uppercase;letter-spacing:.06em}
.share-controls select{padding:7px 10px;border:1px solid var(--line);border-radius:9px;background:var(--surface);font-size:.85rem;text-transform:none}
.share-btns{display:flex;gap:8px;flex-wrap:wrap}
.share-btns .btn{padding:9px 16px;font-size:.85rem}
.share-platforms{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.share-plat{border:1px solid var(--line);background:var(--surface);color:var(--ink-soft);border-radius:999px;padding:7px 14px;font-size:.8rem;cursor:pointer;transition:all .18s}
.share-plat:hover{border-color:var(--ink);transform:translateY(-1px)}
.share-hint{font-size:.72rem;color:var(--muted);margin:10px 0 0;line-height:1.5}
/* prominent share CTA + floating button */
.btn-share-hot{position:relative;display:inline-flex;align-items:center;gap:9px;border:0;cursor:pointer;font-weight:700;font-size:.95rem;padding:14px 24px;border-radius:999px;color:#04231a;background:linear-gradient(100deg,#34d399,#22d3ee,#a78bfa,#34d399);background-size:280% 100%;animation:exhotgrad 7s linear infinite;box-shadow:0 12px 32px rgba(34,211,238,.32),0 0 0 1px rgba(255,255,255,.28) inset;transition:transform .18s,box-shadow .18s}
.btn-share-hot:hover{transform:translateY(-2px) scale(1.02);box-shadow:0 18px 42px rgba(34,211,238,.42)}
@keyframes exhotgrad{to{background-position:280% 50%}}
.share-fab{position:fixed;right:20px;bottom:100px;z-index:70;display:inline-flex;align-items:center;gap:9px;padding:12px 18px;border-radius:999px;border:1px solid rgba(255,255,255,.35);cursor:pointer;color:#04231a;font-weight:800;font-size:.86rem;background:linear-gradient(120deg,#34d399,#22d3ee);box-shadow:0 12px 30px rgba(34,211,238,.38);animation:exfabpulse 2.8s ease-in-out infinite;transition:transform .18s}
.share-fab:hover{transform:translateY(-3px) scale(1.04)}
.share-fab .sf-ic{width:22px;height:22px;display:grid;place-items:center;border-radius:7px;background:rgba(255,255,255,.4);font-size:.95rem;line-height:1}
@keyframes exfabpulse{0%,100%{box-shadow:0 12px 30px rgba(34,211,238,.38),0 0 0 0 rgba(52,211,153,.5)}50%{box-shadow:0 12px 30px rgba(34,211,238,.38),0 0 0 15px rgba(52,211,153,0)}}
@media (max-width:720px){.share-fab{right:12px;bottom:78px;padding:10px 14px;font-size:.8rem}.btn-share-hot{padding:12px 18px;font-size:.88rem}}
/* KPI tiles + animated donut */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:18px 0 6px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.kpi-n{display:block;font-family:Georgia,serif;font-size:2.05rem;line-height:1.05;letter-spacing:-.02em}
.kpi-l{display:block;color:var(--muted);font-size:.74rem;margin-top:6px;text-transform:uppercase;letter-spacing:.08em}
.donut-wrap{display:flex;align-items:center;gap:26px;flex-wrap:wrap;margin:10px 0}
.vz-donut{width:156px;height:156px;transform:rotate(-90deg);flex:0 0 auto}
.vz-donut .bg{fill:none;stroke:rgba(148,163,184,.25);stroke-width:14}
.vz-donut .fg{fill:none;stroke:#34d399;stroke-width:14;stroke-linecap:round;animation:donutDraw 1.25s cubic-bezier(.2,.75,.25,1) .12s both}
@keyframes donutDraw{from{stroke-dashoffset:314.159}to{stroke-dashoffset:var(--target,0)}}
@media (prefers-reduced-motion:reduce){.vz-donut .fg{animation:none}}
.donut-txt{display:flex;flex-direction:column;gap:6px}
.donut-txt .big{font-family:Georgia,serif;font-size:1.9rem;line-height:1}
.donut-txt .muted{font-size:.78rem;color:var(--muted)}
/* dashboard-style icon cards + notes */
.kpi{display:flex;align-items:flex-start;gap:13px}
.kpi-ico{flex:0 0 auto;width:40px;height:40px;border-radius:12px;display:grid;place-items:center;font-size:1.05rem;line-height:1;background:linear-gradient(135deg,rgba(52,211,153,.20),rgba(34,211,238,.16));border:1px solid rgba(52,211,153,.26)}
.kpi-b{display:flex;flex-direction:column;min-width:0}
.sec-h-ico{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:8px;background:rgba(52,211,153,.15);font-size:.9rem;margin-right:10px;vertical-align:-4px}
.viz-note{color:var(--muted);font-size:.86rem;line-height:1.65;margin:16px 0 0;max-width:72ch}
.vz-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.72rem;color:var(--muted);margin-top:10px}
.vz-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
/* card sparkline */
.spark{display:flex;align-items:flex-end;gap:2px;height:26px;margin:8px 0 2px}
.spark i{flex:1;min-height:2px;border-radius:2px 2px 1px 1px;background:linear-gradient(180deg,#34d399,#0ea5e9);transform-origin:bottom;animation:sparkGrow .8s cubic-bezier(.2,.75,.25,1) both}
@keyframes sparkGrow{from{transform:scaleY(.05)}to{transform:scaleY(1)}}
.card-note{font-size:.72rem;color:var(--muted);margin:2px 0 6px}
@media (prefers-reduced-motion:reduce){.spark i{animation:none}}
"""


SHARE_JS = r"""
(function(){
  var D=window.EX_SHARE; if(!D) return;
  var TPL={
    midnight:{bg:['#0c1a1f','#070d13'],ink:'#eaf3f2',sub:'#93aaa8',accent:'#34d399',cell:'rgba(255,255,255,.055)',line:'rgba(255,255,255,.14)'},
    paper:{bg:['#f7f3e8','#ece4d2'],ink:'#1c1a16',sub:'#6b6152',accent:'#b5731a',cell:'rgba(255,255,255,.55)',line:'rgba(28,26,22,.14)'},
    terminal:{bg:['#04080a','#081410'],ink:'#e7fff4',sub:'#79d6a4',accent:'#7cffb2',cell:'rgba(124,255,178,.07)',line:'rgba(124,255,178,.26)'},
    dawn:{bg:['#ffe9ee','#e6efff'],ink:'#272138',sub:'#6a6280',accent:'#6d5cff',cell:'rgba(255,255,255,.6)',line:'rgba(39,33,56,.13)'}
  };
  var SIZES={story:[1080,1350],square:[1080,1080],wide:[1600,900]};
  var st={tpl:'midnight',size:'story',qr:null};
  var canvas=null,modal=null,qrImg=null;
  function px(n){return Math.round(n);}
  function rr(ctx,x,y,w,h,r){var q=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+q,y);ctx.arcTo(x+w,y,x+w,y+h,q);ctx.arcTo(x+w,y+h,x,y+h,q);ctx.arcTo(x,y+h,x,y,q);ctx.arcTo(x,y,x+w,y,q);ctx.closePath();}
  function draw(){
    if(!canvas)return;
    var S=SIZES[st.size],W=S[0],H=S[1];canvas.width=W;canvas.height=H;
    var ctx=canvas.getContext('2d'),t=TPL[st.tpl];
    var g=ctx.createLinearGradient(0,0,W,H);g.addColorStop(0,t.bg[0]);g.addColorStop(1,t.bg[1]);ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
    var P=px(W*0.06);
    ctx.fillStyle=t.ink;ctx.font='700 '+px(W*0.034)+'px Georgia,serif';ctx.fillText('ExchangeKit',P,px(H*0.085));
    ctx.fillStyle=t.sub;ctx.font='400 '+px(W*0.016)+'px system-ui';ctx.fillText('Trading days · market holidays',P,px(H*0.115));
    ctx.textAlign='right';ctx.fillStyle=t.accent;ctx.font='700 '+px(W*0.05)+'px Georgia,serif';ctx.fillText(String(D.year),W-P,px(H*0.095));ctx.textAlign='left';
    ctx.fillStyle=t.ink;ctx.font='600 '+px(W*0.056)+'px Georgia,"Songti SC","Microsoft YaHei",serif';
    ctx.fillText(D.short+' market holidays',P,px(H*0.185));
    ctx.fillStyle=t.sub;ctx.font='400 '+px(W*0.018)+'px system-ui';ctx.fillText(D.name,P,px(H*0.213));
    var boxTop=px(H*0.25),boxH=px(H*0.10),boxW=px(W*0.42);
    ctx.fillStyle=t.cell;rr(ctx,P,boxTop,boxW,boxH,px(W*0.014));ctx.fill();ctx.strokeStyle=t.line;ctx.lineWidth=1;ctx.stroke();
    ctx.fillStyle=t.accent;ctx.font='700 '+px(W*0.082)+'px Georgia,serif';ctx.fillText(String(D.tradingDays),P+px(W*0.02),boxTop+px(H*0.062));
    ctx.fillStyle=t.sub;ctx.font='500 '+px(W*0.0125)+'px system-ui';ctx.fillText('trading days in '+D.year,P+px(W*0.02),boxTop+px(H*0.085));
    var box2x=P+boxW+px(W*0.02);
    ctx.fillStyle=t.cell;rr(ctx,box2x,boxTop,boxW,boxH,px(W*0.014));ctx.fill();ctx.strokeStyle=t.line;ctx.stroke();
    ctx.fillStyle=t.accent;ctx.font='700 '+px(W*0.082)+'px Georgia,serif';ctx.fillText(String(D.closures.length),box2x+px(W*0.02),boxTop+px(H*0.062));
    ctx.fillStyle=t.sub;ctx.font='500 '+px(W*0.0125)+'px system-ui';ctx.fillText('market holidays',box2x+px(W*0.02),boxTop+px(H*0.085));
    ctx.fillStyle=t.ink;ctx.font='700 '+px(W*0.016)+'px system-ui';ctx.fillText('Closure days',P,px(H*0.425));
    var list=D.closures.slice(0,12), lh=px(H*0.027), per=Math.ceil(list.length/2);
    list.forEach(function(c,i){
      var col=Math.floor(i/per), row=i%per;
      var x=P+col*px(W*0.44), y=px(H*0.455)+row*lh;
      ctx.fillStyle=t.accent;ctx.font='600 '+px(W*0.0105)+'px system-ui';ctx.fillText(c.d,x,y);
      ctx.fillStyle=t.ink;ctx.font='400 '+px(W*0.0105)+'px system-ui';ctx.fillText(c.n,x+px(W*0.072),y);
    });
    var fy=px(H*0.84);
    ctx.strokeStyle=t.line;ctx.beginPath();ctx.moveTo(P,fy);ctx.lineTo(W-P,fy);ctx.stroke();
    ctx.fillStyle=t.ink;ctx.font='600 '+px(W*0.017)+'px system-ui';ctx.fillText('ExchangeKit',P,fy+px(H*0.035));
    ctx.fillStyle=t.sub;ctx.font='400 '+px(W*0.0105)+'px system-ui';ctx.fillText(D.url.replace('https://',''),P,fy+px(H*0.058));
    ctx.fillText('Scan to open the calendar',P,fy+px(H*0.078));
    if(st.qr){var qs=px(Math.min(W*0.105,H*0.105)),qx=W-P-qs,qy=fy+px(H*0.012);
      ctx.fillStyle='#ffffff';rr(ctx,qx-px(W*0.006),qy-px(W*0.006),qs+px(W*0.012),qs+px(W*0.012),px(W*0.008));ctx.fill();
      ctx.drawImage(st.qr,qx,qy,qs,qs);}
  }
  function ensure(){
    if(modal)return modal;
    var wrap=document.createElement('div');wrap.className='share-modal';
    wrap.innerHTML='<div class="share-panel"><div class="share-head"><strong>Share card</strong>'+
      '<button type="button" class="share-close" aria-label="Close">x</button></div>'+
      '<canvas class="share-canvas"></canvas>'+
      '<div class="share-controls"><label>Style<select data-share-tpl>'+Object.keys(TPL).map(function(k){return '<option value="'+k+'">'+k+'</option>';}).join('')+'</select></label>'+
      '<label>Size<select data-share-size><option value="story">Story 4:5</option><option value="square">Square</option><option value="wide">Wide</option></select></label></div>'+
      '<div class="share-btns"><button type="button" class="btn" data-share-dl>Download PNG</button>'+
      '<button type="button" class="btn ghost" data-share-native>Share</button>'+
      '<button type="button" class="btn ghost" data-share-copy>Copy image</button></div>'+
      '<div class="share-platforms" data-share-platforms></div>'+
      '<p class="share-hint">Shortcuts open the platform composer with text + link. For image-only apps (WeChat Moments, Xiaohongshu, Douyin, Instagram) tap "Download PNG" first, then post the image there.</p></div>';
    document.body.appendChild(wrap);modal=wrap;canvas=wrap.querySelector('.share-canvas');
    wrap.querySelector('.share-close').addEventListener('click',function(){wrap.classList.remove('on');});
    wrap.addEventListener('click',function(e){if(e.target===wrap)wrap.classList.remove('on');});
    wrap.querySelector('[data-share-tpl]').addEventListener('change',function(){st.tpl=this.value;draw();});
    wrap.querySelector('[data-share-size]').addEventListener('change',function(){st.size=this.value;draw();});
    wrap.querySelector('[data-share-dl]').addEventListener('click',function(){dl();});
    wrap.querySelector('[data-share-native]').addEventListener('click',function(){nativeShare();});
    wrap.querySelector('[data-share-copy]').addEventListener('click',function(){copy();});
    return wrap;
  }
  function toBlob(cb){canvas.toBlob(function(b){cb(b);},'image/png');}
  var CP={CN:['wechat','weibo','xhs','douyin'],TW:['line','facebook','whatsapp'],HK:['whatsapp','wechat','facebook'],
    JP:['line','x','facebook'],KR:['kakao','facebook','x'],US:['x','facebook','reddit','linkedin'],
    GB:['x','facebook','whatsapp','linkedin'],CA:['x','facebook','whatsapp'],AU:['facebook','x','whatsapp'],
    IN:['whatsapp','x','telegram','linkedin'],SG:['whatsapp','telegram','facebook'],MY:['whatsapp','facebook','telegram'],
    TH:['line','facebook','x'],VN:['facebook','zalo'],ID:['whatsapp','facebook','instagram'],PH:['facebook','whatsapp'],
    DE:['whatsapp','facebook','x'],FR:['whatsapp','facebook','x'],ES:['whatsapp','facebook','x'],IT:['whatsapp','facebook','x'],
    NL:['whatsapp','facebook','x'],PL:['facebook','x','whatsapp'],RU:['vk','telegram','whatsapp'],
    BR:['whatsapp','instagram','facebook'],MX:['whatsapp','facebook','x'],AR:['whatsapp','facebook','x'],
    ZA:['whatsapp','facebook','x'],AE:['whatsapp','telegram','x'],SA:['whatsapp','x','telegram'],
    TR:['whatsapp','x','telegram'],IL:['whatsapp','facebook','telegram'],EG:['whatsapp','facebook','x'],
    NG:['whatsapp','facebook','x'],KE:['whatsapp','facebook','x'],NZ:['facebook','x','whatsapp'],
    SE:['facebook','whatsapp','x'],NO:['facebook','whatsapp'],DK:['facebook','whatsapp'],FI:['whatsapp','facebook','x'],
    CH:['whatsapp','facebook','x'],AT:['whatsapp','facebook','x'],PT:['whatsapp','facebook','x'],GR:['facebook','whatsapp','x']};
  var PN={x:'X',facebook:'Facebook',whatsapp:'WhatsApp',telegram:'Telegram',line:'LINE',weibo:'微博',
    wechat:'微信',xhs:'小红书',douyin:'抖音',kakao:'KakaoTalk',vk:'VK',reddit:'Reddit',linkedin:'LinkedIn',
    instagram:'Instagram',zalo:'Zalo'};
  function platformHref(id,cap,url){
    var u=encodeURIComponent(url), t=encodeURIComponent(cap);
    if(id==='x')return 'https://twitter.com/intent/tweet?text='+t+'&url='+u;
    if(id==='facebook')return 'https://www.facebook.com/sharer/sharer.php?u='+u;
    if(id==='linkedin')return 'https://www.linkedin.com/sharing/share-offsite/?url='+u;
    if(id==='reddit')return 'https://www.reddit.com/submit?url='+u+'&title='+t;
    if(id==='whatsapp')return 'https://wa.me/?text='+encodeURIComponent(cap+' '+url);
    if(id==='telegram')return 'https://t.me/share/url?url='+u+'&text='+t;
    if(id==='line')return 'https://social-plugins.line.me/lineit/share?url='+u;
    if(id==='weibo')return 'https://service.weibo.com/share/share.php?url='+u+'&title='+t;
    if(id==='kakao')return 'https://story.kakao.com/share?url='+u;
    if(id==='vk')return 'https://vk.com/share.php?url='+u;
    if(id==='zalo')return 'https://zalo.me/share?u='+u;
    return '';
  }
  function caption(){ return 'ExchangeKit · '+D.short+' '+D.year+': '+D.tradingDays+' trading days, '+D.closures.length+' market holidays · '+D.url; }
  function renderPlatforms(){
    if(!modal)return;
    var box=modal.querySelector('[data-share-platforms]'); if(!box)return;
    var cc=(window.EX_COUNTRY||'').toUpperCase();
    var ids=CP[cc]||['x','facebook','whatsapp','telegram','linkedin'];
    box.innerHTML='';
    ids.forEach(function(id){
      var b=document.createElement('button'); b.type='button'; b.className='share-plat'; b.textContent=PN[id]||id;
      b.addEventListener('click',function(){
        var h=platformHref(id,caption(),D.url);
        if(h){ window.open(h,'_blank','noopener'); }
        else { try{navigator.clipboard.writeText(caption());}catch(e){} dl(); alert(PN[id]+' 不支持网页直接带图发布：图片已下载、文案已复制，请打开 App 发布。'); }
      });
      box.appendChild(b);
    });
  }
  function detectCountry(){
    if(window.EX_COUNTRY)return;
    fetch('/geo').then(function(r){return r.ok?r.json():null;}).then(function(d){
      window.EX_COUNTRY=((d&&d.country)||'').toUpperCase(); renderPlatforms();
    }).catch(function(){ renderPlatforms(); });
  }
  function dl(){toBlob(function(b){var a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='exchangekit-'+D.slug+'-'+D.year+'.png';document.body.appendChild(a);a.click();setTimeout(function(){URL.revokeObjectURL(a.href);a.remove();},800);});}
  function nativeShare(){toBlob(function(b){var f=new File([b],'exchangekit.png',{type:'image/png'});if(navigator.canShare&&navigator.canShare({files:[f]})){navigator.share({files:[f],title:'ExchangeKit',text:D.short+' '+D.year+' market holidays'}).catch(function(){});}else{dl();}});}
  function copy(){toBlob(function(b){if(navigator.clipboard&&window.ClipboardItem){navigator.clipboard.write([new ClipboardItem({'image/png':b})]).then(function(){alert('Copied image / 图片已复制');},function(){dl();});}else{dl();}});}
  function open(){ensure().classList.add('on');draw();detectCountry();renderPlatforms();}
  qrImg=new Image();qrImg.onload=function(){st.qr=qrImg;if(modal)draw();};qrImg.src=D.qr;
  document.querySelectorAll('[data-share-open]').forEach(function(b){b.addEventListener('click',function(e){e.preventDefault();open();});});
  if(new URLSearchParams(location.search).has('share')){window.addEventListener('load',open);}
  // floating, always-visible share CTA
  (function(){
    if(document.querySelector('.share-fab')) return;
    var lang=(document.documentElement.lang||'en').slice(0,2);
    var TXT={zh:'分享卡片',ja:'共有カード',ko:'공유 카드',es:'Compartir',fr:'Partager',de:'Teilen'};
    var fab=document.createElement('button');
    fab.type='button'; fab.className='share-fab'; fab.setAttribute('aria-label','Share card');
    fab.innerHTML='<span class="sf-ic" aria-hidden="true">✨</span><span class="sf-txt">'+(TXT[lang]||'Share card')+'</span>';
    fab.addEventListener('click', function(){ open(); });
    document.body.appendChild(fab);
  })();
})();
"""


CRUMB_CSS = """
.crumbs{font-size:.78rem;color:var(--muted);margin:2px 0 18px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.crumbs a{color:var(--muted);text-decoration:none;border-bottom:1px solid transparent}
.crumbs a:hover{color:var(--ink);border-bottom-color:currentColor}
.crumbs span[aria-current]{color:var(--ink);font-weight:600}
.crumbs .sep{opacity:.45}
"""


def _crumb_block(crumbs, canonical: str, esc_fn=None) -> tuple:
    """Return (visible html, ld json string) for a breadcrumb trail."""
    import json as _json
    from urllib.parse import urljoin as _urljoin
    esc_ = esc_fn or (lambda s: s)
    items, parts = [], []
    for i, (label, href) in enumerate(crumbs, start=1):
        item = {"@type": "ListItem", "position": i, "name": label}
        if href:
            item["item"] = _urljoin(canonical, href)
            parts.append(f'<a href="{href}">{esc_(label)}</a>')
        else:
            parts.append(f'<span aria-current="page">{esc_(label)}</span>')
        items.append(item)
    html = '<nav class="crumbs" aria-label="Breadcrumb">' + '<span class="sep">›</span>'.join(parts) + "</nav>"
    ld = _json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
                      "itemListElement": items}, ensure_ascii=False)
    return html, ld


_CSS_CACHE: dict[str, str] = {}


def _css_bundle() -> str:
    if "css" not in _CSS_CACHE:
        bundle = CSS + MAP_CSS + SHARE_CSS + SUPPORT_CSS + SEARCH_CSS + CRUMB_CSS + SISTER_CSS
        _CSS_CACHE["css"] = bundle
        _CSS_CACHE["ver"] = hashlib.md5(bundle.encode("utf-8")).hexdigest()[:10]
    return _CSS_CACHE["css"]


def _css_ver() -> str:
    _css_bundle()
    return _CSS_CACHE["ver"]


def page(title: str, desc: str, canonical: str, body: str, base: str = "", script: str = "",
         robots: str = "index,follow", hol_href: str = "", crumbs: list | None = None,
         lang: str = "en", alternates: str = "",
         json_ld: str = "") -> str:
    _json_ld_script = (f'<script type="application/ld+json">{json_ld}</script>'
                       if json_ld else "")
    nav = (
        '<header class="site-head"><div class="wrap head-inner">'
        f'<a class="brand" href="{base}index.html"><span class="brand-mark">◈</span>{SITE_NAME}</a>'
        '<button type="button" class="nav-search" data-search-open aria-label="Search">'
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.9" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/>'
        '<path d="M15.5 15.5L21 21"/></svg><span>Search</span><kbd>⌘K</kbd></button>'
        f'<nav><a href="{base}index.html" data-i18n="nav.ex">Exchanges</a>'
        f'<a href="{base}index.html#map" data-i18n="nav.map">Live map</a>'
        f'<a href="{base}api/index.html" data-i18n="nav.api">API</a>'
        f'<a href="{base}about/index.html" data-i18n="nav.about">About</a></nav>'
        '<select class="lang-select" data-hk-lang aria-label="Language">'
        '<option value="en">EN</option><option value="zh">中文</option><option value="ja">日本語</option>'
        '<option value="ko">한국어</option><option value="es">ES</option><option value="fr">FR</option>'
        '<option value="de">DE</option></select>'
        "</div></header>"
    )
    foot = (
        '<footer class="site-foot"><div class="wrap">'
        f'<p><strong>{SITE_NAME}</strong> — {SITE_TAGLINE}</p>'
        f'<p><span data-i18n="foot.note">Schedules follow the official holiday calendar of each exchange.</span> '
        "For planning only — confirm with the exchange for critical dates.</p>"
        f'<p><a href="{base}privacy/index.html">Privacy</a> · <a href="{base}about/index.html">About</a> · '
        f'<a href="{base}support/index.html">♥ Support · 打赏</a></p>'
        + lang_links(base)
        + sister_html(SITE_NAME)
        + "</div></footer>"
    )
    _ex_crumb_html, _ex_crumb_ld = ("", "")
    if crumbs:
        _ex_crumb_html, _ex_crumb_ld = _crumb_block(crumbs, canonical)
    _ex_crumb_head = (
        f'<script type="application/ld+json">{_ex_crumb_ld}</script>' if _ex_crumb_ld else ""
    )
    html = (
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title>"
        f'<meta name="description" content="{desc}">'
        f'<link rel="canonical" href="{canonical}">'
        f"{alternates}"
        f'<meta name="robots" content="{robots}">'
        f'<meta name="google-site-verification" content="{GOOGLE_VERIFY}">'
        f'<meta name="msvalidate.01" content="{BING_VERIFY}">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f'<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{title}">'
        f'<meta property="og:description" content="{desc}">'
        f'<meta property="og:url" content="{canonical}">'
        f'<meta property="og:image" content="{SITE_URL}/og-cover.png">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<script type="application/ld+json">{_WEBSITE_LD}</script>'
        f"{_json_ld_script}"
        f'<link rel="stylesheet" href="{base}assets/site.css?v={_css_ver()}">'
        f"</head><body>{nav}"
        + _ex_crumb_head
        + f'<main class="wrap">{_ex_crumb_html}{body}</main>{foot}'
        + f'<script>window.HK_BASE="{base}";</script>'
        + f"<script>{SEARCH_JS}</script>"
        + f"<script>{MOTION_JS}</script><script>{I18N_JS}</script>{script}<script>{PAGE_SHARE_JS}</script></body></html>"
    )
    return clean_links(hide_api(deemoji(html)))


FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0f1115"/>'
    '<path d="M14 46V30M26 46V22M38 46V34M50 46V18" stroke="#faf9f6" stroke-width="4" stroke-linecap="round"/>'
    '<circle cx="50" cy="18" r="4" fill="#b5731a"/></svg>'
)


LANG_CODES = ["zh", "ja", "ko", "es", "fr", "de"]

LANG_LABELS = {"en": "English", "zh": "中文", "ja": "日本語", "ko": "한국어",
               "es": "Español", "fr": "Français", "de": "Deutsch"}

LANG_TEXT = {
    "zh": [
        "全球交易所交易日与休市日",
        "32 家交易所每个年份的交易日数量、休市日历、一键 .ics 订阅与免费 JSON API。",
        "查看交易所",
        "开市时钟"
    ],
    "ja": [
        "世界の取引所の取引日数と休場日",
        "32 の取引所の年間取引日数、休場カレンダー、.ics 購読、無料 JSON API。",
        "取引所を見る",
        "マーケット時計"
    ],
    "ko": [
        "세계 거래소 거래일과 휴장일",
        "32개 거래소의 연간 거래일 수, 휴장 일정, .ics 구독과 무료 JSON API.",
        "거래소 보기",
        "시장 시계"
    ],
    "es": [
        "Días de negociación y festivos bursátiles",
        "Días de negociación por año, calendario de cierres, .ics y API JSON gratis para 32 bolsas.",
        "Ver bolsas",
        "Reloj de mercados"
    ],
    "fr": [
        "Jours de bourse et jours de fermeture",
        "Jours de cotation par an, calendrier des fermetures, .ics et API JSON gratuite pour 32 bourses.",
        "Voir les bourses",
        "Horloge des marchés"
    ],
    "de": [
        "Handelstage und Börsenfeiertage",
        "Handelstage pro Jahr, Schließungskalender, .ics und kostenlose JSON-API für 32 Börsen.",
        "Börsen ansehen",
        "Marktuhr"
    ]
}


def hreflang_links(site_url: str) -> str:
    parts = ['<link rel="alternate" hreflang="en" href="' + site_url + '/">']
    for code in LANG_CODES:
        parts.append('<link rel="alternate" hreflang="' + code + '" href="' + site_url + '/' + code + '/">')
    parts.append('<link rel="alternate" hreflang="x-default" href="' + site_url + '/">')
    return "".join(parts)


def lang_links(base: str) -> str:
    items = ['<a href="' + base + 'index.html">English</a>']
    for code in LANG_CODES:
        items.append('<a href="' + base + code + '/index.html">' + LANG_LABELS[code] + "</a>")
    return '<p class="lang-links">' + " · ".join(items) + "</p>"


def page_lang_home(lang: str, site_url: str) -> str:
    t = LANG_TEXT[lang]
    title, lede, cta1, cta2 = t[0], t[1], t[2], t[3]
    extra_cta = ('<a class="btn ghost" href="../index.html#countries">' + t[4] + "</a>") if len(t) > 4 else ""
    cta2_href = "../index.html#clock"
    body = (
        '<section class="hero"><p class="eyebrow">' + SITE_NAME + " · " + LANG_LABELS[lang] + "</p>"
        + "<h1>" + title + "</h1><p class='lede'>" + lede + "</p>"
        + '<div class="cta-row"><a class="btn" href="../index.html">' + cta1 + "</a>"
        + '<a class="btn ghost" href="' + cta2_href + '">' + cta2 + "</a>"
        + extra_cta
        + "</div></section>"
        + '<p class="viz-note">Localized entry page — the tool itself switches language automatically.</p>'
        + support_strip("../", "ExchangeKit")
    )
    return page(title=title, desc=lede, canonical=site_url + "/" + lang + "/", body=body,
                base="../", lang=lang, alternates=hreflang_links(site_url))


def page_support(site_url: str) -> str:
    def media(img: str, alt: str) -> str:
        path = ROOT / "assets" / "support" / f"{img}.png"
        if path.exists():
            return f'<img class="sup-qr" src="../assets/support/{img}.png" alt="{alt}" loading="lazy">'
        return f'<div class="sup-ph" aria-hidden="true">QR<br><code>assets/support/{img}.png</code></div>'

    cards = "".join([
        '<div class="sup-card">' + media("wechat", "WeChat tip QR code") +
        '<h3>微信赞赏</h3><p>扫码随意打赏，金额随意。</p></div>',
        '<div class="sup-card">' + media("alipay", "Alipay tip QR code") +
        '<h3>支付宝</h3><p>扫码打赏，支持项目持续更新。</p></div>',
        '<div class="sup-card"><div class="sup-ico">☕</div><h3>Buy me a coffee</h3>'
        '<p>International cards / PayPal.</p>'
        '<a class="btn" href="https://buymeacoffee.com/" target="_blank" rel="noopener">Open</a></div>',
        '<div class="sup-card"><div class="sup-ico">★</div><h3>GitHub Sponsors</h3>'
        '<p>Monthly or one-time sponsorship.</p>'
        '<a class="btn" href="https://github.com/sponsors/ChaoyuZhang1" target="_blank" '
        'rel="noopener">Sponsor</a></div>',
    ])
    body = (
        '<style>'
        '.sup-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:22px 0}'
        '@media(max-width:820px){.sup-grid{grid-template-columns:repeat(2,1fr)}}'
        '@media(max-width:460px){.sup-grid{grid-template-columns:1fr}}'
        '.sup-card{background:#fff;border:1px solid #e5e2da;border-radius:16px;padding:18px;text-align:center}'
        '.sup-qr{width:100%;max-width:180px;border-radius:12px;display:block;margin:0 auto 12px}'
        '.sup-ph{height:150px;border:2px dashed #d9d3c7;border-radius:12px;display:flex;flex-direction:column;'
        'align-items:center;justify-content:center;gap:6px;color:#8a8274;font-size:.78rem;margin-bottom:12px}'
        '.sup-ph code{font-size:.7rem;word-break:break-all}'
        '.sup-ico{font-size:2.2rem;line-height:1;margin:26px 0 14px}'
        '.sup-card h3{margin:0 0 6px;font-size:1.02rem}.sup-card p{color:#6b6558;font-size:.86rem;margin:0 0 12px}'
        '</style>'
        '<section class="hero"><p class="eyebrow">SUPPORT · 打赏支持</p>'
        '<h1>Keep ExchangeKit free</h1>'
        '<p class="lede">If ExchangeKit saved you time, you can buy me a coffee. Tips are optional — the '
        'calendars, ICS feeds and API stay free for everyone.</p></section>'
        '<section class="sec"><h2>打赏方式</h2><div class="sup-grid">' + cards + '</div>'
        '<p class="muted">打赏完全自愿，不换取任何功能、数据或优先级。</p></section>'
        '<section class="sec"><h2>打赏用在哪里</h2><ul>'
        '<li>维护 32 家交易所的休市规则与假期数据</li>'
        '<li>域名、CDN 与构建基础设施费用</li>'
        '<li>继续扩充交易所与年份覆盖</li></ul></section>'
        '<section class="sec"><h2>Commercial API use</h2>'
        '<p>The JSON API is free under a generous fair-use policy. For commercial use or a higher-volume '
        'guarantee, a sponsor licence is available — tip above and get in touch.</p></section>'
    )
    return page("Support ExchangeKit · 打赏支持",
                "Support ExchangeKit with a tip — WeChat, Alipay, Buy Me a Coffee or GitHub Sponsors.",
                f"{site_url}/support/", body, base="../")


def webcal_url(https_url: str) -> str:
    return https_url.replace("https://", "webcal://", 1)


def google_cal_url(ics_url: str) -> str:
    return "https://calendar.google.com/calendar/r?cid=" + quote(webcal_url(ics_url), safe="")


def outlook_cal_url(ics_url: str) -> str:
    return "https://outlook.live.com/calendar/0/addfromweb?url=" + quote(ics_url, safe="")


def subscribe_block(short: str, slug: str, year: int, site_url: str) -> str:
    ics = f"{site_url}/{slug}/calendar-{year}.ics"
    wc = webcal_url(ics)
    return (
        f'<section class="sec" id="subscribe"><h2>Subscribe to {short} market holidays {year}</h2>'
        '<p class="sub">One URL — auto-updating calendar. Works with iOS, macOS, Google Calendar and Outlook; '
        "no .ics file import needed.</p>"
        '<div class="sub-actions">'
        f'<a class="btn" href="{wc}">📱 iOS / macOS — one-tap subscribe</a>'
        f'<a class="btn ghost" href="{google_cal_url(ics)}" target="_blank" rel="noopener">Add to Google Calendar</a>'
        f'<a class="btn ghost" href="/go/{slug}/">Android — one-tap setup</a>'
        f'<a class="btn ghost" href="{outlook_cal_url(ics)}" target="_blank" rel="noopener">Add to Outlook</a>'
        f'<button type="button" class="btn ghost" data-copy="{ics}">Copy .ics link</button>'
        "</div>"
        '<div class="sub-help">'
        "<details open><summary>iPhone / iPad / Mac — subscribe (auto-updates)</summary><ol>"
        "<li>Tap <strong>iOS / macOS — one-tap subscribe</strong> → Calendar opens → tap <strong>Subscribe</strong>.</li>"
        "<li>Or Settings → Calendar → Accounts → Add Account → Other → <strong>Add Subscribed Calendar</strong>, "
        f"paste <code>{ics}</code>.</li></ol></details>"
        "<details><summary>Android — Google Calendar can't open webcal links; use one of these</summary><ol>"
        "<li>Browser → <a href=\"https://calendar.google.com/calendar/r/settings/addbyurl\" target=\"_blank\" "
        'rel="noopener">Google Calendar → Add calendar → From URL</a> → paste the .ics URL.</li>'
        "<li>Or install <strong>ICSx5</strong> to sync the .ics subscription into the Android system calendar.</li>"
        "<li>Samsung Calendar: Settings → Add calendar → Subscribe → paste URL.</li></ol></details>"
        "<details><summary>Outlook / Windows</summary><ol>"
        "<li>Outlook → Calendar → Add calendar → Subscribe from web → paste the .ics link.</li></ol></details>"
        "</div>"
        f'<p class="muted">Direct .ics link (HTTPS): <code>{ics}</code></p></section>'
    )


def go_page(short: str, slug: str, year: int, site_url: str) -> str:
    ics = f"{site_url}/{slug}/calendar-{year}.ics"
    wc = webcal_url(ics)
    body = (
        f'<section class="hero"><p class="eyebrow">Android setup · {short} {year}</p>'
        f"<h1>Subscribe to {short} market holidays</h1>"
        '<p class="lede">We are copying the calendar link to your clipboard. Paste it into '
        "Google Calendar (Add by URL) or a subscription app — it updates automatically.</p></section>"
        '<div class="callout" data-go-status>Preparing your subscription link…</div>'
        '<div class="sub-actions">'
        '<a class="btn" href="https://calendar.google.com/calendar/r/settings/addbyurl" '
        'target="_blank" rel="noopener">Open Google Calendar → Add by URL</a>'
        f'<button type="button" class="btn ghost" data-copy="{ics}">Copy link</button>'
        f'<a class="btn ghost" href="{ics}">Download .ics</a>'
        f'<a class="btn ghost" href="/{slug}/{year}/index.html">Back to {short} {year}</a>'
        "</div>"
        '<section class="sec"><h2>2 steps</h2><div class="sub-help">'
        "<details open><summary>Google Calendar (Android browser or desktop)</summary><ol>"
        "<li>The .ics link is already copied (if not, tap <strong>Copy link</strong>).</li>"
        "<li>Open Google Calendar → Settings → <strong>Add calendar → From URL</strong> → "
        "paste the link → Add calendar.</li></ol></details>"
        "<details><summary>ICSx5 (Android app — syncs into the system calendar)</summary><ol>"
        "<li>Install ICSx5 → Add calendar → paste the copied link.</li></ol></details>"
        "<details><summary>iPhone / Mac</summary><ol>"
        f'<li><a href="{wc}">Subscribe with Apple Calendar</a> (webcal link, auto-updates).</li>'
        "</ol></details></div></section>"
        f'<p class="muted">Calendar link: <code>{ics}</code></p>'
        "<script>(function(){var t=" + json.dumps(ics) + ";"
        "function ok(){var s=document.querySelector('[data-go-status]');"
        "if(s){s.textContent='✓ Link copied — now paste it into Google Calendar (Add calendar → From URL).';}}"
        "function copy(){if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(ok,ok);}"
        "else{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();"
        "try{document.execCommand('copy');}catch(e){}a.parentNode.removeChild(a);ok();}}"
        "copy();document.querySelectorAll('[data-copy]').forEach(function(b){b.addEventListener('click',copy);});"
        "})();</script>"
    )
    return page(f"Subscribe to {short} {year} market holidays — Android one-tap setup",
                f"Guided Android setup to subscribe to {short} market holidays via Google Calendar From URL or ICSx5.",
                f"{site_url}/go/{slug}/", body, base="../../", robots="noindex,follow")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-url", default="https://exchangekit.pages.dev")
    args = parser.parse_args()
    site_url = args.site_url.rstrip("/")

    rows = json.loads((HK / "data" / "holidays.json").read_text(encoding="utf-8"))["holidays"]
    names_by_date: dict[tuple, str] = {}
    for row in rows:
        try:
            d = date.fromisoformat(row["date"])
        except (KeyError, ValueError):
            continue
        names_by_date.setdefault((row["country"], d), str(row["name"]))

    out = ROOT / "dist"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "site.css").write_text(_css_bundle(), encoding="utf-8")
    urls: list[str] = []
    current_year = date.today().year if date.today().year in YEARS else max(YEARS)

    data: dict[tuple[str, int], dict] = {}
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        try:
            cal = mcal.get_calendar(code)
        except Exception as exc:  # noqa: BLE001
            print("skip", code, exc)
            continue
        for year in YEARS:
            try:
                sch = cal.schedule(start_date=f"{year}-01-01", end_date=f"{year}-12-31")
            except Exception:  # noqa: BLE001
                continue
            sessions = {d_.date() for d_ in sch.index}
            closures = []
            monthly = [0] * 13
            d_ = date(year, 1, 1)
            end = date(year, 12, 31)
            while d_ <= end:
                if d_.weekday() < 5:
                    if d_ in sessions:
                        monthly[d_.month] += 1
                    else:
                        closures.append({
                            "date": d_.isoformat(),
                            "weekday": d_.strftime("%A"),
                            "name": names_by_date.get((cc, d_), "Market holiday"),
                        })
                d_ += timedelta(days=1)
            data[(code, year)] = {
                "code": code, "name": name, "short": short, "cc": cc, "city": city,
                "tz": tz, "open": open_t, "close": close_t,
                "tradingDays": len(sessions), "monthly": monthly, "closures": closures,
            }

    if not data:
        print("no exchange data computed")
        return 1

    def slug_for(short: str) -> str:
        base = slugify(short.lower())
        return base

    qr_dir = out / "assets" / "qr"
    qr_dir.mkdir(parents=True, exist_ok=True)
    if qrcode is not None:
        for code, name, short, cc, city, tz, _o, _c in EXCHANGES:
            if (code, YEARS[0]) not in data:
                continue
            try:
                qrcode.make(f"{site_url}/{slug_for(short)}/", box_size=4, border=1).save(
                    qr_dir / f"{slug_for(short)}.png"
                )
            except Exception:  # noqa: BLE001
                continue

    # data for the live market clock (client-side countdown)
    ex_markets = [
        {"code": code, "short": short, "city": city, "tz": tz,
         "open": open_t, "close": close_t, "slug": slug_for(short)}
        for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES
        if (code, min(YEARS)) in data
    ]
    ex_closures = {}
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        per_year = {
            str(y): [c["date"] for c in data[(code, y)]["closures"]]
            for y in (current_year, current_year + 1) if (code, y) in data
        }
        if per_year:
            ex_closures[code] = per_year
    ex_markets_json = json.dumps(ex_markets, ensure_ascii=False)
    ex_closures_json = json.dumps(ex_closures, ensure_ascii=False)

    # homepage
    cards = []
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        entry = data.get((code, min(YEARS)))
        if not entry:
            continue
        current = data.get((code, current_year)) or entry
        nxt = [c for c in current["closures"] if c["date"] >= date.today().isoformat()]
        if nxt:
            next_txt = "next " + date.fromisoformat(nxt[0]["date"]).strftime("%d %b")
        else:
            next_txt = "no more this year"
        _mon = [current["monthly"][i] if i < len(current["monthly"]) else 0 for i in range(1, 13)]
        _mx = max(_mon) or 1
        spark = "".join(f'<i style="height:{max(6, v / _mx * 100):.0f}%"></i>' for v in _mon)
        cards.append(
            f'<a class="card" href="{slug_for(short)}/index.html" data-code="{code}" data-tz="{tz}" data-open="{open_t}" data-close="{close_t}" data-live-market>'
            f'<div class="flag">{flag_emoji(cc)}</div><h3>{short}</h3>'
            f'<p>{current["tradingDays"]} trading days in {current_year}</p>'
            f'<span class="spark" aria-hidden="true">{spark}</span>'
            f'<p class="card-note">{len(current["closures"])} market holidays · {next_txt}</p>'
            f'<p class="status"><span class="dot"></span><span data-live-label>{city}</span></p></a>'
        )
    map_markers = []
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        if (code, YEARS[0]) not in data:
            continue
        lat, lon = COORDS.get(code, (0.0, 0.0))
        map_markers.append(
            f'<g class="ex-dot" data-lat="{lat}" data-lon="{lon}" data-short="{short}" '
            f'data-city="{city}" data-tz="{tz}" data-open="{open_t}" data-close="{close_t}" '
            f'data-href="{slug_for(short)}/index.html">'
            '<circle class="ring" r="11"></circle><circle class="core" r="4.4"></circle></g>'
        )
    map_section = (
        '<section class="sec" id="map"><h2 data-i18n="map.h2">Market map — live open / closed</h2>'
        '<p class="sub" data-i18n="map.sub">Every exchange on one interactive map. Green pulsing dots are markets open right now; '
        "we locate you automatically. Drag to pan, scroll to zoom.</p>"
        '<span class="map-badge" id="map-open-count">loading…</span></p>'
        '<div class="map-wrap">'
        '<svg id="exmap" viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid meet" role="img" '
        'aria-label="World map of stock exchanges">'
        '<g id="map-g"><path class="map-land" d="' + MAP_PATH + '"></path>'
        + "".join(map_markers)
        + '</g></svg>'
        '<div class="map-tip" id="map-tip"></div>'
        '<div class="map-controls">'
        '<button type="button" data-map-zoom="in" aria-label="Zoom in">+</button>'
        '<button type="button" data-map-zoom="out" aria-label="Zoom out">−</button>'
        '<button type="button" data-map-reset aria-label="Reset view">⟲</button>'
        '<button type="button" data-map-locate aria-label="Locate me">◎</button>'
        "</div>"
        '<div class="map-legend"><span><i class="lg open"></i><span data-i18n="map.open">Open now</span></span>'
        '<span><i class="lg closed"></i><span data-i18n="map.closed">Closed</span></span>'
        '<span><i class="lg you"></i><span data-i18n="map.you">You</span></span></div>'
        "</div></section>"
    )

    faq = [
        ("What counts as a market holiday?",
         "A weekday on which the exchange is closed. Weekends are always non-trading days and are not listed."),
        ("Where does the data come from?",
         "Holiday rules follow the official published calendar of each exchange; holiday names come from open public-holiday datasets."),
        ("Can I subscribe to an exchange calendar?",
         "Yes — every exchange page has .ics links for Google Calendar, Apple Calendar and Outlook."),
    ]
    faq_html = "".join(f"<dt>{q}</dt><dd>{a}</dd>" for q, a in faq)
    clock_section = (
        '<section class="sec" id="clock">'
        '<div class="clock-head"><div>'
        '<h2 data-i18n="clock.h2">Market clock — live open / closed</h2>'
        '<p class="sub" data-i18n="clock.sub">Live countdown to every open and close. Green cards are trading right now.</p>'
        '</div><span class="clock-badge" id="ex-clock-badge"><span class="dot"></span>loading…</span></div>'
        '<div class="clock-wrap">'
        '<div id="ex-clock"><div class="mk-grid" id="ex-clock-grid"></div>'
        '<button type="button" class="btn ghost" id="ex-clock-more" style="margin-top:12px"></button></div>'
        '<aside class="mk-side">'
        '<div class="mk-panel"><h3><span data-i18n="clock.closing">Closing soon</span></h3>'
        '<ul class="mk-list" id="ex-closing"></ul></div>'
        '<div class="mk-panel"><h3><span data-i18n="clock.opening">Opening soon</span></h3>'
        '<ul class="mk-list" id="ex-opening"></ul></div>'
        "</aside></div>"
        '<p class="clock-note" data-i18n="clock.note">Times are each market’s local time. Exchange holidays are skipped automatically.</p>'
        "</section>"
    )
    body = (
        '<section class="hero"><p class="eyebrow" data-i18n="hero.eyebrow">Trading days · market holidays · 2025–2028</p>'
        '<h1 data-i18n="hero.h1">Market holidays and trading days.</h1>'
        '<p class="lede" data-i18n="hero.lede">Every closure day for the world\'s major stock exchanges, with trading-day counts, '
        "monthly breakdowns, one-click .ics subscriptions and a free JSON API.</p></section>"
        + map_section
        + clock_section
        + '<section class="sec" id="closures"><h2 data-i18n="ex.h2">Exchanges</h2>'
        '<p class="sub" data-i18n="ex.sub">Trading days and the next closure for '
        + str(current_year) + ".</p>"
        '<div class="grid">' + "".join(cards) + "</div></section>"
        '<span hidden></span>'
        '<section class="sec" id="why"><h2>Why this matters</h2>'
        "<p>Settlement, payroll, FX valuation, fund NAV, trading windows and deadline planning all depend on the "
        "exchange calendar — not just public holidays. ExchangeKit gives you the exact list per exchange and year.</p>"
        '<div class="callout">Cross-check with your broker or exchange notice before acting on time-sensitive trades.</div>'
        "</section>"
        '<section class="sec"><h2>FAQ</h2><dl class="faq">' + faq_html + "</dl></section>"
    )
    (out / "index.html").write_text(
        page("Market Holidays & Trading Days — ExchangeKit",
             "Trading days and market holidays for NYSE, NASDAQ, SSE, HKEX, TSE, LSE, Xetra and 25 more exchanges. Free .ics and JSON API.",
             site_url + "/", body + support_strip("", "ExchangeKit"),
             script=("<script>window.EX_FOCUS_YEAR=" + str(current_year) + ";</script>"
                     "<script>window.EX_MARKETS=" + ex_markets_json + ";window.EX_CLOSURES=" + ex_closures_json + ";</script>"
                     "<script>" + MAP_JS + "</script><script>" + CLOCK_JS + "</script>"),
             alternates=hreflang_links(site_url)),
        encoding="utf-8",
    )
    urls.append("")
    for _lang in LANG_CODES:
        _ld = out / _lang
        _ld.mkdir(parents=True, exist_ok=True)
        (_ld / "index.html").write_text(page_lang_home(_lang, site_url), encoding="utf-8")
        urls.append(_lang + "/")

    # exchange pages + year pages + ics + api
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        entry = data.get((code, YEARS[0]))
        if not entry:
            continue
        slug = slug_for(short)
        exdir = out / slug
        exdir.mkdir(parents=True, exist_ok=True)
        year_rows = "".join(
            f'<tr><td><a href="{y}/index.html">{y}</a></td><td>{data[(code, y)]["tradingDays"]}</td>'
            f'<td>{len(data[(code, y)]["closures"])}</td></tr>'
            for y in YEARS if (code, y) in data
        )
        status_html = (
            f'<p class="status" data-live-market data-code="{code}" data-tz="{tz}" data-open="{open_t}" data-close="{close_t}">'
            f'<span class="dot"></span><span data-live-label>{city}</span>'
            '<span class="live-count" data-live-count></span></p>'
        )
        (exdir / "index.html").write_text(
            page(f"{short} Market Holidays & Trading Days — {name}",
                 f"{short} trading days and market holidays by year (2025–2028). .ics subscription and JSON API.",
                 f"{site_url}/{slug}/",
                 f'<section class="hero"><p class="eyebrow">{cc} · {city}</p>'
                 f'<h1><span class="flag">{flag_emoji(cc)}</span> {short}</h1>'
                 f'<p class="lede">{name} — trading days and closure days by year.</p>{status_html}</section>'
                 '<section class="sec" id="holidays"><h2>By year</h2><div class="tbl-wrap"><table><thead><tr>'
                 "<th>Year</th><th>Trading days</th><th>Market holidays</th></tr></thead><tbody>"
                 + year_rows + "</tbody></table></div></section>"
                 + subscribe_block(short, slug, YEARS[1] if (code, YEARS[1]) in data else YEARS[0], site_url)
                 + f'<p><a href="../index.html">← All exchanges</a></p>',
                 base="../../", hol_href="#holidays",
                 crumbs=[("Home", "../../index.html"), ("Exchanges", "../../index.html#closures"), (short, "")],
                 script="<script>window.EX_CLOSURES=" + json.dumps({code: ex_closures.get(code, {})}, ensure_ascii=False) + ";</script>"),
            encoding="utf-8",
        )
        urls.append(f"{slug}/")
        for y in YEARS:
            if (code, y) not in data:
                continue
            d = data[(code, y)]
            ydir = exdir / str(y)
            ydir.mkdir(parents=True, exist_ok=True)
            closure_rows = "".join(
                f'<tr><td>{date.fromisoformat(c["date"]).strftime("%d %b %Y")}</td>'
                f'<td>{c["weekday"]}</td><td>{c["name"]}</td></tr>'
                for c in d["closures"]
            )
            _sibs = [
                (slug_for(_s2), _s2)
                for _c2, _n2, _s2, _cc2, *_rest in EXCHANGES
                if _cc2 == cc and _c2 != code and (_c2, y) in data
            ]
            rel_html = ""
            if _sibs:
                rel_html = (
                    "<section class=\"sec\"><h2>Other "
                    + (COUNTRY_NAMES.get(cc) or cc)
                    + " exchanges</h2><div class=\"chips\">"
                    + "".join(
                        f'<a class="chip" href="../../{_sg}/{y}/index.html">{_s} {y}</a>'
                        for _sg, _s in _sibs
                    )
                    + "</div></section>"
                )
            max_m = max(d["monthly"][1:] + [1])
            bars = "".join(
                f'<div class="bar-row"><span>{MONTHS[i-1]}</span>'
                f'<span class="bar"><i data-w="{(d["monthly"][i] / max_m * 100):.0f}%"></i></span>'
                f'<span>{d["monthly"][i]}</span></div>'
                for i in range(1, 13)
            )
            closures_n = len(d["closures"])
            weekdays_n = d["tradingDays"] + closures_n
            open_pct = d["tradingDays"] / max(weekdays_n, 1)
            donut = (
                '<section class="sec"><h2><span class="sec-h-ico">📈</span>Market open vs closed in ' + str(y) + "</h2>"
                '<div class="donut-wrap">'
                f'<svg class="vz-donut" data-donut="{open_pct:.3f}" viewBox="0 0 120 120" aria-hidden="true">'
                '<circle class="bg" cx="60" cy="60" r="50"></circle>'
                f'<circle class="fg" cx="60" cy="60" r="50" style="stroke-dasharray:314.159;--target:'
                f'{314.159 * (1 - open_pct):.1f}"></circle></svg>'
                '<div class="donut-txt">'
                f'<span class="big">{d["tradingDays"]}</span>'
                f'<span class="muted">trading days in {y} · {closures_n} market holidays</span>'
                f'<span class="muted">{open_pct * 100:.1f}% of weekdays the exchange is open</span>'
                "</div></div>"
                '<div class="vz-legend">'
                f'<span><i style="background:#34d399"></i>Open · {open_pct * 100:.1f}%</span>'
                f'<span><i style="background:#94a3b8"></i>Closed · {(1 - open_pct) * 100:.1f}%</span></div>'
                '<div class="kpi-row">'
                f'<div class="kpi"><span class="kpi-ico">📈</span><span class="kpi-b">'
                f'<span class="kpi-n">{d["tradingDays"]}</span>'
                '<span class="kpi-l">trading days</span></span></div>'
                f'<div class="kpi"><span class="kpi-ico">🚫</span><span class="kpi-b">'
                f'<span class="kpi-n">{closures_n}</span>'
                '<span class="kpi-l">market holidays</span></span></div>'
                f'<div class="kpi"><span class="kpi-ico">🗓️</span><span class="kpi-b">'
                f'<span class="kpi-n">{weekdays_n}</span>'
                '<span class="kpi-l">weekdays in the year</span></span></div>'
                "</div>"
                f'<p class="viz-note">A trading day is a weekday the exchange is open. Market holidays are '
                f"weekdays it closes — {closures_n} in {y} "
                f"({len(d['closures'])} closure dates, including weekend-adjacent ones listed below).</p>"
                "</section>"
            )
            faq = [
                (f"How many trading days does {short} have in {y}?",
                 f"{d['tradingDays']} trading days in {y}, after weekends and "
                 f"{len(d['closures'])} market holidays are removed."),
                (f"Which days is {short} closed in {y}?",
                 "The full closure list is in the table above, including holidays that fall next to a "
                 "weekend."),
                (f"Can I subscribe to the {short} holiday calendar?",
                 "Yes — the calendar.ics link on this page imports every closure date straight into Google "
                 "Calendar, Apple Calendar or Outlook."),
            ]
            (ydir / "index.html").write_text(
                page(f"{short} Market Holidays {y} — {d['tradingDays']} trading days",
                     f"{short} ({name}) market holidays and trading days in {y}: {d['tradingDays']} trading days, "
                     f"{len(d['closures'])} closure days. Full list with dates.",
                     f"{site_url}/{slug}/{y}/",
                     f'<section class="hero"><p class="eyebrow">{short} · {y}</p>'
                     f'<h1><span class="flag">{flag_emoji(cc)}</span> {short} market holidays in {y}</h1>'
                     f'<div class="chips"><span class="chip">{d["tradingDays"]} trading days</span>'
                     f'<span class="chip">{len(d["closures"])} market holidays</span></div>'
                     f'<p class="status" data-live-market data-code="{code}" data-tz="{tz}" data-open="{open_t}" data-close="{close_t}" style="margin-top:12px">'
                     '<span class="dot"></span><span data-live-label></span>'
                     '<span class="live-count" data-live-count></span></p>'
                     '<div class="cta-row" style="margin-top:20px">'
                     '<button type="button" class="btn-share-hot" data-share-open>'
                     '<span aria-hidden="true">✨</span> 生成分享卡片 · Share card</button>'
                     f'<a class="btn ghost" href="calendar.ics">Add {y} to calendar</a>'
                     "</div></section>"
                     + donut
                     + '<section class="sec"><h2><span class="sec-h-ico">📊</span>Trading days by month</h2>'
                     '<div class="bars">' + bars + "</div>"
                     + f'<p class="viz-note">Trading days per month in {y}. Shorter bars mean more market '
                     "holidays (or fewer weekdays) in that month.</p></section>"
                     '<section class="sec" id="holidays"><h2>Market holidays</h2><div class="tbl-wrap"><table><thead><tr>'
                     "<th>Date</th><th>Day</th><th>Holiday</th></tr></thead><tbody>"
                     + closure_rows + "</tbody></table></div></section>"
                     + subscribe_block(short, slug, y, site_url)
                     + rel_html
                     + '<section class="sec"><h2>Frequently asked questions</h2>' + faq_block(faq) + "</section>"
                     + f'<p><a href="../index.html">← {short} overview</a></p>',
                     base="../../../", hol_href="#holidays",
                     json_ld=faq_json_ld(faq),
                     crumbs=[("Home", "../../../index.html"), ("Exchanges", "../../../index.html#closures"),
                             (short, "../../index.html"), (str(y), "")],
                     script="<script>window.EX_CLOSURES=" + json.dumps({code: ex_closures.get(code, {})}, ensure_ascii=False) + ";</script>"
                     "<script>window.EX_SHARE="
                     + json.dumps({
                         "short": short,
                         "name": name,
                         "slug": slug,
                         "year": y,
                         "tradingDays": d["tradingDays"],
                         "closures": [
                             {"d": date.fromisoformat(c["date"]).strftime("%d %b"), "n": c["name"]}
                             for c in d["closures"]
                         ],
                         "url": f"{site_url}/{slug}/{y}/",
                         "qr": f"/assets/qr/{slug}.png",
                     }, ensure_ascii=False)
                     + ";</script><script>" + SHARE_JS + "</script>"),
                encoding="utf-8",
            )
            urls.append(f"{slug}/{y}/")
            # ICS
            ics = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:-//ExchangeKit//{short}//EN",
                   f"X-WR-CALNAME:{short} market holidays {y}", "CALSCALE:GREGORIAN"]
            for c in d["closures"]:
                dd = date.fromisoformat(c["date"])
                ics += [
                    "BEGIN:VEVENT",
                    f"UID:{slug}-{c['date']}@exchangekit",
                    f"DTSTAMP:{date.today().strftime('%Y%m%d')}T000000Z",
                    f"DTSTART;VALUE=DATE:{dd.strftime('%Y%m%d')}",
                    f"DTEND;VALUE=DATE:{(dd + timedelta(days=1)).strftime('%Y%m%d')}",
                    f"SUMMARY:{short} closed: {c['name'].replace(',', ' ')}",
                    "TRANSP:TRANSPARENT",
                    "END:VEVENT",
                ]
            ics.append("END:VCALENDAR")
            (exdir / f"calendar-{y}.ics").write_text("\r\n".join(ics) + "\r\n", encoding="utf-8")
            # API
            api_dir = out / "api" / "v1" / "exchange" / code
            api_dir.mkdir(parents=True, exist_ok=True)
            (api_dir / f"{y}.json").write_text(
                json.dumps({
                    "exchange": code, "name": name, "short": short, "country": cc,
                    "timezone": tz, "year": y, "tradingDays": d["tradingDays"],
                    "monthly": {MONTHS[i-1]: d["monthly"][i] for i in range(1, 13)},
                    "closures": d["closures"],
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # exchanges list API
    (out / "api").mkdir(exist_ok=True)
    (out / "api" / "v1").mkdir(parents=True, exist_ok=True)
    (out / "api" / "v1" / "exchanges.json").write_text(
        json.dumps([
            {"code": c, "name": n, "short": s, "country": cc, "city": city, "timezone": tz,
             "slug": slug_for(s)}
            for c, n, s, cc, city, tz, _o, _cl in EXCHANGES if (c, YEARS[0]) in data
        ], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    api_body = (
        '<section class="hero"><p class="eyebrow">API</p><h1>Exchange calendar API</h1>'
        '<p class="lede">Static JSON for every exchange and year.</p></section>'
        '<section class="sec"><h2>Endpoints</h2>'
        '<div class="card"><code>GET /api/v1/exchanges.json</code></div>'
        '<div class="card" style="margin-top:10px"><code>GET /api/v1/exchange/{CODE}/{YYYY}.json</code></div>'
        '<p class="muted" style="margin-top:10px">Example: <a href="/api/v1/exchange/XNYS/2026.json">'
        "/api/v1/exchange/XNYS/2026.json</a></p></section>"
        '<section class="sec"><h2>Notes</h2><ul>'
        "<li>Rate limit: 240 requests/minute per IP; over the limit returns HTTP 429 with "
        "<code>Retry-After</code>. Responses are cacheable for a day.</li>"
        "<li>Free under a generous fair-use policy. Commercial or high-volume use? "
        'See <a href="../support/index.html">Support</a>.</li>'
        "</ul></section>"
    )
    (out / "api" / "index.html").write_text(
        page("Exchange Calendar API — static JSON", "Free static JSON API for exchange trading days and market holidays.",
             f"{site_url}/api/", api_body, base="../", robots="noindex,follow"),
        encoding="utf-8",
    )
    if SHOW_API:
        urls.append("api/")

    # subscribe hub
    sub_rows = []
    for code, name, short, cc, city, tz, _o, _c in EXCHANGES:
        if (code, YEARS[1]) not in data:
            continue
        slug = slug_for(short)
        ics = f"{site_url}/{slug}/calendar-{YEARS[1]}.ics"
        sub_rows.append(
            f'<tr><td><a href="{slug}/index.html">{short}</a></td><td>{city}</td>'
            f'<td><a href="{webcal_url(ics)}">📱 Subscribe</a> · '
            f'<a href="{ics}">.ics</a> · '
            f'<a href="{google_cal_url(ics)}" target="_blank" rel="noopener">Google</a> · '
            f'<a href="{outlook_cal_url(ics)}" target="_blank" rel="noopener">Outlook</a></td></tr>'
        )
    sub_body = (
        '<section class="hero"><p class="eyebrow">Calendar subscriptions</p>'
        "<h1>Subscribe to exchange calendars</h1>"
        '<p class="lede">One URL per exchange, auto-updating. iPhone, iPad, Mac, Android, Google Calendar and '
        "Outlook all support URL subscriptions — no .ics file import.</p></section>"
        '<section class="sec"><h2>How it works</h2><div class="sub-help">'
        "<details open><summary>iPhone / iPad / Mac — subscribe (auto-updates)</summary><ol>"
        "<li>Tap <strong>Subscribe</strong> → Calendar opens → tap <strong>Subscribe</strong>.</li>"
        "<li>Or Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar.</li>"
        "</ol></details>"
        "<details><summary>Android — Google Calendar can't open webcal links; use one of these</summary><ol>"
        "<li>Easiest: open <a href=\"/go/\"><strong>Android one-tap setup</strong></a> — it copies the link "
        "and opens Google Calendar's “Add by URL”.</li>"
        "<li>Browser → Google Calendar → Add calendar → From URL → paste the .ics link.</li>"
        "<li>Or install <strong>ICSx5</strong> to sync the .ics subscription into the Android system calendar.</li>"
        "</ol></details>"
        "<details><summary>Outlook / Windows</summary><ol>"
        "<li>Add calendar → Subscribe from web → paste the .ics link.</li></ol></details>"
        "</div></section>"
        '<section class="sec"><h2>All exchanges</h2><div class="tbl-wrap"><table><thead><tr>'
        f"<th>Exchange</th><th>City</th><th>Subscribe ({YEARS[1]})</th></tr></thead><tbody>"
        + "".join(sub_rows) + "</tbody></table></div></section>"
    )
    (out / "subscribe").mkdir(exist_ok=True)
    (out / "subscribe" / "index.html").write_text(
        page("Subscribe to exchange calendars — one URL, auto-updating",
             "Subscribe to exchange market-holiday calendars by URL — works with iPhone, Mac, Google Calendar and Outlook.",
             f"{site_url}/subscribe/", sub_body, base="../"),
        encoding="utf-8",
    )
    urls.append("subscribe/")

    # Android one-tap setup pages (/go/{exchange}/) + hub
    go_year = YEARS[2] if YEARS[2] in {y for (_c, y) in data.keys()} else YEARS[1]
    (out / "go").mkdir(exist_ok=True)
    go_rows = []
    for code, name, short, cc, city, tz, _o, _c in EXCHANGES:
        if (code, go_year) not in data:
            continue
        slug = slug_for(short)
        gdir = out / "go" / slug
        gdir.mkdir(exist_ok=True)
        (gdir / "index.html").write_text(go_page(short, slug, go_year, site_url), encoding="utf-8")
        ics = f"{site_url}/{slug}/calendar-{go_year}.ics"
        go_rows.append(
            f'<tr><td><a href="{slug}/index.html">{short}</a></td><td>{city}</td>'
            f'<td><a href="{slug}/index.html">📱 One-tap setup</a></td>'
            f'<td><a href="{ics}">.ics</a></td></tr>'
        )
    go_body = (
        '<section class="hero"><p class="eyebrow">Android subscriptions</p>'
        "<h1>One-tap setup for Android</h1>"
        '<p class="lede">Pick an exchange: we copy the calendar link and open Google Calendar’s '
        "“Add by URL”, where you paste it once. After that the calendar updates automatically.</p></section>"
        '<section class="sec"><h2>All exchanges</h2><div class="tbl-wrap"><table><thead><tr>'
        f"<th>Exchange</th><th>City</th><th>Setup</th><th>Direct .ics</th></tr></thead><tbody>"
        + "".join(go_rows) + "</tbody></table></div></section>"
        '<div class="callout">Android has no system handler for <code>webcal://</code> links — so we copy '
        "the link and open Google Calendar for you.</div>"
    )
    (out / "go" / "index.html").write_text(
        page("Android one-tap calendar subscription setup",
             "Guided Android setup to subscribe to exchange market-holiday calendars via Google Calendar From URL or ICSx5.",
             f"{site_url}/go/", go_body, base="../", robots="noindex,follow"),
        encoding="utf-8",
    )
    for path, title, desc in [
        ("about", "About ExchangeKit", "About ExchangeKit, data sources and methodology."),
        ("privacy", "Privacy", "Privacy policy for ExchangeKit."),
    ]:
        (out / path).mkdir(exist_ok=True)
        body_p = (
            f'<section class="hero"><h1>{title.split(" — ")[0]}</h1>'
            f'<p class="lede">{desc}</p></section>'
            '<section class="sec"><p>Holiday rules follow the official published calendar of each exchange. '
            "Holiday names from open public-holiday datasets. Data for planning only — "
            "always confirm critical dates with the exchange.</p></section>"
        )
        (out / path / "index.html").write_text(
            page(title, desc, f"{site_url}/{path}/", body_p, base="../"), encoding="utf-8"
        )
        urls.append(f"{path}/")

    # ── site search index ──
    search_entries = []
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        if (code, YEARS[0]) not in data:
            continue
        slug_ = slug_for(short)
        search_entries.append({"t": f"{short} — {name}", "s": f"Trading days · {city}",
                               "u": f"/{slug_}/", "k": "exchange"})
        for y in YEARS:
            if (code, y) in data:
                d_ = data[(code, y)]
                search_entries.append({"t": f"{short} {y}", "s": f"{d_['tradingDays']} trading days · {len(d_['closures'])} closures",
                                       "u": f"/{slug_}/{y}/", "k": "year"})
    for _p, _t, _s in [
        *([("api/", "Free JSON API", "Trading days and market holidays")] if SHOW_API else []),
        ("about/", "About", "Method and data sources"),
        ("support/", "Support", "Keep the project free"),
    ]:
        search_entries.append({"t": _t, "s": _s, "u": f"/{_p}", "k": "page"})
    (out / "search-index.json").write_text(
        json.dumps(search_entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    (out / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    _og = ROOT / "assets" / "og-cover.png"
    if _og.exists():
        (out / "og-cover.png").write_bytes(_og.read_bytes())
    (out / "support").mkdir(exist_ok=True)
    (out / "support" / "index.html").write_text(page_support(site_url), encoding="utf-8")
    urls.append("support/")
    (out / "_headers").write_text(
        "/*.ics\n  Content-Type: text/calendar; charset=utf-8\n  Cache-Control: public, max-age=3600\n"
        "/api/*\n  Access-Control-Allow-Origin: *\n  Cache-Control: public, max-age=86400\n"
        "/assets/support/*\n  Cache-Control: public, max-age=604800\n"
        "/search-index.json\n  Cache-Control: public, max-age=3600\n"
        "/assets/site.css\n  Cache-Control: public, max-age=31536000, immutable\n",
        encoding="utf-8",
    )
    support_dir = ROOT / "assets" / "support"
    if support_dir.exists():
        (out / "assets" / "support").mkdir(parents=True, exist_ok=True)
        for p in support_dir.glob("*.png"):
            (out / "assets" / "support" / p.name).write_bytes(p.read_bytes())
    _404 = (
        '<section class="hero"><p class="eyebrow">404</p>'
        "<h1>This market is closed — permanently.</h1>"
        '<p class="lede">The page you asked for does not exist. Search an exchange (⌘K), or start from '
        "the live market clock.</p>"
        '<div class="cta-row"><a class="btn" href="/index.html#clock">Market clock</a>'
        '<a class="btn ghost" href="/index.html#closures">All exchanges</a>'
        '<a class="btn ghost" href="/api/index.html">JSON API</a></div></section>'
    )
    (out / "404.html").write_text(
        page("Page not found — " + SITE_NAME,
             "This page does not exist. Browse exchanges, the live market clock, or the JSON API.",
             site_url + "/404.html", _404, base="/", robots="noindex,follow"),
        encoding="utf-8",
    )

    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    today = date.today().isoformat()
    for path in urls:
        sitemap.append(f"<url><loc>{site_url}/{path}</loc><lastmod>{today}</lastmod></url>")
    sitemap.append("</urlset>")
    (out / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (out / f"9c1f7a2b4d6e8f0a1b3c5d7e9f2a4b6c.txt").write_text("9c1f7a2b4d6e8f0a1b3c5d7e9f2a4b6c", encoding="utf-8")

    print(f"Built {len(urls)} pages / {len(EXCHANGES)} exchanges -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas_market_calendars as mcal

ROOT = Path(__file__).resolve().parent
HK = ROOT.parent / "holiday-kit"
sys.path.insert(0, str(HK / "scripts"))
from build_site import COUNTRY_NAMES, flag_emoji, slugify  # noqa: E402

SITE_NAME = "ExchangeKit"
SITE_TAGLINE = "Trading days and market holidays for the world's exchanges."
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
  // live market status
  document.querySelectorAll('[data-live-market]').forEach(function(el){
    var tz=el.getAttribute('data-tz'), open=el.getAttribute('data-open'), close=el.getAttribute('data-close');
    if (!tz) return;
    function update(){
      try {
        var now=new Date();
        var parts=new Intl.DateTimeFormat('en-GB',{timeZone:tz,weekday:'short',hour:'2-digit',minute:'2-digit',hour12:false}).formatToParts(now);
        var map={}; parts.forEach(function(p){ map[p.type]=p.value; });
        var wd=map.weekday, hm=map.hour+':'+map.minute;
        var isWeekend=(wd==='Sat'||wd==='Sun');
        var isOpen=!isWeekend && hm>=open && hm<close;
        var dot=el.querySelector('.dot'), label=el.querySelector('[data-live-label]');
        if(dot) dot.className='dot '+(isOpen?'open':'closed');
        if(label) label.textContent=isOpen?'Market open now':'Market closed';
      } catch(e){}
    }
    update(); setInterval(update, 30000);
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


def page(title: str, desc: str, canonical: str, body: str, base: str = "", script: str = "") -> str:
    nav = (
        '<header class="site-head"><div class="wrap head-inner">'
        f'<a class="brand" href="{base}index.html"><span class="brand-mark">◈</span>{SITE_NAME}</a>'
        f'<nav><a href="{base}index.html">Exchanges</a>'
        f'<a href="{base}index.html#closures">Holidays</a>'
        f'<a href="{base}api/index.html">API</a>'
        f'<a href="{base}about/index.html">About</a></nav>'
        "</div></header>"
    )
    foot = (
        '<footer class="site-foot"><div class="wrap">'
        f'<p><strong>{SITE_NAME}</strong> — {SITE_TAGLINE}</p>'
        '<p>Schedules derived from pandas-market-calendars exchange rules; holiday names joined from open holiday data. '
        "For planning only — confirm with the exchange for critical dates.</p>"
        f'<p><a href="{base}privacy/index.html">Privacy</a> · <a href="{base}about/index.html">About</a> · '
        f'<a href="https://workdaykit.pages.dev">Business days calculator</a> · '
        f'<a href="https://holidaykit.pages.dev">Holiday calendars</a></p>'
        "</div></footer>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title>"
        f'<meta name="description" content="{desc}">'
        f'<link rel="canonical" href="{canonical}">'
        '<meta name="robots" content="index,follow">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f"<style>{CSS}</style></head><body>{nav}"
        f'<main class="wrap">{body}</main>{foot}'
        f"<script>{MOTION_JS}</script>{script}</body></html>"
    )


FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#0f1115"/>'
    '<path d="M14 46V30M26 46V22M38 46V34M50 46V18" stroke="#faf9f6" stroke-width="4" stroke-linecap="round"/>'
    '<circle cx="50" cy="18" r="4" fill="#b5731a"/></svg>'
)


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
        '<a class="btn ghost" href="https://calendar.google.com/calendar/r/settings/addbyurl" '
        'target="_blank" rel="noopener">Android — Add by URL</a>'
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
    out.mkdir(parents=True)
    urls: list[str] = []
    current_year = date.today().year

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

    # homepage
    cards = []
    for code, name, short, cc, city, tz, open_t, close_t in EXCHANGES:
        entry = data.get((code, min(YEARS)))
        if not entry:
            continue
        current = data.get((code, current_year)) or entry
        nxt = [c for c in current["closures"] if c["date"] >= date.today().isoformat()]
        next_txt = (f'next closure {nxt[0]["date"]}' if nxt else "no more closures this year")
        cards.append(
            f'<a class="card" href="{slug_for(short)}/index.html" data-tz="{tz}" data-open="{open_t}" data-close="{close_t}" data-live-market>'
            f'<div class="flag">{flag_emoji(cc)}</div><h3>{short}</h3>'
            f'<p>{current["tradingDays"]} trading days in {current_year}</p>'
            f'<p class="status"><span class="dot"></span><span data-live-label>{city}</span></p></a>'
        )
    faq = [
        ("What counts as a market holiday?",
         "A weekday on which the exchange is closed. Weekends are always non-trading days and are not listed."),
        ("Where does the data come from?",
         "Exchange holiday rules are computed with pandas-market-calendars; names are joined from open public-holiday datasets."),
        ("Can I subscribe to an exchange calendar?",
         "Yes — every exchange page has .ics links for Google Calendar, Apple Calendar and Outlook."),
    ]
    faq_html = "".join(f"<dt>{q}</dt><dd>{a}</dd>" for q, a in faq)
    body = (
        '<section class="hero"><p class="eyebrow">Trading days · market holidays · 2025–2028</p>'
        "<h1>Market holidays and trading days.</h1>"
        '<p class="lede">Every closure day for the world\'s major stock exchanges, with trading-day counts, '
        "monthly breakdowns, one-click .ics subscriptions and a free JSON API.</p></section>"
        '<section class="sec"><h2>Exchanges</h2>'
        '<p class="sub">Trading days and the next closure for ' + str(current_year) + '.</p>'
        '<div class="grid">' + "".join(cards) + "</div></section>"
        '<section class="ad">[Ad slot]</section>'
        '<section class="sec" id="closures"><h2>Why this matters</h2>'
        "<p>Settlement, payroll, FX valuation, fund NAV, trading windows and deadline planning all depend on the "
        "exchange calendar — not just public holidays. ExchangeKit gives you the exact list per exchange and year.</p>"
        '<div class="callout">Cross-check with your broker or exchange notice before acting on time-sensitive trades.</div>'
        "</section>"
        '<section class="sec"><h2>FAQ</h2><dl class="faq">' + faq_html + "</dl></section>"
    )
    (out / "index.html").write_text(
        page("Market Holidays & Trading Days — ExchangeKit",
             "Trading days and market holidays for NYSE, NASDAQ, SSE, HKEX, TSE, LSE, Xetra and 25 more exchanges. Free .ics and JSON API.",
             site_url + "/", body),
        encoding="utf-8",
    )
    urls.append("")

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
            f'<p class="status" data-live-market data-tz="{tz}" data-open="{open_t}" data-close="{close_t}">'
            f'<span class="dot"></span><span data-live-label>{city}</span></p>'
        )
        (exdir / "index.html").write_text(
            page(f"{short} Market Holidays & Trading Days — {name}",
                 f"{short} trading days and market holidays by year (2025–2028). .ics subscription and JSON API.",
                 f"{site_url}/{slug}/",
                 f'<section class="hero"><p class="eyebrow">{cc} · {city}</p>'
                 f'<h1><span class="flag">{flag_emoji(cc)}</span> {short}</h1>'
                 f'<p class="lede">{name} — trading days and closure days by year.</p>{status_html}</section>'
                 '<section class="sec"><h2>By year</h2><div class="tbl-wrap"><table><thead><tr>'
                 "<th>Year</th><th>Trading days</th><th>Market holidays</th></tr></thead><tbody>"
                 + year_rows + "</tbody></table></div></section>"
                 + subscribe_block(short, slug, YEARS[1] if (code, YEARS[1]) in data else YEARS[0], site_url)
                 + f'<p><a href="../index.html">← All exchanges</a></p>',
                 base="../../"),
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
            max_m = max(d["monthly"][1:] + [1])
            bars = "".join(
                f'<div class="bar-row"><span>{MONTHS[i-1]}</span>'
                f'<span class="bar"><i data-w="{(d["monthly"][i] / max_m * 100):.0f}%"></i></span>'
                f'<span>{d["monthly"][i]}</span></div>'
                for i in range(1, 13)
            )
            (ydir / "index.html").write_text(
                page(f"{short} Market Holidays {y} — {d['tradingDays']} trading days",
                     f"{short} ({name}) market holidays and trading days in {y}: {d['tradingDays']} trading days, "
                     f"{len(d['closures'])} closure days. Full list with dates.",
                     f"{site_url}/{slug}/{y}/",
                     f'<section class="hero"><p class="eyebrow">{short} · {y}</p>'
                     f'<h1><span class="flag">{flag_emoji(cc)}</span> {short} market holidays in {y}</h1>'
                     f'<div class="chips"><span class="chip">{d["tradingDays"]} trading days</span>'
                     f'<span class="chip">{len(d["closures"])} market holidays</span></div></section>'
                     '<section class="sec"><h2>Trading days by month</h2><div class="bars">' + bars + "</div></section>"
                     '<section class="sec"><h2>Market holidays</h2><div class="tbl-wrap"><table><thead><tr>'
                     "<th>Date</th><th>Day</th><th>Holiday</th></tr></thead><tbody>"
                     + closure_rows + "</tbody></table></div></section>"
                     + subscribe_block(short, slug, y, site_url)
                     + f'<p><a href="../index.html">← {short} overview</a></p>',
                     base="../../../"),
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
    )
    (out / "api" / "index.html").write_text(
        page("Exchange Calendar API — static JSON", "Free static JSON API for exchange trading days and market holidays.",
             f"{site_url}/api/", api_body, base="../"),
        encoding="utf-8",
    )
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
        "<details><summary>Android (Google Calendar)</summary><ol>"
        "<li>Other calendars → “+” → From URL → paste the .ics link.</li></ol></details>"
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
    for path, title, desc in [
        ("about", "About ExchangeKit", "About ExchangeKit, data sources and methodology."),
        ("privacy", "Privacy", "Privacy policy for ExchangeKit."),
    ]:
        (out / path).mkdir(exist_ok=True)
        body_p = (
            f'<section class="hero"><h1>{title.split(" — ")[0]}</h1>'
            f'<p class="lede">{desc}</p></section>'
            '<section class="sec"><p>Exchange holiday rules from pandas-market-calendars. '
            "Holiday names from open public-holiday datasets. Data for planning only — "
            "always confirm critical dates with the exchange.</p></section>"
        )
        (out / path / "index.html").write_text(
            page(title, desc, f"{site_url}/{path}/", body_p, base="../"), encoding="utf-8"
        )
        urls.append(f"{path}/")

    (out / "favicon.svg").write_text(FAVICON, encoding="utf-8")
    (out / "_headers").write_text(
        "/*.ics\n  Content-Type: text/calendar; charset=utf-8\n  Cache-Control: public, max-age=3600\n",
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

    print(f"Built {len(urls)} pages / {len(EXCHANGES)} exchanges -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

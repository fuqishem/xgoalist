#!/usr/bin/env python3
"""Günlük kupon araştırması için veri toplama aracı.

Kullanım (repo kökünden):
  python3 -I tools/veri.py futbol 2026-11-23            # tüm maçlar + 1X2 oranları + FotMob id (TR saati)
  python3 -I tools/veri.py mac <fotmob_id>              # kadro, sakat/cezalı, hava, form, H2H, tablo, xG, içgörüler
  python3 -I tools/veri.py lig <fotmob_lig_id>          # lig tablosu (genel/ev/deplasman) + xG tablosu
  python3 -I tools/veri.py ou 2026-11-23                # 2.5 Alt/Üst + Asya handikap oranları (football-data.co.uk, ~21 lig)
  python3 -I tools/veri.py basket 2026-11-23            # tüm basket ligleri oranları + NBA/NCAA spread, total, ML, kayıtlar, sakatlar
  python3 -I tools/veri.py sonuc 2026-11-22             # o günün skorları (kupon kontrolü için)

Kaynaklar: betexplorer.com, fotmob.com, football-data.co.uk, ESPN public API.
Bot korumalı (403) siteler atlatılmaz.
"""
import csv, datetime as dt, gzip, html, io, json, re, subprocess, sys, unicodedata

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
TR = dt.timezone(dt.timedelta(hours=3))


def get(url):
    r = subprocess.run(["curl", "-sL", "--compressed", "-m", "40", "-A", UA, url], capture_output=True)
    b = r.stdout
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b.decode("utf-8", "ignore")


def getj(url):
    try:
        return json.loads(get(url))
    except Exception:
        return None


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|cf|sc|ac|afc|fk|sk|if|club|cd|ud|sd|calcio|w|women|u\d+)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def similar(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a in b or b in a or a[:5] == b[:5]


# ---------------------------------------------------------------- futbol
def betexplorer_day(d):
    t = get(f"https://www.betexplorer.com/football/next/?year={d.year}&month={d.month}&day={d.day}")
    out = []
    for blk in re.split(r'<ul class="leagues-list"', t)[1:]:
        lg = re.search(r'leaguesNames">([^<]+)', blk)
        lg = lg.group(1).strip() if lg else "?"
        for m in re.split(r'<ul class="table-main__matchInfo"', blk)[1:]:
            mdt = re.search(r'data-dt="(\d+),(\d+),(\d+),(\d+),(\d+)"', m)
            names = re.findall(r'table-main__truncate ">([^<]+)</p>', m)
            odds = re.findall(r'data-odd="([\d.]+)"', m)
            if not mdt or len(names) < 2:
                continue
            D, M, Y, h, mi = map(int, mdt.groups())
            # betexplorer saati CET (UTC+1, kış) -> UTC
            utc = dt.datetime(Y, M, D, h, mi, tzinfo=dt.timezone(dt.timedelta(hours=1))).astimezone(dt.timezone.utc)
            out.append(dict(utc=utc, lig=lg, ev=html.unescape(names[0]), dep=html.unescape(names[1]),
                            o1=odds[0] if len(odds) > 2 else "", ox=odds[1] if len(odds) > 2 else "",
                            o2=odds[2] if len(odds) > 2 else ""))
    return out


def fotmob_day(d):
    j = getj(f"https://www.fotmob.com/api/data/matches?date={d:%Y%m%d}") or {}
    out = []
    for lg in j.get("leagues", []):
        for m in lg.get("matches", []):
            try:
                utc = dt.datetime.fromisoformat(m["status"]["utcTime"].replace("Z", "+00:00"))
            except Exception:
                continue
            out.append(dict(utc=utc, lig=f'{lg.get("ccode","")} {lg.get("name","")}', lig_id=lg.get("primaryId", lg.get("id")),
                            ev=m["home"]["name"], dep=m["away"]["name"], id=m["id"],
                            bitti=m["status"].get("finished"), iptal=m["status"].get("cancelled")))
    return out


def cmd_futbol(day):
    d = dt.date.fromisoformat(day)
    days = [d - dt.timedelta(days=1), d, d + dt.timedelta(days=1)]
    start = dt.datetime(d.year, d.month, d.day, tzinfo=TR)
    end = start + dt.timedelta(days=1, hours=8)  # TR gecesi/sabaha karşı Amerika maçları dahil
    bx = [x for dd in days for x in betexplorer_day(dd) if start <= x["utc"] < end]
    fm = [x for dd in days for x in fotmob_day(dd) if start <= x["utc"] < end]
    used = set()
    rows = []
    for b in bx:
        hit = next((f for f in fm if f["id"] not in used and abs((f["utc"] - b["utc"]).total_seconds()) <= 3 * 3600
                    and (similar(f["ev"], b["ev"]) or similar(f["dep"], b["dep"]))), None)
        if hit:
            used.add(hit["id"])
        rows.append(dict(b, id=hit["id"] if hit else "", lig_id=hit["lig_id"] if hit else ""))
    for f in fm:
        if f["id"] not in used and not f["iptal"]:
            rows.append(dict(f, o1="", ox="", o2=""))
    rows.sort(key=lambda r: r["utc"])
    w = csv.writer(sys.stdout)
    w.writerow(["tr_saat", "lig", "ev", "deplasman", "1", "X", "2", "fotmob_id", "fotmob_lig_id"])
    for r in rows:
        w.writerow([r["utc"].astimezone(TR).strftime("%d.%m %H:%M"), r["lig"], r["ev"], r["dep"], r["o1"], r["ox"], r["o2"], r["id"], r.get("lig_id", "")])
    ligs = {r["lig"] for r in rows}
    print(f"# {len(rows)} maç, {len(ligs)} lig ({sum(1 for r in rows if r['o1'])} maçta oran var)", file=sys.stderr)


# ---------------------------------------------------------------- mac
def cmd_mac(mid):
    j = getj(f"https://www.fotmob.com/api/data/matchDetails?matchId={mid}")
    if not j:
        print("FotMob verisi alınamadı"); return
    c = j.get("content", {})
    mf = c.get("matchFacts", {}) or {}
    ib = mf.get("infoBox", {}) or {}
    g = j.get("general", {})
    print(f"## {g.get('homeTeam',{}).get('name')} - {g.get('awayTeam',{}).get('name')}  ({g.get('leagueName')} / hafta {g.get('leagueRoundName')})")
    t = (ib.get("Match Date") or {}).get("utcTime")
    if t:
        print("Saat (TR):", dt.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(TR).strftime("%d.%m %H:%M"))
    st = ib.get("Stadium") or {}
    print("Stat:", st.get("name"), st.get("city"), "| zemin:", st.get("surface"))
    ref = ib.get("Referee") or {}
    if ref:
        print("Hakem:", ref.get("text"))
    w = c.get("weather") or {}
    if w:
        print(f"Hava: {w.get('description')}, {w.get('temperature')}°C, rüzgar {w.get('windSpeed')} m/s, yağış ihtimali %{w.get('precipChance')}, yağış {w.get('precipitation')} mm, kar {w.get('snow')}")
    lu = c.get("lineup") or {}
    print("Kadro tipi:", lu.get("lineupType"), "(predicted = muhtemel, standard = resmi)")
    for side in ("homeTeam", "awayTeam"):
        tm = lu.get(side) or {}
        if not tm:
            continue
        print(f"- {tm.get('name')} diziliş {tm.get('formation')}")
        st11 = [p.get("name") for p in tm.get("starters", [])]
        if st11:
            print("  İlk 11:", ", ".join(st11))
        un = [f"{u.get('name')} ({(u.get('unavailability') or {}).get('type')}"
              f"{', dönüş: ' + str((u.get('unavailability') or {}).get('expectedReturn')) if (u.get('unavailability') or {}).get('expectedReturn') else ''})"
              for u in tm.get("unavailable", [])]
        print("  Eksikler:", ", ".join(un) if un else "yok/bilinmiyor")
    tf = mf.get("teamForm") or []
    for i, side in enumerate(tf[:2]):
        s = " ".join(f"{x.get('resultString')}({x.get('score')})" for x in side)
        print(f"Form {'ev' if i == 0 else 'dep'} (son maçlar): {s}")
    h2h = c.get("h2h") or {}
    if h2h.get("summary"):
        a, b, cc = h2h["summary"]
        print(f"H2H özet: ev {a} galibiyet / {b} beraberlik / dep {cc} galibiyet")
        done = [m for m in h2h.get("matches", []) if (m.get("status") or {}).get("finished")][:6]
        for m in done:
            print(f"  {m['time']['utcTime'][:10]} {m['home']['name']} {m.get('status',{}).get('scoreStr','')} {m['away']['name']}")
    for ins in (mf.get("insights") or [])[:12]:
        print("İçgörü:", ins.get("text"))
    tb = c.get("table") or {}
    if tb.get("leagueId"):
        print(f"(Lig tablosu ve xG için: veri.py lig {tb.get('parentLeagueId') or tb['leagueId']})  takım id'leri: {tb.get('teams')}")


# ---------------------------------------------------------------- lig
def cmd_lig(lid):
    j = getj(f"https://www.fotmob.com/api/data/leagues?id={lid}") or {}
    for tbl in j.get("table", []):
        data = tbl.get("data", {})
        subs = data.get("tables") or [data]
        for sub in subs:
            t = sub.get("table", {})
            print(f"## {data.get('leagueName', '')} {sub.get('leagueName', '')}")
            home = {r["id"]: r for r in t.get("home", [])}
            away = {r["id"]: r for r in t.get("away", [])}
            xg = {r["id"]: r for r in t.get("xg", [])}
            print("sıra takım O G B M averaj P | ev G-B-M gol | dep G-B-M gol | xG xGA xPuan")
            for r in t.get("all", []):
                h, a, x = home.get(r["id"], {}), away.get(r["id"], {}), xg.get(r["id"], {})
                xs = f"{x.get('xg', 0):.1f} {x.get('xgConceded', 0):.1f} {x.get('xPoints', 0):.1f}" if x else "-"
                print(f"{r.get('idx')}. {r['name']} {r.get('played')} {r.get('wins')} {r.get('draws')} {r.get('losses')} {r.get('scoresStr')} {r.get('pts')} | "
                      f"{h.get('wins','-')}-{h.get('draws','-')}-{h.get('losses','-')} {h.get('scoresStr','')} | "
                      f"{a.get('wins','-')}-{a.get('draws','-')}-{a.get('losses','-')} {a.get('scoresStr','')} | {xs}")


# ---------------------------------------------------------------- ou
def cmd_ou(day):
    d = dt.date.fromisoformat(day)
    rows = list(csv.DictReader(io.StringIO(get("https://www.football-data.co.uk/fixtures.csv").lstrip("﻿"))))
    w = csv.writer(sys.stdout)
    w.writerow(["lig", "tarih", "saat(UK)", "ev", "dep", "Ort1", "OrtX", "Ort2", "Üst2.5", "Alt2.5", "AH", "AH_ev", "AH_dep"])
    for r in rows:
        try:
            rd = dt.datetime.strptime(r["Date"], "%d/%m/%Y").date()
        except Exception:
            continue
        if rd in (d, d + dt.timedelta(days=1)):
            w.writerow([r["Div"], r["Date"], r.get("Time"), r["HomeTeam"], r["AwayTeam"], r.get("AvgH"), r.get("AvgD"), r.get("AvgA"),
                        r.get("Avg>2.5"), r.get("Avg<2.5"), r.get("AHh"), r.get("AvgAHH"), r.get("AvgAHA")])


# ---------------------------------------------------------------- basket
def betexplorer_basket(d):
    t = get(f"https://www.betexplorer.com/basketball/next/?year={d.year}&month={d.month}&day={d.day}")
    out = []
    for blk in re.split(r"<tbody", t)[1:]:
        lg = re.search(r'class="table-main__tournament">(.*?)</a>', blk, re.S)
        lg = re.sub(r"<[^>]+>", "", lg.group(1)).strip() if lg else "?"
        for tr in re.findall(r'<tr data-fro[^>]*data-dt="([^"]+)"[^>]*>(.*?)</tr>', blk, re.S):
            D, M, Y, h, mi = map(int, tr[0].split(","))
            if "time--fin" in tr[1]:
                continue
            names = [re.sub(r"<[^>]+>", "", x) for x in re.findall(r'teamLine--(?:home|away)">(.*?)</span>', tr[1])]
            odds = re.findall(r'data-odd="([\d.]+)"', tr[1])
            if len(names) == 2:
                utc = dt.datetime(Y, M, D, h, mi, tzinfo=dt.timezone(dt.timedelta(hours=1)))
                out.append((utc, lg, html.unescape(names[0]), html.unescape(names[1]), odds[:2]))
    return out


def cmd_basket(day):
    d = dt.date.fromisoformat(day)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=TR)
    end = start + dt.timedelta(days=1, hours=8)
    rows = sorted({r[:4]: r for dd in (d, d + dt.timedelta(days=1)) for r in betexplorer_basket(dd) if start <= r[0] < end}.values())
    print(f"## Tüm basket ligleri (betexplorer, {len(rows)} maç, {len({r[1] for r in rows})} lig) — ev/dep oranları")
    for utc, lg, h, a, o in rows:
        print(f"{utc.astimezone(TR):%d.%m %H:%M} | {lg} | {h} - {a} | {' '.join(o)}")
    for sport, name in (("nba", "NBA"), ("mens-college-basketball", "NCAA")):
        extra = "&groups=50" if sport != "nba" else ""
        j = getj(f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/scoreboard?dates={d:%Y%m%d}&limit=300{extra}") or {}
        inj = {}
        if sport == "nba":
            ij = getj("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries") or {}
            for team in ij.get("injuries", []):
                inj[team.get("displayName")] = [f"{i.get('athlete',{}).get('displayName')} ({i.get('status')})" for i in team.get("injuries", [])]
        print(f"## {name} ({len(j.get('events', []))} maç)")
        for ev in j.get("events", []):
            c = ev["competitions"][0]
            teams = {t["homeAway"]: t for t in c["competitors"]}
            hm, aw = teams.get("home", {}), teams.get("away", {})
            rec = lambda t: ", ".join(f"{r.get('name', r.get('type'))}:{r.get('summary')}" for r in t.get("records", []))
            o = (c.get("odds") or [{}])[0]
            def ml(side):
                a = (((o.get("moneyline") or {}).get(side) or {}).get("close") or {}).get("odds", "")
                try:
                    v = int(a.replace("+", ""))
                    return f"{a} (={1 + (v / 100 if v > 0 else 100 / -v):.2f})"
                except Exception:
                    return a
            tm = dt.datetime.fromisoformat(c["date"].replace("Z", "+00:00")).astimezone(TR).strftime("%d.%m %H:%M")
            print(f"{tm} TR | {aw.get('team',{}).get('displayName')} @ {hm.get('team',{}).get('displayName')} | {o.get('details','')} O/U {o.get('overUnder','')} | ML dep {ml('away')} ev {ml('home')}")
            print(f"   kayıt dep [{rec(aw)}] ev [{rec(hm)}]")
            for t in (aw, hm):
                nm = t.get("team", {}).get("displayName")
                if inj.get(nm):
                    print(f"   sakat {nm}: {'; '.join(inj[nm][:8])}")


# ---------------------------------------------------------------- sonuc
def cmd_sonuc(day):
    """Dünün kuponlarını kontrol etmek için: futbol skorları (FotMob) + NBA/NCAA skorları (ESPN)."""
    d = dt.date.fromisoformat(day)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=TR)
    end = start + dt.timedelta(days=1, hours=8)
    for dd in (d - dt.timedelta(days=1), d, d + dt.timedelta(days=1)):
        j = getj(f"https://www.fotmob.com/api/data/matches?date={dd:%Y%m%d}") or {}
        for lg in j.get("leagues", []):
            for m in lg.get("matches", []):
                st = m.get("status", {})
                try:
                    utc = dt.datetime.fromisoformat(st["utcTime"].replace("Z", "+00:00"))
                except Exception:
                    continue
                if start <= utc < end:
                    sc = st.get("scoreStr") or ("İPTAL/ERTELENDİ" if st.get("cancelled") else "oynanmadı")
                    print(f"{utc.astimezone(TR):%d.%m %H:%M} | {lg.get('name')} | {m['home']['name']} {sc} {m['away']['name']} | id {m['id']}")
    for sport in ("nba", "mens-college-basketball"):
        for dd in (d, d + dt.timedelta(days=1)):
            j = getj(f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport}/scoreboard?dates={dd:%Y%m%d}&limit=300&groups=50") or {}
            for ev in j.get("events", []):
                c = ev["competitions"][0]
                print(f"{sport} | " + " - ".join(f"{t['team']['displayName']} {t.get('score','')}" for t in c["competitors"]) + f" | {c['status']['type']['description']}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    {"futbol": cmd_futbol, "mac": cmd_mac, "lig": cmd_lig, "ou": cmd_ou, "basket": cmd_basket, "sonuc": cmd_sonuc}[sys.argv[1]](sys.argv[2])

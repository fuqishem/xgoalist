#!/usr/bin/env python3
"""Dixon-Coles tarzı gol modeli: maç olasılıkları + piyasa ile karşılaştırma (değer/edge).

Kullanım (repo kökünden):
  python3 -I tools/model.py 2026-11-23            # o günün modelli maçları (tablo)
  python3 -I tools/model.py 2026-11-23 --csv      # CSV çıktı

Yöntem:
  - Veri: football-data.co.uk (bu sezon + geçen sezon; 22 ana lig + 16 ek lig). Bu sezon
    CSV'lerinde maç başı xG varsa gol yerine 0.5*gol + 0.5*xG kullanılır.
  - Takım hücum/savunma gücü + ev avantajı, zaman ağırlıklı (yarı ömür ~110 gün) Poisson,
    iteratif ölçekleme ile tahmin edilir; düşük skorlar için Dixon-Coles düzeltmesi (rho=-0.08).
  - Çıktı: model olasılıkları (1/X/2, 2.5 Üst, KG Var), marjı temizlenmiş piyasa olasılıkları,
    edge = model - piyasa, ve %50 model + %50 piyasa karışımı ("adil oran").
  - Pazar oranları betexplorer (1X2) ve football-data fixtures.csv (Alt/Üst) kaynaklıdır.
Uyarı: Model kaba bir referanstır; kadro/eksik/motivasyon bilgisini içermez. Büyük edge'ler
çoğu zaman modelin bilmediği bir haberden kaynaklanır, kontrol etmeden oynama.
"""
import csv, datetime as dt, io, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import veri  # noqa: E402

MAIN = {  # betexplorer lig adı -> football-data kodu
    "England: Premier League": "E0", "England: Championship": "E1", "England: League One": "E2",
    "England: League Two": "E3", "England: National League": "EC", "Scotland: Premiership": "SC0",
    "Scotland: Championship": "SC1", "Scotland: League One": "SC2", "Scotland: League Two": "SC3",
    "Germany: Bundesliga": "D1", "Germany: 2. Bundesliga": "D2", "Italy: Serie A": "I1", "Italy: Serie B": "I2",
    "Spain: LaLiga": "SP1", "Spain: LaLiga2": "SP2", "France: Ligue 1": "F1", "France: Ligue 2": "F2",
    "Netherlands: Eredivisie": "N1", "Belgium: Jupiler Pro League": "B1", "Belgium: Pro League": "B1",
    "Portugal: Liga Portugal": "P1", "Turkey: Super Lig": "T1", "Greece: Super League": "G1",
}
EXTRA = {
    "Argentina: Liga Profesional": "ARG", "Austria: Bundesliga": "AUT", "Brazil: Serie A": "BRA",
    "China: Super League": "CHN", "Denmark: Superliga": "DNK", "Finland: Veikkausliiga": "FIN",
    "Ireland: Premier Division": "IRL", "Japan: J1 League": "JPN", "Mexico: Liga MX": "MEX",
    "Norway: Eliteserien": "NOR", "Poland: Ekstraklasa": "POL", "Romania: Superliga": "ROU",
    "Russia: Premier League": "RUS", "Sweden: Allsvenskan": "SWE", "Switzerland: Super League": "SWZ",
    "USA: MLS": "USA",
}
HALF_LIFE = 110.0
RHO = -0.08
_cache = {}


def season_codes(today):
    y = today.year % 100 if today.month >= 7 else (today.year - 1) % 100
    return [f"{y:02d}{y + 1:02d}", f"{y - 1:02d}{y:02d}"]


def load_matches(code, today):
    """[(tarih, ev, dep, ev_gol_ağırlıklı, dep_gol_ağırlıklı)]"""
    if code in _cache:
        return _cache[code]
    rows = []
    if code in EXTRA.values():
        txt = veri.get(f"https://www.football-data.co.uk/new/{code}.csv").lstrip("﻿")
        for r in csv.DictReader(io.StringIO(txt)):
            try:
                d = dt.datetime.strptime(r["Date"], "%d/%m/%Y").date()
                hg, ag = float(r["HG"]), float(r["AG"])
            except Exception:
                continue
            if (today - d).days <= 600:
                rows.append((d, r["Home"], r["Away"], hg, ag))
    else:
        for s in season_codes(today):
            txt = veri.get(f"https://www.football-data.co.uk/mmz4281/{s}/{code}.csv").lstrip("﻿")
            for r in csv.DictReader(io.StringIO(txt)):
                try:
                    d = dt.datetime.strptime(r["Date"], "%d/%m/%Y").date()
                    hg, ag = float(r["FTHG"]), float(r["FTAG"])
                except Exception:
                    continue
                try:
                    hg, ag = 0.5 * hg + 0.5 * float(r["HxG"]), 0.5 * ag + 0.5 * float(r["AxG"])
                except Exception:
                    pass
                rows.append((d, r["HomeTeam"], r["AwayTeam"], hg, ag))
    rows = [r for r in rows if r[0] < today]
    _cache[code] = rows
    return rows


def fit(rows, today):
    teams = sorted({r[1] for r in rows} | {r[2] for r in rows})
    att = {t: 1.0 for t in teams}
    dfn = {t: 1.0 for t in teams}
    home = 1.2
    w = [0.5 ** ((today - r[0]).days / HALF_LIFE) for r in rows]
    for _ in range(60):
        na = {t: 0.0 for t in teams}; da = {t: 0.0 for t in teams}
        nd = {t: 0.0 for t in teams}; dd = {t: 0.0 for t in teams}
        for wi, (d, h, a, hg, ag) in zip(w, rows):
            na[h] += wi * hg; da[h] += wi * dfn[a] * home
            na[a] += wi * ag; da[a] += wi * dfn[h]
        for t in teams:
            att[t] = (na[t] + 1.0) / (da[t] + 1.0)  # +1: küçük örneklem için ortalamaya çekme
        m = sum(att.values()) / len(att)
        for t in teams:
            att[t] /= m
        for wi, (d, h, a, hg, ag) in zip(w, rows):
            nd[h] += wi * ag; dd[h] += wi * att[a]
            nd[a] += wi * hg; dd[a] += wi * att[h] * home
        for t in teams:
            dfn[t] = (nd[t] + 1.0) / (dd[t] + 1.0)
        hn = sum(wi * r[3] for wi, r in zip(w, rows))
        hd = sum(wi * att[r[1]] * dfn[r[2]] for wi, r in zip(w, rows))
        home = hn / hd if hd else 1.2
    games = {t: 0 for t in teams}
    for r in rows:
        if (today - r[0]).days <= 400:
            games[r[1]] += 1; games[r[2]] += 1
    return att, dfn, home, games


def probs(lh, la):
    P = [[0.0] * 11 for _ in range(11)]
    for i in range(11):
        for j in range(11):
            p = math.exp(-lh) * lh ** i / math.factorial(i) * math.exp(-la) * la ** j / math.factorial(j)
            if i == 0 and j == 0: p *= 1 - lh * la * RHO
            elif i == 0 and j == 1: p *= 1 + lh * RHO
            elif i == 1 and j == 0: p *= 1 + la * RHO
            elif i == 1 and j == 1: p *= 1 - RHO
            P[i][j] = p
    s = sum(map(sum, P))
    P = [[x / s for x in row] for row in P]
    p1 = sum(P[i][j] for i in range(11) for j in range(11) if i > j)
    px = sum(P[i][i] for i in range(11))
    p2 = 1 - p1 - px
    o25 = sum(P[i][j] for i in range(11) for j in range(11) if i + j >= 3)
    btts = sum(P[i][j] for i in range(1, 11) for j in range(1, 11))
    return p1, px, p2, o25, btts


def best_team(name, teams):
    n = veri.norm(name)
    best, score = None, 0
    for t in teams:
        m = veri.norm(t)
        if not m:
            continue
        if n == m:
            return t
        s = 0
        if n in m or m in n:
            s = min(len(n), len(m)) + 2
        else:
            k = 0
            while k < min(len(n), len(m)) and n[k] == m[k]:
                k += 1
            s = k if k >= 4 else 0
        if s > score:
            best, score = t, s
    return best


def devig(*odds):
    try:
        inv = [1 / float(o) for o in odds]
    except Exception:
        return None
    s = sum(inv)
    return [x / s for x in inv]


def run(day, as_csv=False):
    d = dt.date.fromisoformat(day)
    start = dt.datetime(d.year, d.month, d.day, tzinfo=veri.TR)
    end = start + dt.timedelta(days=1, hours=8)
    fixtures = [x for dd in (d, d + dt.timedelta(days=1)) for x in veri.betexplorer_day(dd) if start <= x["utc"] < end]
    fd = list(csv.DictReader(io.StringIO(veri.get("https://www.football-data.co.uk/fixtures.csv").lstrip("﻿"))))
    out = []
    fitted = {}
    for f in fixtures:
        code = MAIN.get(f["lig"]) or EXTRA.get(f["lig"])
        if not code:
            continue
        if code not in fitted:
            rows = load_matches(code, d)
            fitted[code] = fit(rows, d) if len(rows) > 50 else None
        model = fitted[code]
        if not model:
            continue
        att, dfn, home, games = model
        h, a = best_team(f["ev"], att), best_team(f["dep"], att)
        if not h or not a or h == a:
            continue
        lh, la = att[h] * dfn[a] * home, att[a] * dfn[h]
        p1, px, p2, o25, btts = probs(lh, la)
        mk = devig(f["o1"], f["ox"], f["o2"])
        fx = next((r for r in fd if r["Div"] == code and veri.similar(r["HomeTeam"], h) and veri.similar(r["AwayTeam"], a)), None)
        mo = devig(fx.get("Avg>2.5"), fx.get("Avg<2.5")) if fx else None
        out.append(dict(saat=f["utc"].astimezone(veri.TR).strftime("%d.%m %H:%M"), lig=f["lig"], mac=f"{f['ev']} - {f['dep']}",
                        xg=f"{lh:.2f}-{la:.2f}", az_veri=min(games.get(h, 0), games.get(a, 0)) < 8,
                        m=(p1, px, p2), p=mk, o25=o25, btts=btts, mo25=mo[0] if mo else None,
                        odds=(f["o1"], f["ox"], f["o2"]), ou_odds=(fx.get("Avg>2.5"), fx.get("Avg<2.5")) if fx else None))
    if as_csv:
        w = csv.writer(sys.stdout)
        w.writerow(["saat", "lig", "mac", "beklenen_gol", "m1", "mX", "m2", "p1", "pX", "p2", "m_ust25", "p_ust25", "m_kg", "az_veri"])
        for o in out:
            p = o["p"] or (None, None, None)
            w.writerow([o["saat"], o["lig"], o["mac"], o["xg"], *[f"{x:.3f}" for x in o["m"]],
                        *[f"{x:.3f}" if x else "" for x in p], f"{o['o25']:.3f}", f"{o['mo25']:.3f}" if o["mo25"] else "",
                        f"{o['btts']:.3f}", o["az_veri"]])
        return
    # --- Benham tarzı değer listesi: karışım olasılığı (model+piyasa)/2 ile EV, çeyrek Kelly
    vals = []
    for o in out:
        if not o["p"]:
            continue
        for k, lab in enumerate(("MS1", "MSX", "MS2")):
            try:
                odd = float(o["odds"][k])
            except Exception:
                continue
            pm = (o["m"][k] + o["p"][k]) / 2
            vals.append((pm * odd - 1, o, lab, odd, pm))
        if o["mo25"] and o["ou_odds"]:
            for lab, pmod, pmk, odd in (("2.5 Üst", o["o25"], o["mo25"], o["ou_odds"][0]), ("2.5 Alt", 1 - o["o25"], 1 - o["mo25"], o["ou_odds"][1])):
                try:
                    odd = float(odd)
                except Exception:
                    continue
                pm = (pmod + pmk) / 2
                vals.append((pm * odd - 1, o, lab, odd, pm))
    vals = [v for v in vals if v[0] >= 0.03 and not v[1]["az_veri"]]
    vals.sort(key=lambda v: -v[0])
    if not as_csv:
        print("# DEĞER LİSTESİ (Benham: yalnızca EV>+%3; olasılık = %50 model + %50 marjsız piyasa; pay = çeyrek Kelly, kasanın %'si)")
        for ev, o, lab, odd, pm in vals[:25]:
            b = odd - 1
            kelly = max(0.0, (b * pm - (1 - pm)) / b) / 4
            print(f"  {o['saat']} | {o['lig']} | {o['mac']} | {lab} @ {odd:.2f} | olasılık %{pm * 100:.0f} (adil {1 / pm:.2f}) | EV {ev * 100:+.1f}% | pay %{kelly * 100:.1f}")
        print()
    print(f"# {len(out)} maç modellendi ({len(fixtures)} maçtan; kapsanan ligler: {len(fitted)})")
    print("saat | lig | maç | beklenen gol | MODEL 1/X/2 | PİYASA 1/X/2 | edge 1/X/2 | 2.5Ü model/piyasa | KG model | adil oran (karışım) 1/X/2")
    for o in out:
        m, p = o["m"], o["p"]
        if p:
            mix = [(a + b) / 2 for a, b in zip(m, p)]
            edge = " ".join(f"{(a - b) * 100:+.0f}" for a, b in zip(m, p))
            pstr = " ".join(f"{x * 100:.0f}" for x in p)
            fair = " ".join(f"{1 / x:.2f}" for x in mix)
        else:
            edge = pstr = fair = "-"
        ou = f"{o['o25'] * 100:.0f}/{o['mo25'] * 100:.0f}" if o["mo25"] else f"{o['o25'] * 100:.0f}/-"
        flag = " (az veri)" if o["az_veri"] else ""
        print(f"{o['saat']} | {o['lig']} | {o['mac']}{flag} | {o['xg']} | {' '.join(f'{x * 100:.0f}' for x in m)} | {pstr} | {edge} | {ou} | {o['btts'] * 100:.0f} | {fair}")


def istat(code, home_q, away_q, n=10):
    """Korner/kart/ilk yarı/hakem istatistikleri (22 ana lig; football-data bu sezon + geçen sezon)."""
    today = dt.date.today()
    rows = []
    for s in season_codes(today):
        txt = veri.get(f"https://www.football-data.co.uk/mmz4281/{s}/{code}.csv").lstrip("\ufeff")
        rows += [r for r in csv.DictReader(io.StringIO(txt)) if r.get("FTHG") not in (None, "")]
    rows.sort(key=lambda r: dt.datetime.strptime(r["Date"], "%d/%m/%Y"))
    teams = {r["HomeTeam"] for r in rows} | {r["AwayTeam"] for r in rows}
    f = lambda r, k: float(r.get(k) or 0)
    for q in (home_q, away_q):
        t = best_team(q, teams)
        if not t:
            print(f"{q}: takım bulunamadı"); continue
        ms = [r for r in rows if t in (r["HomeTeam"], r["AwayTeam"])][-n:]
        if not ms:
            continue
        agg = dict(kor_at=0, kor_ye=0, kart=0, kart_rakip=0, iy_at=0, iy_ye=0, gol_at=0, gol_ye=0, ust25=0, kg=0, iy_ust05=0)
        iyms = []
        for r in ms:
            h = r["HomeTeam"] == t
            s_, c_ = ("H", "A") if h else ("A", "H")
            agg["kor_at"] += f(r, s_ + "C"); agg["kor_ye"] += f(r, c_ + "C")
            agg["kart"] += f(r, s_ + "Y") + 2 * f(r, s_ + "R"); agg["kart_rakip"] += f(r, c_ + "Y") + 2 * f(r, c_ + "R")
            g1, g2 = f(r, "FTHG"), f(r, "FTAG"); i1, i2 = f(r, "HTHG"), f(r, "HTAG")
            gs, gc, ihs, ihc = (g1, g2, i1, i2) if h else (g2, g1, i2, i1)
            agg["gol_at"] += gs; agg["gol_ye"] += gc; agg["iy_at"] += ihs; agg["iy_ye"] += ihc
            agg["ust25"] += g1 + g2 >= 3; agg["kg"] += g1 > 0 and g2 > 0; agg["iy_ust05"] += i1 + i2 >= 1
            res = lambda a, b: "1" if a > b else ("X" if a == b else "2")
            iyms.append(f"{'E' if h else 'D'}:{res(ihs, ihc)}/{res(gs, gc)}")
        k = len(ms)
        print(f"## {t} (son {k} lig maçı, kendi açısından)")
        print(f"  gol {agg['gol_at']/k:.2f} att / {agg['gol_ye']/k:.2f} yedi | İY gol {agg['iy_at']/k:.2f}/{agg['iy_ye']/k:.2f} | "
              f"2.5Ü %{100*agg['ust25']/k:.0f} | KG %{100*agg['kg']/k:.0f} | İY 0.5Ü %{100*agg['iy_ust05']/k:.0f}")
        print(f"  korner {agg['kor_at']/k:.1f} kazandı / {agg['kor_ye']/k:.1f} verdi (maç toplamı ort. {(agg['kor_at']+agg['kor_ye'])/k:.1f}) | "
              f"kart puanı (sarı=1, kırmızı=2) {agg['kart']/k:.1f} / rakip {agg['kart_rakip']/k:.1f}")
        print(f"  İY/MS (son maçlar): {' '.join(iyms)}")
    up = next((r for r in csv.DictReader(io.StringIO(veri.get("https://www.football-data.co.uk/fixtures.csv").lstrip("\ufeff")))
               if r["Div"] == code and veri.similar(r["HomeTeam"], home_q) and veri.similar(r["AwayTeam"], away_q)), None)
    ref = (up or {}).get("Referee")
    if ref:
        rm = [r for r in rows if r.get("Referee") == ref]
        if rm:
            y = sum(f(r, "HY") + f(r, "AY") for r in rm) / len(rm); rr = sum(f(r, "HR") + f(r, "AR") for r in rm) / len(rm)
            print(f"## Hakem {ref}: {len(rm)} maç, maç başı sarı {y:.2f}, kırmızı {rr:.2f}")


def kapanis(day):
    """Kapanış oranları (CLV kontrolü): football-data bu sezon CSV'lerinden o günün maçları.
    PSC* = Pinnacle kapanış, AvgC* = ortalama kapanış. Bizim aldığımız oran kapanıştan yüksekse CLV pozitif."""
    d = dt.date.fromisoformat(day)
    for code in sorted(set(MAIN.values())):
        txt = veri.get(f"https://www.football-data.co.uk/mmz4281/{season_codes(d)[0]}/{code}.csv").lstrip("﻿")
        for r in csv.DictReader(io.StringIO(txt)):
            try:
                if dt.datetime.strptime(r["Date"], "%d/%m/%Y").date() != d:
                    continue
            except Exception:
                continue
            print(f"{code} | {r['HomeTeam']} {r.get('FTHG','')}-{r.get('FTAG','')} {r['AwayTeam']} | kapanış ort 1/X/2 {r.get('AvgCH','')} {r.get('AvgCD','')} {r.get('AvgCA','')}"
                  f" | Pinnacle {r.get('PSCH','')} {r.get('PSCD','')} {r.get('PSCA','')} | 2.5Ü/A kapanış {r.get('AvgC>2.5','')} {r.get('AvgC<2.5','')}")


def dusen():
    """betexplorer: son 24 saatte en çok düşen oranlar (bugün ve yarın)."""
    import html as H, re
    t = veri.get("https://www.betexplorer.com/dropping-odds/?sport=football&period=24h&matches=2")
    s = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", t)
    s = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s)))
    i = s.find("Dropping bookies")
    body = s[i:]
    for m in re.finditer(r"([A-Z][\w .'()/-]+: [\w .'()/-]+?) Drop 1 X 2 Best bet ((?:\d\d\.\d\d\.\d{4} )?\d\d:\d\d) (.+?) (\d+)% Drop: \d+% » B's: (\d+)% \((\d+/\d+)\)", body):
        print(f"{m.group(2)} (CET) | {m.group(1)} | {m.group(3)} | düşüş %{m.group(4)} | şirketlerin %{m.group(5)}'i ({m.group(6)})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if sys.argv[1] == "istat":
        istat(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "dusen":
        dusen()
    elif sys.argv[1] == "kapanis":
        kapanis(sys.argv[2])
    else:
        run(sys.argv[1], "--csv" in sys.argv)

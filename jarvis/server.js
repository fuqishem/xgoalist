// Jarvis ev sunucusu: bağımlılıksız Node.js (18+). Başlat: node server.js
'use strict';
const http = require('http'), fs = require('fs'), path = require('path');
const DIR = __dirname, DATA = path.join(DIR, 'data.json'), CFG = path.join(DIR, 'config.json');
const cfg = Object.assign({ port: 3000, token: '', name: 'efendim', city: 'İstanbul', prov: 'gemini', key: '', model: '', base: '' },
  fs.existsSync(CFG) ? JSON.parse(fs.readFileSync(CFG, 'utf8')) : {});
cfg.key = process.env.JARVIS_KEY || cfg.key; cfg.token = process.env.JARVIS_TOKEN || cfg.token;
const DEFAULT_MODEL = { gemini: 'gemini-2.5-flash', groq: 'llama-3.3-70b-versatile', custom: 'llama3.1' };
const BASES = { groq: 'https://api.groq.com/openai/v1', custom: 'http://localhost:11434/v1' };

let db = { notes: [], tasks: [], hist: [] };
try { db = Object.assign(db, JSON.parse(fs.readFileSync(DATA, 'utf8'))); } catch {}
const save = () => fs.writeFileSync(DATA, JSON.stringify(db, null, 1));
const tr = s => s.toLocaleLowerCase('tr-TR');

const WMO = c => c === 0 ? 'açık' : c <= 2 ? 'parçalı bulutlu' : c === 3 ? 'kapalı' : c <= 48 ? 'sisli' : c <= 57 ? 'çiseleyen yağmurlu' : c <= 67 ? 'yağmurlu' : c <= 77 ? 'karlı' : c <= 82 ? 'sağanak yağışlı' : c <= 86 ? 'kar sağanaklı' : 'fırtınalı';
async function weather(q) {
  let cityName = cfg.city;
  const m = q.match(/([a-zçğıöşü]+?)(?:'|’)?\s*(?:da|de|ta|te)\s+(?:hava|bugün|yarın)/i);
  if (m && !/^(bugün|yarın|şu|bu|dışarıda|hava)$/i.test(m[1])) cityName = m[1];
  const g = await (await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=tr`)).json();
  const r = g.results?.[0]; if (!r) return `${cityName} adlı yeri bulamadım.`;
  const w = await (await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${r.latitude}&longitude=${r.longitude}&current=temperature_2m,apparent_temperature,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=2`)).json();
  const c = w.current, d = w.daily;
  if (/yarın/.test(q)) return `${r.name} için yarın en yüksek ${Math.round(d.temperature_2m_max[1])}, en düşük ${Math.round(d.temperature_2m_min[1])} derece. Yağış ihtimali yüzde ${d.precipitation_probability_max[1] ?? 0}.`;
  return `${r.name} için şu an hava ${WMO(c.weather_code)}, ${Math.round(c.temperature_2m)} derece, hissedilen ${Math.round(c.apparent_temperature)}. Bugün ${Math.round(d.temperature_2m_min[0])} ile ${Math.round(d.temperature_2m_max[0])} arası, yağış ihtimali yüzde ${d.precipitation_probability_max[0] ?? 0}.`;
}
const NUM = { sıfır:0, bir:1, iki:2, üç:3, dört:4, beş:5, altı:6, yedi:7, sekiz:8, dokuz:9, on:10, yirmi:20, otuz:30, kırk:40, elli:50 };
const numWords = s => s.replace(/\b[a-zçğıöşü]+\b/g, w => (w in NUM ? NUM[w] : w));
function calc(q) {
  const e = numWords(tr(q)).replace(/,/g, '.').replace(/çarpı|kere/g, '*').replace(/bölü/g, '/').replace(/artı/g, '+').replace(/eksi/g, '-')
    .replace(/[^0-9+\-*/().\s]/g, ' ').replace(/\s+/g, ' ').trim();
  if (!/^[\d+\-*/().\s]+$/.test(e) || !/\d\s*[-+*/]\s*\(?\d/.test(e)) return null;
  try { const v = Function('"use strict";return (' + e + ')')(); return Number.isFinite(v) ? +v.toFixed(6) : null; } catch { return null; }
}
const openTasks = () => db.tasks.filter(x => !x.done);

async function local(raw) {
  const q = tr(raw).replace(/[?!.]+$/g, '').trim(); let m;
  const now = new Date();
  if (/(günaydın özeti|günlük özet|özet ver|bugün ne var)/.test(q)) {
    const t = openTasks();
    return `Günaydın ${cfg.name}. ${now.toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' })}. ${await weather('hava').catch(() => '')} ${t.length ? `Açık görevleriniz: ${t.map(x => x.t).join(', ')}.` : 'Açık göreviniz yok.'}`;
  }
  if (/(saat kaç|saati söyle)/.test(q)) return 'Saat ' + now.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  if (/(bugün|tarih|günlerden)/.test(q) && /(ne|hangi|tarih)/.test(q) && !/hava/.test(q)) return 'Bugün ' + now.toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  if (/hava/.test(q) && /(nasıl|durum|derece|sıcak|soğuk|yağmur|kaç)/.test(q)) return weather(q).catch(() => 'Hava durumuna ulaşamadım.');
  if ((m = raw.match(/^(?:şunu\s+)?not\s+(?:al|et|ekle)[:,]?\s*(.+)$/i) || raw.match(/^(.+?)\s+diye\s+not\s+(?:al|et)$/i))) { db.notes.push({ t: m[1], d: Date.now() }); save(); return 'Not alındı.'; }
  if (/(notlarım|notları (oku|listele|göster))/.test(q)) return db.notes.length ? db.notes.slice(-5).map((n, i) => `${i + 1}. ${n.t}`).join('. ') : 'Kayıtlı notunuz yok.';
  if (/notları (sil|temizle)/.test(q)) { db.notes = []; save(); return 'Tüm notlar silindi.'; }
  if ((m = raw.match(/^(?:görev|hedef)\s+ekle[:,]?\s*(.+)$/i) || raw.match(/^(.+?)\s+(?:görevi|hedefi)\s+ekle$/i) || raw.match(/^(.+?)\s+diye\s+(?:bir\s+)?(?:görev|hedef)\s+ekle$/i))) { db.tasks.push({ t: m[1], done: false }); save(); return `Görev eklendi: ${m[1]}`; }
  if (/(görevlerim|hedeflerim|yapılacaklar|görevleri (oku|listele|göster))/.test(q)) { const o = openTasks(); return o.length ? `${o.length} açık göreviniz var. ` + o.map((x, i) => `${i + 1}. ${x.t}`).join('. ') : 'Açık göreviniz yok. Harika.'; }
  if ((m = numWords(q).match(/(\d+)\.?\s*(?:görevi|hedefi)\s*(?:tamamla|bitir|yaptım)/))) { const it = openTasks()[m[1] - 1]; if (!it) return 'Öyle bir görev bulamadım.'; it.done = true; save(); return `Tamamlandı: ${it.t}. Tebrikler.`; }
  if (/^(merhaba|selam|günaydın|iyi akşamlar)/.test(q)) return `Merhaba ${cfg.name}. Size nasıl yardımcı olabilirim?`;
  const c = calc(raw); if (c !== null && /\d/.test(raw)) return `Sonuç ${String(c).replace('.', ',')}`;
  return null;
}

async function askLLM(text) {
  if (cfg.prov === 'none') return `Bunu yapamıyorum ${cfg.name}, yapay zeka kapalı.`;
  if (!cfg.key && cfg.prov !== 'custom') return `Yapay zeka için config.json içine API anahtarı girilmeli ${cfg.name}.`;
  db.hist.push({ r: 'user', c: text }); db.hist = db.hist.slice(-12);
  const sys = `Sen Iron Man filmlerindeki J.A.R.V.I.S. gibi zarif, esprili, kibar ve yetkin bir kişisel asistansın. Kullanıcıya "${cfg.name}" diye hitap et. Yanıtların Türkçe, sesli okunacağı için KISA (en fazla 2-3 cümle), düz metin olsun; madde işareti, markdown, emoji kullanma. Bilmediğin şeyi uydurma. Şu an: ${new Date().toLocaleString('tr-TR', { dateStyle: 'full', timeStyle: 'short' })}. Açık görevler: ${openTasks().map(x => x.t).join('; ') || 'yok'}.`;
  const model = cfg.model || DEFAULT_MODEL[cfg.prov]; let out;
  if (cfg.prov === 'gemini') {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'x-goog-api-key': cfg.key },
      body: JSON.stringify({ systemInstruction: { parts: [{ text: sys }] }, contents: db.hist.map(h => ({ role: h.r === 'user' ? 'user' : 'model', parts: [{ text: h.c }] })) }) });
    const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || r.status);
    out = j.candidates?.[0]?.content?.parts?.map(x => x.text).join('');
  } else {
    const r = await fetch((cfg.base || BASES[cfg.prov]).replace(/\/$/, '') + '/chat/completions', { method: 'POST', headers: { 'Content-Type': 'application/json', ...(cfg.key ? { Authorization: 'Bearer ' + cfg.key } : {}) },
      body: JSON.stringify({ model, messages: [{ role: 'system', content: sys }, ...db.hist.map(h => ({ role: h.r, content: h.c }))] }) });
    const j = await r.json(); if (!r.ok) throw new Error(j.error?.message || r.status);
    out = j.choices?.[0]?.message?.content;
  }
  out = (out || '').trim() || 'Cevap alamadım.';
  db.hist.push({ r: 'assistant', c: out }); save(); return out;
}
async function ask(q) { try { return (await local(q)) ?? (await askLLM(q)); } catch (e) { return 'Bir sorun oluştu. ' + String(e.message).slice(0, 120); } }

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml' };
const PUBLIC = new Set(['index.html', 'manifest.json', 'icon.svg', 'sw.js']);
http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x'), send = (c, body, type = 'text/plain; charset=utf-8') => { res.writeHead(c, { 'Content-Type': type, 'Cache-Control': 'no-store' }); res.end(body); };
  if (u.pathname === '/api/health') return send(200, 'ok');
  if (u.pathname === '/ask' || u.pathname === '/api/ask') {
    let body = ''; for await (const ch of req) { body += ch; if (body.length > 1e5) return send(413, 'büyük'); }
    let q = u.searchParams.get('q'), tok = u.searchParams.get('token') || req.headers['x-token'];
    if (req.method === 'POST' && body) { try { const j = JSON.parse(body); q = j.q ?? q; tok = tok || j.token; } catch { q = q || body; } }
    if (cfg.token && tok !== cfg.token) return send(401, 'Yetkisiz. Adresin sonuna &token=... ekleyin.');
    if (!q) return send(400, 'q parametresi gerekli');
    return send(200, await ask(String(q)));
  }
  if (u.pathname === '/api/state') { if (cfg.token && u.searchParams.get('token') !== cfg.token) return send(401, 'Yetkisiz'); return send(200, JSON.stringify({ notes: db.notes, tasks: db.tasks }), TYPES['.json']); }
  const f = u.pathname === '/' ? 'index.html' : u.pathname.slice(1);
  if (PUBLIC.has(f)) return send(200, fs.readFileSync(path.join(DIR, f)), TYPES[path.extname(f)] || 'text/plain');
  send(404, 'yok');
}).listen(cfg.port, '0.0.0.0', () => console.log(`Jarvis hazır: http://localhost:${cfg.port}  (telefondan: bilgisayarın yerel IP'si ile)`));

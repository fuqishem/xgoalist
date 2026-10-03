# J.A.R.V.I.S.

Telefonda ve bilgisayarda çalışan, sesli, Türkçe kişisel asistan (PWA). Derleme veya sunucu gerekmez.

## Çalıştırma
- Yerelde: `cd jarvis && python3 -m http.server 8080`, ardından Chrome'da `http://localhost:8080`.
- Telefonda: GitHub Pages'i açın (Settings → Pages → branch → `/ (root)`), `https://<kullanıcı>.github.io/xgoalist/jarvis/` adresini Chrome'da açıp "Ana ekrana ekle" deyin.

## Yapay zeka (ücretsiz seçenekler)
Sağ üstteki ⚙ menüsünden seçin. Anahtar yalnızca cihazınızın tarayıcısında saklanır.
- **Gemini**: aistudio.google.com/apikey (ücretsiz katman)
- **Groq**: console.groq.com/keys (ücretsiz katman)
- **Ollama** (evde, tamamen ücretsiz): "Özel" seçip `http://<bilgisayar-ip>:11434/v1` yazın.

## Yerel komutlar (anahtarsız çalışır)
saat, tarih, hava durumu ("Ankara'da hava nasıl"), zamanlayıcı ("10 dakika zamanlayıcı kur"), not ("not al: …"), görev ("görev ekle …", "görevlerim", "1. görevi tamamla"), hesaplama, YouTube/Google arama, şaka.

Not: Sesli komut Android Chrome ve masaüstü Chrome/Edge'de çalışır. iPhone Safari'de konuşma tanıma sınırlıdır; yazarak kullanabilirsiniz.

## iPhone + HomePod mini
- iPhone'da uygulama ekranındayken klavyedeki 🎙 dikte tuşunu kullanın (ana ekrandaki uygulamada web mikrofonu çalışmaz).
- **Hands-free Siri Kısayolu** (Kısayollar uygulaması → +):
  1. "Metin iste" (Ask for Input) → istem: "Buyurun?"
  2. "URL içeriğini al" → `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`, Yöntem: POST, Başlık `x-goog-api-key: <anahtarınız>`, Gövde (JSON): `contents` → `parts` → `text` = Metin istem sonucu (başına "Kısa, Türkçe, düz metinle cevapla: " ekleyin).
  3. "Sözlüğü al" → `candidates.1.content.parts.1.text`.
  4. "Metni oku" (Speak Text).
  5. Adını "Jarvis" koyun. "Hey Siri, Jarvis" deyince çalışır.
- HomePod mini'de Kısayollar çalışır, ama "Metin iste" HomePod'da desteklenmeyebilir. Orada sabit işler (örn. "Günaydın özeti": hava + sabit bir prompt) için girdisiz kısayol yapın.

## Ev sunucusu (Windows) — önerilen kurulum
Bilgisayar açık kaldığı sürece Jarvis'in "beyni" olur: API anahtarı yalnızca orada durur, notlar/görevler tüm cihazlarda ortaktır, Siri Kısayolları ve HomePod tek bir adrese istek atar.

1. https://nodejs.org adresinden **Node.js LTS** kurun.
2. Repoyu indirin (GitHub → Code → Download ZIP) ve `jarvis` klasörünü açın.
3. `start-jarvis.bat`'ı çift tıklayın (ilk seferde `config.json` oluşur). Pencereyi kapatın, `config.json`'u Not Defteri ile açıp **`key`** (Gemini/Groq anahtarı), **`token`** (uzun bir parola) ve **`city`** alanlarını doldurun. `start-jarvis.bat`'ı yeniden başlatın.
4. Windows açılışında otomatik başlasın: `Win+R` → `shell:startup` → `start-jarvis.bat` kısayolunu oraya koyun.
5. İlk çalıştırmada Windows Güvenlik Duvarı sorarsa **Özel ağlar**a izin verin.
6. Bilgisayarın yerel IP'sini bulun (`ipconfig` → IPv4, örn. `192.168.1.20`). Router'dan bu bilgisayara sabit IP verin.

**Kullanım**
- Tarayıcı: `http://192.168.1.20:3000/?token=PAROLA` (token bir kez kaydedilir).
- Siri Kısayolu (iPhone ve HomePod): "Metin iste" → "URL'nin içeriğini al" ile `http://192.168.1.20:3000/ask?token=PAROLA&q=` + (URL kodlanmış metin) → "Metni oku". Soru sormayan HomePod kısayolları için sabit metin kullanın, örn. `q=günaydın özeti` → "Hey Siri, günaydın Jarvis".
- Ev dışında: bilgisayara ve iPhone'a ücretsiz **Tailscale** kurun; `192.168...` yerine bilgisayarın Tailscale adresini kullanın. Portu internete açmayın.

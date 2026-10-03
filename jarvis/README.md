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

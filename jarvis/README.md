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

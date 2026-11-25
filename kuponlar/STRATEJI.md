# Kupon stratejisi — Matthew Benham ilkeleri (25.11.2026'dan itibaren)

Benham (Smartodds, Brentford, FC Midtjylland): sonuçlara değil süreç verisine bakar, kendi modeliyle piyasayı yener, yalnızca değerli bahse girer.

## Uygulanan kurallar
1. **Sonuç değil süreç:** Takım gücü xG/xGA ve şut kalitesiyle ölçülür (model %50 gol + %50 xG). Puan tablosu tek başına kullanılmaz.
2. **Şans → ortalamaya dönüş:** `veri.py lig` çıktısındaki "şans" (P − xPuan). +6 ve üstü = şanslı takım (karşısına/aleyhine eğilim), −6 ve altı = şanssız takım (lehine eğilim).
3. **Yalnızca değer:** Her seçimde olasılık = %50 model + %50 marjsız piyasa. Beklenen değer (EV) ≥ +%3 ise "değer", −%3 ile +%3 arası "nötr", altı "alma". Modelin kapsamadığı liglerde (ŞL, NBA vb.) değer kanıtı yoktur → bunu açıkça belirt.
4. **Piyasaya saygı:** Model ile piyasa arasındaki fark çok büyükse (>15 puan) önce modelin bilmediği bir haber ara (rotasyon, sakatlık). Genelde piyasa haklıdır.
5. **Marj gerçeği:** Kombine kuponlarda her ayağın marjı çarpılır; 10 ayaklı kupon değersiz ayaklarla uzun vadede kaybettirir. Kupon ayakları mümkün olduğunca değer/nötr seçimlerden kurulur; ana öneri tekli değer bahisleridir.
6. **Kasa yönetimi:** Tekli değer bahislerinde pay = çeyrek Kelly (kasanın %'si). Kuponlara kasanın küçük, sabit bir kısmı (ör. %0.5-1) ayrılır.
7. **Ölçüm:** Kısa vadeli sonuç değil, kapanış oranını geçmek (CLV) ve uzun vadeli ROI ölçülür (`model.py kapanis <tarih>`). istatistik.md'de seçimler değer/nötr/negatif olarak ayrı izlenir.
8. **Duran top ve detay:** Korner/kart/İY pazarları `model.py istat` verisiyle seçilir, tahminle değil.

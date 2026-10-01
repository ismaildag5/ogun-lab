# Doğrulama durumu — 1 Ekim 2026

## Tamamlananlar

- Python 3.12 ile 27 otomatik test geçti. Çıktı: `backend-tests.txt`.
- 100 yemek, 10 kurgusal mutfak; ilk açılış verisi tekrar çalıştırıldığında çoğalmıyor.
- Fiyat geçmişi, hedef fiyat geçişi, büyük düşüş eşikleri, cihaz başına takip, tekrar gönderim ve süre sonu davranışları izole SQLite testleriyle doğrulandı.
- Gerçek tarayıcıda Tavuk dürüm 180 → 140 TL hedef takibi, Klasik burger 200 → 120 TL büyük düşüşü, değişmeyen fiyatın yeni olay üretmemesi denendi.
- Sunucu yeniden başlatıldıktan sonra kayıtlar ve tarayıcı takibi korundu.
- 50 TL bütçede uygun yemek yokken bütçeden bağımsız indirim sekmesi 120 TL burgeri %40 / 80 TL düşüşle gösteriyor. Görsel: `price-drops.png`.
- Önceki oturumda 390 piksel mobil görünümde yemek ekranında yatay taşma olmadığı, yönetim tablosunun kendi alanında kaydığı kontrol edildi.
- Gradle 8.13 wrapper oluşturuldu.
- Kullanıcının çalıştırdığı CMD ile Java derlemesi tamamlandı. Android 8.0 uyumsuz `windowLightNavigationBar` ayarı `values-v27` içine taşındı; son `assembleDebug lintDebug` başarılı (42 saniye, 47 görev). Lint: 0 hata, 22 uyarı.
- `ogun-deneme.apk` APK Signature Scheme v2 ile doğrulandı; paket `com.ogunlab.app`, sürüm `0.3.0-deneme`, min SDK 26 / target SDK 35.
- APK SHA-256: `B3F5DA34FAA54E35C97320A50739A7642FD9FDDACE4D1BF02494A32176990791`.
- Firebase `ogun-deneme` projesi Analytics ve Gemini kapalı olarak başarıyla oluşturuldu. İlk ProgressEvent hatasının kesin nedeni belirlenmedi.
- Firebase Android kaydı konsoldan doğrulandı: `com.ogunlab.app`, `Öğün Deneme`. FCM API (V1) etkin.
- Firebase yapılandırma dosyalarının indirilmesi sonraki aşamaya bırakıldı. Dosyası alınamayan, kullanılmamış servis hesabı anahtarı silindi. Yerel Firebase bağlantısı henüz tamamlanmadı.
- Windows başlatıcıları (`BASLAT.cmd`, `TELEFONLA-BASLAT.cmd`) eklendi; PowerShell politikası gerektirmez. Python yolu kontrolü geçti.

## Henüz doğrulanmayanlar

- Fiziksel cihazda kurulum ve arayüz testi yapılmadı. Lint uyarıları ayrıca kaynak raporunda görülebilir: `android/app/build/reports/lint-results-debug.txt`.
- İlk Windows derlemesi erişim kısıtlamasına takıldı; kullanıcı oturumunda Java derlemesi yapıldıktan sonra kaynak düzeltmesi ve son derleme otomasyon oturumunda tamamlandı. Başlatıcı artık saf CMD kullanır, PowerShell politikası değiştirilmedi. `android-build.log` ilk lint hatasını içerebilir; nihai lint raporu günceldir.
- Firebase servis hesabı ve sunucu yapılandırması henüz tamamlanmadı.
- Gerçek FCM gönderimi ve telefonda bildirim teslimi denenmedi. Otomatik testlerde taklit gönderici kullanıldı. Tarayıcı deneme uyarısı veya testlerin geçmesi gerçek telefon teslimi kanıtı değildir.

## Sonraki kabul testi

Firebase yapılandırması ve APK kurulumundan sonra telefon ile bilgisayarı aynı Wi-Fi ağına bağla, sunucuyu `--lan` ile başlat, telefondan eşleştir ve bildirim izni ver. Tavuk dürüm 180 TL iken telefondan 140 TL hedefi ekle; uygulama arka plandayken fiyatı 140 TL yap. Telefon ekranında bildirim ve sunucudaki alındı onayı birlikte kontrol edilmeli.

# Telefon bildirimini etkinleştirme

Bu proje kendi bilgisayarındaki SQLite veritabanını kullanır. Firebase yalnızca bildirim taşıyıcısıdır. Firestore, ücretli Cloud Functions, hosting veya faturalandırma hesabı gerekmiyor.

## 1. Ücretsiz Firebase projesi

https://console.firebase.google.com adresinde kendi Google hesabınla oturum aç. Şifre veya doğrulama kodlarını sohbete yazma. Yeni proje oluştur; örneğin `ogun-deneme`. Varsa ücretli plan geçişini seçme. Google Analytics ve isteğe bağlı yapay zekâ özellikleri bu deneme için gerekli değil. Hizmet şartlarını okuyup kabul etme kararı sana aittir.

## 2. Android uygulama kaydı

Proje ayarlarında Android uygulaması ekle. Paket adı tam olarak **com.ogunlab.app** olmalı. Görünen adı `Öğün Deneme` yapabilirsin. FCM için SHA parmak izi zorunlu değildir. `google-services.json` dosyasını bilgisayarına indir. Bu projede Firebase ayarları eşleştirmeden sonra sunucudan yüklenir; dosyayı APK içine yerleştirip tekrar derlemek gerekmez.

## 3. Sunucu gönderim yetkisi

Proje ayarları → Hizmet hesapları / Service accounts → Firebase Admin SDK ekranından sunucuda kullanılacak servis hesabı JSON anahtarını oluşturup indir. Bu anahtar gizlidir; sohbete yapıştırma, Git'e veya paylaşım paketine ekleme. Anahtar oluşturma hesabında yönetim yetkisi gerektirir. Kurumsal hesapta anahtar oluşturma engelliyse korumayı kaldırmak yerine yöneticinle uygun kimlik doğrulama yöntemini belirle.

Cloud Messaging ekranında **Firebase Cloud Messaging API (V1)** etkin olmalıdır. Eski sunucu anahtarı / legacy API kullanılmıyor. Sunucu kimliğinin ilgili projede FCM mesajı gönderme yetkisi olmalı. Bu deneme servis hesabına yeni geniş yönetici rolleri eklemez.

İki dosya hazır olduğunda uygulama klasöründe şu komutu, dosyaların gerçek yollarıyla çalıştır:

```powershell
.\.venv\Scripts\python.exe firebase_kur.py --android-json 'C:\dosyalar\google-services.json' --service-account 'C:\dosyalar\servis-hesabi.json'
```

Henüz Python ortamı yoksa önce `python -m venv .venv`, ardından `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` çalıştır. Araç yalnızca eşleşen proje/paket bilgilerini kabul eder ve özel dosyaları `private/` altına yazar. Anahtar içeriğini ekrana basmaz.

## 4. Telefonla bağlantı

1. Normal sunucu açıksa kapat. `TELEFONLA-BASLAT.cmd` dosyasını çift tıklayarak sunucuyu aynı bilgisayarda başlat.
2. Bilgisayarda http://127.0.0.1:8767/admin adresini aç. Firebase ayarları mevcut görünmeli.
3. Android 8 veya üzeri, Google Play hizmetleri bulunan telefona deneme APK'sını yükle. Bu bir mağaza sürümü değildir.
4. Telefon ve bilgisayar aynı güvenilir Wi-Fi ağında olsun. Windows bağlantı izni isterse yalnızca bu deneme sunucusunun gerekli özel ağ erişimini değerlendir; güvenlik duvarını kapatma.
5. Yönetim ekranında eşleştirme kodu oluştur. Ekrandaki yerel IP adresini ve kodu Android uygulamasının “Sunucuya bağlan” penceresine yaz. Telefonda `127.0.0.1` bilgisayarını göstermez.
6. Uygulamada “Bildirim izni”ni aç. Yönetim ekranında telefonun adı ve “Bildirim cihaz kaydı var” görünmeli.

Firebase yapılandırmasını daha sonra eklediysen uygulamayı yeniden öne getir. Cihaz kaydını tekrar dener. Başka bir Firebase projesine geçersen uygulama sürecini yeniden başlatıp bağlantıyı yeniden eşleştir.

## 5. Gerçek uçtan uca test

1. Gerekirse yönetim ekranından Tavuk dürüm fiyatını önce 180 TL yap.
2. **Telefondan** Tavuk dürüm için 140 TL hedefi belirle. Tarayıcıdaki takip, telefondaki kullanıcıdan ayrıdır.
3. Ana ekran tuşuyla uygulamayı arka plana al. Ayarlardan “Zorla durdur” kullanma.
4. Bilgisayardan fiyatı 140 TL yap. Yönetim ekranında uygun takip için bildirim kaydı oluşmalı.
5. Durum önce bekliyor/gönderiliyor, sonra FCM kabul etti olabilir. Bu tek başına telefonda görüntülendiğini ispatlamaz.
6. Telefonda bildirimi gör ve dokun. İlgili yemeğin güncel fiyat ekranı açılmalı. Telefonun gösterim isteğini işlemesi ve sunucuya onay göndermesi sonrası “Telefonda alındı” görünür; bu insanın okuduğu anlamına gelmez.

Telefon internetten veya yerel ağdan koparsa gecikme olabilir. Bildirim alındı onayı yerel sunucuya ulaşamadığında telefonda saklanır ve uygulama tekrar açılınca gönderilmeye çalışılır. Gönderilmeyen deneme bildirimleri 15 dakika sonra sona erer. Android pil ayarları, bildirim izni, kanal ayarları, internet ve Google Play hizmetleri teslimi etkiler.

Resmî kaynaklar: [Android Firebase kurulumu](https://firebase.google.com/docs/android/setup), [FCM Android başlangıcı](https://firebase.google.com/docs/cloud-messaging/android/get-started), [sunucu ortamı](https://firebase.google.com/docs/cloud-messaging/server-environment), [ücretlendirme](https://firebase.google.com/pricing).

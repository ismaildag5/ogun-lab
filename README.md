# Öğün — kendi veritabanımızla deneme

100 kurgusal yemek, 10 kurgusal mutfak. Gerçek yemek platformlarına bağlantı yok. SQLite ve Python sunucusu, bilgisayarda fiyat yönetimi, Android istemcisi ve FCM gönderim kuyruğu birlikte bulunur.

Pamukkale Üniversitesi çevresindeki öğrenciler için geliştirilen bu prototip, bütçeye uygun yemekleri bulmayı ve takip edilen yemeklerdeki fiyat düşüşlerini göstermeyi amaçlar. Sipariş veya ödeme işlemi yapmaz.

## İlk kurulum

Python 3.12 veya üstünü kur. Depoyu indirdikten sonra proje klasöründe:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server/app.py
```

Linux/macOS'ta Python yolu `.venv/bin/python` olur. İlk açılışta örnek veritabanı otomatik oluşur. Firebase kurulumu gerçek telefon bildirimi aşamasında gerekir; yemek listesi, fiyat yönetimi ve tarayıcı denemesi Firebase olmadan kullanılabilir.

| Klasör | İçerik |
|---|---|
| `server/` | Python HTTP sunucusu, SQLite ve bildirim kuyruğu |
| `web/` | Yemek listesi, takip ve fiyat yönetimi ekranları |
| `android/` | Java Android uygulaması ve Gradle wrapper |
| `tests/` | İzole veritabanıyla otomatik testler |

Çalışma veritabanı, özel anahtarlar, cihaz kimlikleri ve derleme çıktıları Git deposuna eklenmez. Yeni kurulum, `server/catalog_seed.py` içindeki kurgusal verilerle başlar.

## Bilgisayarda açma

Windows'ta `BASLAT.cmd` dosyasını çift tıkla. Telefonla deneme için `TELEFONLA-BASLAT.cmd` kullan. Bu başlatıcılar PowerShell çalıştırma politikası değişikliği gerektirmez. Ardından:

- Yemekler: http://127.0.0.1:8767
- Fiyat yönetimi: http://127.0.0.1:8767/admin

Sunucu zaten çalışıyorsa ikinci kez başlatma. Durdurmak için çalıştığı terminalde Ctrl+C kullan. Betik engellenirse PowerShell güvenlik politikasını değiştirmeden `python server/app.py` komutunu kullanabilirsin. Python 3.12 ile doğrulandı. Sunucu yalnızca bilgisayarda çalışır; kalıcı hosting değildir.

Veritabanı `data/lab.sqlite3` dosyasıdır. İlk çalıştırmada 100 yemek eklenir; sonraki çalıştırmalar fiyatlarını veya takiplerini sıfırlamaz. Önceki gerçek veri pilotu ayrı klasörde korunur.

## İlk deneme

1. Yemek ekranında Tavuk dürüm ara ve “Takip et” seç.
2. “Hedef fiyatıma ulaşınca” seçeneğine 140 TL yaz.
3. Fiyat yönetiminde aynı yemeği seçip fiyatını 140 TL yap. Başlangıç fiyatı zaten 140 veya altındaysa önce 180 TL yap.
4. Yemek ekranındaki deneme uyarısını ve fiyat geçmişini incele. Ekran açıkken 5 saniyede bir yenilenir.
5. Telefon testi için aynı takibi Android uygulamasından ayrıca oluştur. Tarayıcı ve telefon farklı kullanıcılardır.

Yerel geliştirmede tarayıcıyla Tavuk dürüm 180 → 140 TL, Klasik burger 200 → 120 TL senaryoları denendi. Bu test geçmişi Git deposunda bulunmaz; yeni kurulum temiz örnek veriyle başlar.

## Takip kuralları

- **Her düşüş:** Yeni fiyat bir önceki kayıtlı fiyattan düşükse.
- **Hedef fiyat:** Fiyat, hedefin üstünden hedefe veya altına geçerse. Hedefin altındaki her küçük değişiklik yeniden uyarı üretmez. Henüz gönderilmeyen ilk hedef uyarısı, fiyat daha da düşerse geçerliliğini korur.
- **Büyük düşüş:** Son düşük fiyat döneminden önceki 7 günde kayıtlı en düşük fiyatla karşılaştırınca hem en az %25 hem 40 TL düşüş. Fiyatı yükseltip eski seviyesine geri getirmek tek başına büyük indirim sayılmaz. Her yeni daha düşük seviyenin referansı yeniden hesaplanır.
- “Fiyatı düşenler” bütçeden bağımsızdır. Büyük düşüşler ilk kaydından itibaren 72 saat görünür.

Kendi yönettiğimiz fiyatlar değiştirene kadar geçerlidir; gerçek platformdan gözlemmiş gibi 24 saatlik doğrulama etiketi kullanılmaz. Her yemeğin sabit kimliği, mutfağı ve porsiyonu vardır; fiyat dışı içerik değiştirme ekranı bu sürümde yoktur.

## Bildirim nasıl çalışır?

Fiyat değişikliği ve uygun kullanıcıların bildirim kayıtları tek veritabanı işlemiyle yazılır. Sunucu 2 saniyede bir gönderim kuyruğunu kontrol eder. Telefonun sürekli fiyat veritabanını sorgulaması gerekmez. Android uygulaması yalnızca öndeyken 15 saniyede bir listeyi yeniler; arka plandaki bildirim FCM üzerinden gelir.

Firebase yokken kayıtlar bekler; sahte telefon teslimi üretilmez. Telefona ait FCM kimliği yoksa da gönderim bekler. Deneme bildirimlerinin ömrü 15 dakikadır. Gönderim hataları artan bekleme ile yeniden denenir. İşlem kimliği ve cihaz/olay eşsizliği aynı fiyat değişikliğini çift kaydetmeyi önler; Android tarafı aynı bildirim kimliğini tekrar göstermez.

Fiyat yükselirse henüz gönderilmemiş eski uyarı iptal edilir. Bir sonraki uygun düşüş aynı kullanıcı için bekleyen eski uyarının yerini alır. Gönderilmiş push mesajını geri çağırma garantisi yoktur; bildirime dokunulduğunda güncel fiyat sunucudan okunur.

Durumlar:

| Durum | Anlamı |
|---|---|
| Tarayıcı denemesi | Sadece bilgisayar ekranındaki test uyarısı |
| Gönderim bekliyor | Kuyruk kaydı var; henüz FCM kabulü yok |
| FCM kabul etti | Google gönderim isteğini kabul etti; telefon teslimi kanıtlanmadı |
| Telefonda alındı | Android uygulaması bildirimi gösterme isteğini işledi ve sunucuya onay verdi; kullanıcının okuduğu anlamına gelmez |
| Süresi doldu / iptal / yeni fiyat var | Bekleyen uyarı artık gönderilmez |

## Android ve Firebase

Android kaynakları `android/` altındadır. Paket adı `com.ogunlab.app`, Android 8+ ve Google Play hizmetleri gerekir. Android kaynak kodu Java'dır. Firebase ayarları APK'ya gömülmez; yerel sunucuyla eşleştirmede alınır. Servis hesabı anahtarı yalnızca sunucuda kalır.

30 Eylül 2026'da deneme APK'sı derlendi ve imzası doğrulandı. Android lint sonucu: 0 hata, 22 uyarı. Fiziksel telefonda kurulum ve bildirim testi henüz yapılmadı. APK üretilen bir dosyadır ve kaynak deposuna eklenmez. Android Studio'da `android/` klasörünü aç veya JDK 17 ve Android SDK 35 kurulu bir terminalde şu komutları çalıştır:

```powershell
cd android
.\gradlew.bat assembleDebug lintDebug
```

Linux/macOS'ta `./gradlew assembleDebug lintDebug` kullan. SDK konumunu Android Studio'dan veya `ANDROID_HOME` ortam değişkeniyle belirt. APK çıktısı: `android/app/build/outputs/apk/debug/app-debug.apk`.

CMD başlatıcısı PowerShell kullanmaz; “running scripts is disabled” hatası için Windows betik politikasını değiştirmek gerekmez.

Gerçek bildirim için [FIREBASE-KURULUM.md](FIREBASE-KURULUM.md) yönergeleri tamamlanmalıdır. Bu kurulum için Google hesabına kendin giriş yapman ve Android telefonla teslimi denemen gerekir. Firebase yapılandırması olmadan “telefon bildirimi çalıştı” denemez.

Telefon bağlantısı için `./telefonla-baslat.ps1` veya `python server/app.py --lan` kullan. Bu seçenek yalnızca deneme telefon API'sini yerel ağa açar; yönetim ekranı bilgisayarın loopback adresinde kalır. Yönetim ekranından tek kullanımlık, 10 dakikalık eşleştirme kodu oluştur. Kullanıcı tercihleri telefon kimliğine bağlıdır. Kod denemeleri sınırlandırılır; cihaz erişim anahtarı sunucuda özetlenmiş biçimde saklanır.

Bu prototip güvenilir yerel ağda HTTP kullanır. İnternete açık çok kullanıcılı hizmet olarak yayımlanmamalıdır. Üretim aşamasında HTTPS, kullanıcı hesapları, cihaz erişimini iptal etme ve kalıcı barındırma gerekir. Uygulamayı ayarlardan zorla durdurmak ve Android bildirim/pil izinleri teslimi etkileyebilir.

## Geliştirici komutları

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe server/app.py
```

Fiyat yönetimi ve domain testleri Python standart kütüphanesiyle çalışır. FCM gönderimi için `firebase-admin` gerekir. Android projesini Android Studio'da `android/` klasöründen aç; Android SDK 35 ve JDK 17 kullan. Derleme: `gradlew.bat assembleDebug lintDebug`.

Testler izole geçici veritabanında çalışır. Gerçek Firebase'e mesaj göndermez. Cihaz teslimi ayrı kabul testidir. Güncel doğrulama durumu `verification/RESULTS.md` dosyasındadır.

`private/`, `.venv/`, çalışma veritabanındaki cihaz kimlikleri, derleme önbellekleri ve servis hesabı anahtarları paylaşım paketine eklenmemelidir. Veritabanını yedeklerken çalışan SQLite bağlantısının backup API'sini kullan; WAL dosyaları varken yalnızca ana dosyayı kopyalama.

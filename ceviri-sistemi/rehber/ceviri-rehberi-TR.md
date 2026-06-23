# 🌐 Lato Çeviri Botu — Kullanım Rehberi

> **Bot:** @Latotry_bot
> **Konum:** 🌐 Çeviri başlığı (Topic 146)
> **Diller:** 🇹🇭 Tayça ↔ 🇹🇷 Türkçe ↔ 🇬🇧 İngilizce

---

## 📌 Bot Ne İşe Yarar?

Lato Çeviri Botu, otel personelinin birbiriyle farklı dillerde anında iletişim kurmasını sağlar. Bir kişi sesli veya yazılı mesaj gönderdiğinde, bot:

1. Mesajın dilini **otomatik tespit eder** (Tayça, Türkçe veya İngilizce).
2. Mesajı **diğer dillere çevirir**.
3. Çeviriyi grupta herkese gösterir.
4. Ses kayıtlıysa, **sizin ses tonunuzda** sesli çeviri yapabilir.

**Örnek:**
> Ahmet Türkçe sesli mesaj gönderir → Bot Tayça ve İngilizce'ye çevirir → Taylandlı ve İngilizce konuşan personel anında anlar.

---

## 🚀 Nasıl Kullanılır?

### Sesli Mesaj Gönderme
1. 🌐 **Çeviri** başlığına gidin.
2. Telegram mikrofon ikonuna basın ve konuşun.
3. Bot mesajınızı dinler, tespit eder ve diğer dillere çevirir.

### Yazılı Mesaj Gönderme
1. 🌐 **Çeviri** başlığına yazınızı yazın.
2. Bot dilini tespit eder ve diğer dillere çevirir.

> 💡 **İpucu:** Bot en iyi sonucu verirken net ve doğal konuşun. Yavaşça konuşmanıza gerek yok.

---

## 🎙️ Ses Kaydı (Voice Registration)

Bot'un çevirileri **sizin ses tonunuzda** yapabilmesi için ses kaydı yapmanız gerekir.

### Adım Adım Kayıt:

| Adım | Yapılacak İşlem |
|------|----------------|
| **1** | 🌐 Çeviri başlığında `/register` komutunu gönderin |
| **2** | Bot sizden isminizi isteyecek — adınızı veya takma adınızı yazın (örnek: `Ahmet`) |
| **3** | Bot sizden bir ses kaydı isteyecek — **15–30 saniye** arası doğal konuşun |

### Ses Kaydında Ne Söyleyebilirim?

Herhangi bir şey! Örnek:

> *"Merhaba, benim adım Ahmet. Ben Lato Hotel'de resepsiyonist olarak çalışıyorum. Günlük işlerim arasında misafir karşılama, oda rezervasyonu ve telefon görüşmeleri var. İşimi çok seviyorum ve misafirlerimize en iyi hizmeti sunmaya çalışıyorum."*

**Önemli:**
- ✅ Sakin ve net konuşun
- ✅ Arka plan gürültüsü olmayan bir yerde kayıt yapın
- ✅ En az 15 saniye, en fazla 30 saniye konuşun
- ❌ Fısıltı yapmayın
- ❌ Çok hızlı konuşmayın

---

## 🧬 Ses Klonlama Nasıl Çalışır?

Bot, **ElevenLabs** teknolojisini kullanarak sesinizi klonlar:

1. Ses kaydınız alındığında, sistem ses tonunuzu öğrenir.
2. Bundan sonra, bot sizin adınıza çeviri yaptığında, **çeviriyi sizin sesinizle** seslendirir.
3. Örnek: Taylandlı bir personel Tayca konuştuğunda, bot bunu Türkçe'ye çevirir ve Türkçe çeviriyi **sizin ses tonunuzla** okur.

> 🔒 Sesiniz yalnızca bu bot içinde kullanılır. Başka hiçbir yerle paylaşılmaz.

---

## 🔤 Aksan Düzeltmeleri (Accent Corrections)

Bazen bot, özel isimleri veya yerel kelimeleri yanlış duyabilir. Doğru telaffuzu öğretmek için:

### Komut:
```
/accent add yanlışkelime doğrucasım
```

### Örnekler:
```
/accent add phuket puket
/accent add sawatdee savatdi
/accent add kapib kapık
```

Bu sayede bot bu kelimeleri her seferinde doğru telaffuz eder.

### Mevcut Düzeltmeleri Görme:
```
/accent list
```

### Düzeltme Silme:
```
/accent remove yanlışkelime
```

---

## 📋 Komut Listesi

| Komut | Açıklama |
|-------|----------|
| `/register` | Ses kaydı yapma — bot sizin ses tonunuzu öğrenir |
| `/myvoice` | Ses kaydınızın durumunu gösterir (kayıtlı mı, hazır mı) |
| `/accent` | Aksan düzeltmeleri ekle/gör/sil (`/accent add`, `/accent list`, `/accent remove`) |
| `/languages` | Bot'un desteklediği dilleri listeler |
| `/speakers` | Ses kaydı yapmış kişilerin listesini gösterir |
| `/help` | Tüm komutları ve kullanım bilgilerini gösterir |

---

## 🔒 Gizlilik

- 🔐 Ses kayıtlarınız **otel sunucusunda yerel olarak** saklanır.
- 🚫 Ses kayıtları hiçbir üçüncü taraf hizmetle paylaşılmaz (ElevenLabs dışında klonlama için).
- 👤 Yalnızca bot çeviri yapmak için sesinizi kullanır.
- 🗑️ İstediğiniz zaman ses kaydınızın silinmesini isteyebilirsiniz — `/help` komutu ile iletişime geçin.

---

## ❓ Sık Sorulan Sorular

**S: Her mesajı sesli mi çeviriyor?**
C: Hayır. Bot önce yazılı çeviri yapar. Ses kaydınız varsa ve sesli çeviri uygunsa, sesli de verir.

**S: Birden fazla dilde ses kaydı yapabilir miyim?**
C: Şimdilik her kişi için bir ses kaydı yeterlidir. Bot ses tonunuzu tüm dillere uygular.

**S: Ses kaydımı güncellemek istiyorum, ne yapmalıyım?**
C: Tekrar `/register` komutunu kullanın. Yeni kayıt eskisinin yerini alır.

**S: Bot çeviriyi yanlış yaptı, ne yapmalıyım?**
C: Bot'u kullanmaya devam edin. Hataları telaffuz için `/accent` komutunu kullanabilirsiniz.

---

## 📞 Destek

Sorunuz varsa, 🌐 Çeviri başlığında yazın veya `/help` komutunu kullanın.

**Kolay gelsin! 🌟**

---

*Lato Çeviri Botu — Phuket, Tayland*
*@Latotry_bot*

# ✈️ AutoCheck-in Telegram Botu

Uçuş check-in işlemini otomatik yapan Telegram botu.
Uçuştan 24 saat önce otomatik check-in yapar ve boarding pass'i gönderir.

---

## 🚀 Kurulum (Adım Adım)

### 1. Bot Token Al
1. Telegram'da [@BotFather](https://t.me/BotFather) yazın
2. `/newbot` komutunu gönderin
3. Bot ismi ve kullanıcı adı girin
4. Size verilen token'ı kopyalayın (şuna benzer: `7123456789:AAFxxx...`)

### 2. Dosyaları Sunucuya Yükle
**Ücretsiz hosting için [Railway.app](https://railway.app) önerilir:**
1. [railway.app](https://railway.app) adresine gidin, GitHub ile ücretsiz hesap açın
2. "New Project" → "Deploy from GitHub repo" seçin
3. Bu klasörü GitHub'a yükleyin, Railway'e bağlayın

### 3. Environment Variable Ekle
Railway dashboard'unda:
- `BOT_TOKEN` = BotFather'dan aldığınız token

### 4. Playwright Kurulumu (Railway otomatik yapar)
Eğer local çalıştırıyorsanız:
```bash
pip install -r requirements.txt
playwright install chromium
python bot.py
```

---

## 📋 Komutlar

| Komut | Açıklama |
|-------|----------|
| `/start` | Ana menüyü aç |
| `/add` | Yeni uçuş ekle |
| `/flights` | Uçuşlarımı gör |
| `/cancel` | İşlemi iptal et |
| `/help` | Yardım |

---

## ✈️ Desteklenen Havayolları

- Pegasus
- THY (Turkish Airlines)
- SunExpress
- AnadoluJet

---

## ⚠️ Önemli Notlar

- Havayolları CAPTCHA kullanıyorsa check-in başarısız olabilir
- Bu durumda kullanıcıya bildirim gönderilir
- Bazı havayolları check-in için ek doğrulama isteyebilir
- Kişisel verileri güvenli saklayın (production'da şifreleme ekleyin)

---

## 🛠️ Yeni Havayolu Ekleme

`checkin.py` dosyasına yeni bir fonksiyon ekleyin:
```python
async def _checkin_yeni_havayolu(self, pnr: str, lastname: str) -> dict:
    # Havayolunun check-in sayfasına git
    # Formu doldur
    # Sonucu döndür
```
`config.py` içindeki `SUPPORTED_AIRLINES` listesine ekleyin.

---

## 📞 Destek

Sorun yaşarsanız GitHub Issues açın.

# GİB e-Defter & Berat XML Doğrulama Aracı 📑⚖️

[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: GİB e-Defter](https://img.shields.io/badge/Standart-G%C4%B0B%20e--Defter%20XSD-red.svg)](https://edefter.gov.tr)

Gelir İdaresi Başkanlığı (**GİB**) e-Defter sistemine berat yüklerken yaşanan en yaygın krizlerden biri:

> **"Şema Kontrolü Başarısız Oldu (Schema Validation Error)"**  
> **"Borç ve Alacak Tutarları Eşit Değil!"**  
> veya  
> **"Geçersiz XML Sözdizimi / İmza Doğrulanamadı"**

hataları nedeniyle beratın reddedilmesidir. Ayın son günü berat gönderen şirketler için bu durum vergi usulsüzlük cezalarıyla sonuçlanabilir.

Bu açık kaynaklı Python aracı; muhasebe programınızdan üretilen **Yevmiye Defteri**, **Defter-i Kebir** ve **Berat XML** dosyalarını GİB portalına yüklemeden önce saniyeler içinde tarar, tutar dengesini (balans) ve zorunlu alanları doğrular.

---

## 🔍 Neleri Denetler?

1. **Borç / Alacak Balans Kontrolü:** Toplam borç ile toplam alacak tutarının birebir kuruşu kuruşuna eşit olup olmadığını denetler (GİB reddinin 1 numaralı sebebi).
2. **VKN / TCKN Denetimi:** 10 haneli Vergi Kimlik No veya 11 haneli T.C. Kimlik Numarasının varlığını ve biçimini inceler.
3. **Mali Mühür / Dijital İmza Varlığı:** Dosyada `<ds:Signature>` imza blokunun yer alıp almadığını kontrol eder.
4. **XML Sözdizimi:** Bozuk etiketleri ve eksik kapanışları raporlar.

---

## 🚀 Hızlı Kullanım

### Komut Satırından Çalıştırma
```bash
python validate_edefter_xml.py 1234567890-202601-Y-000001.xml
```

**Örnek Çıktı (Başarılı):**
```text
================================================================================
        GİB e-DEFTER & BERAT XML DOĞRULAMA RAPORU v1.0
================================================================================
Dosya Adı:       1234567890-202601-YB-000001.xml
Dosya Türü:      e-Defter Beratı (Yevmiye/Kebir)
VKN/TCKN:        1234567890
İmza Durumu:     ✅ İmzalanmış (<Signature> Mevcut)
Genel Sonuç:     ✅ GEÇERLİ - GİB YÜKLEMESİNE UYGUN

Toplam Borç:     1,450,230.50 TL
Toplam Alacak:   1,450,230.50 TL
Borç/Alacak Fark: 0.00 TL (✅ DENGELİ (0.00 TL))
```

**Örnek Çıktı (Hatalı / Dengesiz):**
```text
🚨 KRİTİK HATALAR:
  - KRİTİK HATA: Borç ve Alacak tutarları eşit değil! (Fark: 150.00 TL). GİB bu beratı kesinlikle reddedecektir!
```

### JSON Formatında Çıktı Alma (Yazılım Entegrasyonları İçin)
```bash
python validate_edefter_xml.py berat.xml --json
```

### Toplu XML Taraması (Klasör Modu)
Bir klasördeki tüm Yevmiye, Kebir ve Berat dosyalarını tek seferde taramak için:
```bash
# Klasördeki tüm XML dosyalarını denetle
python validate_edefter_xml.py --dir ./edefter_arsiv/

# Raporu JSON dosyasına kaydet
python validate_edefter_xml.py --dir ./edefter_arsiv/ --output berat_raporu.json

# Hatalı/dengesiz berat varsa CI/CD veya script'te hata kodu (exit 1) üret
python validate_edefter_xml.py berat.xml --strict
```


---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.


### 📚 İlgili Rehber ve Çözümler
* 📄 [e-Defter Berat Yükleme Gününde Mali Mühür Çalışmazsa Ne Yapılır?](https://mali-muhur-merkezi.pages.dev/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html)
* 📄 [Mali Mühür ile Bireysel E-İmza Arasındaki 3 Temel Fark](https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-ve-e-imza-arasindaki-farklar.html)
* 📄 [e-Fatura ile e-Arşiv Fatura Arasındaki Fark Nedir?](https://efatura-atolyesi.pages.dev/yazilar/e-fatura-ve-e-arsiv-arasindaki-farklar.html)

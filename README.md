# GİB e-Defter ve Berat XML Doğrulayıcı 📊🛡️

[![Python CI](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/gib-edefter-berat-xml-dogrulayici/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: GİB e-Defter](https://img.shields.io/badge/Standart-G%C4%B0B%20e--Defter-success.svg)](https://edefter.gov.tr)
[![Blog](https://img.shields.io/badge/Rehber-Mali%20M%C3%BCh%C3%BCr%20Merkezi-purple.svg)](https://mali-muhur-merkezi.pages.dev/)

Gelir İdaresi Başkanlığı (GİB) e-Defter standartlarına göre hazırlanan **Yevmiye Defteri, Defter-i Kebir ve Berat XML** dosyalarını GİB portalına yüklemeden önce denetleyen; Borç-Alacak dengesini (Balans), GİB isimlendirme formatını, dijital imza ve özet (hash) bütünlüğünü kontrol eden açık kaynaklı Python aracıdır.

---

## ✨ Öne Çıkan Özellikler

* ⚡ **Sıfır Bağımlılık (Zero-Dependency):** Ek kütüphane veya Java yüklemesi gerekmez. Saf Python ile çalışır.
* ⚖️ **Kuruş Hassasiyetinde Balans Kontrolü:** Toplam Borç ve Toplam Alacak tutarlarını karşılaştırır, GİB'in reddedeceği dengesizlikleri yüklemeden önce bildirir.
* 📛 **GİB İsimlendirme Şablonu Denetimi:** `VKN-YYYYMM-Y-000000.xml` ve `VKN-YYYYMM-YB-000000.xml` kurallarını denetler.
* 🔐 **Özet (Hash) Doğrulama:** `--verify-hash` parametresi ile berat içindeki `DigestValue`'nun defter dosyasıyla tam eşleştiğini doğrular.
* 🔏 **Mali Mühür İmza Kontrolü:** Belgede `<ds:Signature>` bloğunun bulunup bulunmadığını denetler.
* 📊 **Çoklu Rapor Formatı:** Terminal renkli çıktı, JSON, CSV ve Markdown tablo desteği.

---

## 🚀 Hızlı Başlangıç

### 1. Tekil Dosya İnceleme
```bash
python validate_edefter_xml.py 1234567890-202601-YB-000000.xml
```

### 2. Berat ile Defterin Özet (Hash) Doğrulaması
```bash
python validate_edefter_xml.py berat.xml --verify-hash yevmiye_defteri.xml
```

### 3. Klasördeki Tüm Dosyaları Toplu Tarama ve CSV Alma
```bash
python validate_edefter_xml.py --dir ./2026_01_beratlar/ --csv rapor.csv
```

---

## 🐍 Python Projelerinde Kullanım

```python
from validate_edefter_xml import validate_edefter_file

sonuc = validate_edefter_file("berat.xml")

if sonuc["valid"]:
    print(f"✅ GİB Yüklemesine Uygun! VKN: {sonuc['meta']['vkn_tckn']}")
    print(f"Borç/Alacak Farkı: {sonuc['meta']['fark']} TL")
else:
    print("❌ Hatalar bulundu:")
    for err in sonuc["errors"]:
        print(f" - {err}")
```

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* ⏱️ **[mali-muhur-eimza-suresi-kontrol](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol):** e-Defter imzalamada kritik Mali Mühür sertifika süresi denetleyici.
* 🧾 **[e-fatura-xml-goruntuleyici](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici):** GİB UBL-TR e-Fatura, e-Arşiv ve e-İrsaliye görüntüleyici.
* 🔧 **[gib-java-guvenlik-cozucu](https://github.com/eimza-kep/gib-java-guvenlik-cozucu):** GİB portalları için Java güvenlik ve istisna yapılandırıcı.

---

## 📚 İlgili Teknik Rehberler
* 📄 [e-Defter Berat Yükleme Günü Mali Mühür Çalışmazsa Acil Eylem Planı](https://mali-muhur-merkezi.pages.dev/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html)
* 📄 [e-Defterde İkincil Kopya Saklama Zorunluluğu ve GİB Zaman Damgası](https://edonusum-kobi.pages.dev/yazilar/e-defter-ikincil-kopya-saklama-zorunlulugu.html)
* 📄 [Mali Mühür Bloke Olduğunda PUK Kodu ile Kilit Nasıl Açılır?](https://mali-muhur-merkezi.pages.dev/yazilar/mali-muhur-pin-bloke-puk-kodu-cozum.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

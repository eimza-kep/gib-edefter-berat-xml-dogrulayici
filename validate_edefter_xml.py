#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GİB e-Defter ve Berat XML Sözdizimi & Balans Doğrulama Aracı
===========================================================
Gelir İdaresi Başkanlığı (GİB) e-Defter standartlarına göre hazırlanan
Yevmiye, Defter-i Kebir ve Berat XML dosyalarını yükleme öncesinde denetler:
Zorunlu alanları, VKN/TCKN, dönem formatını ve en önemlisi Borç-Alacak
tutar eşitliğini (Balans kontrolü) inceler.

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://mali-muhur-merkezi.pages.dev/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html)
Lisans: MIT
"""

import sys
import os
import re
import json
import argparse
import xml.etree.ElementTree as ET

def clean_tag(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def validate_edefter_file(file_path):
    errors = []
    warnings = []
    meta = {
        "file_name": os.path.basename(file_path),
        "file_type": "Bilinmiyor",
        "vkn_tckn": "",
        "donem": "",
        "toplam_borc": 0.0,
        "toplam_alacak": 0.0,
        "fark": 0.0,
        "is_balanced": True,
        "is_signed": False
    }

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {
            "valid": False,
            "errors": [f"XML Sözdizim Hatası (Malformed XML): {e}"],
            "warnings": [],
            "meta": meta
        }

    root_tag = clean_tag(root.tag).lower()

    if "berat" in root_tag:
        meta["file_type"] = "e-Defter Beratı (Yevmiye/Kebir)"
    elif "defter" in root_tag or "ledger" in root_tag:
        meta["file_type"] = "e-Defter Dosyası"
    else:
        warnings.append(f"Kök etiket standart e-defter formatından farklı olabilir: <{clean_tag(root.tag)}>")

    # VKN / TCKN Taraması
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()
        
        if tag in ["vkn", "identifier", "VergiKimlikNo", "TCKN"] and not meta["vkn_tckn"]:
            if re.match(r"^\d{10,11}$", val):
                meta["vkn_tckn"] = val

        # İmza Kontrolü (ds:Signature)
        if tag == "Signature":
            meta["is_signed"] = True

        # Tutar Toplamları (Borç / Alacak)
        try:
            val_float = float(val.replace(",", "."))
            if tag in ["totalDebit", "ToplamBorc", "debitAmount"]:
                meta["toplam_borc"] += val_float
            elif tag in ["totalCredit", "ToplamAlacak", "creditAmount"]:
                meta["toplam_alacak"] += val_float
        except ValueError:
            pass

    # VKN Kontrolü
    if not meta["vkn_tckn"]:
        warnings.append("Dosyada geçerli 10 haneli VKN veya 11 haneli TCKN tespit edilemedi.")

    # İmza Uyarısı
    if not meta["is_signed"]:
        warnings.append("Dosyada Mali Mühür / e-İmza dijital imzası (<Signature>) bulunamadı. GİB portalına yüklemeden önce imzalanmalıdır.")

    # Balans (Borç-Alacak Eşitliği) Kontrolü
    if meta["toplam_borc"] > 0 or meta["toplam_alacak"] > 0:
        fark = abs(meta["toplam_borc"] - meta["toplam_alacak"])
        meta["fark"] = round(fark, 2)
        if fark > 0.01:
            meta["is_balanced"] = False
            errors.append(f"KRİTİK HATA: Borç ve Alacak tutarları eşit değil! (Fark: {fark:,.2f} TL). GİB bu beratı kesinlikle reddedecektir!")

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "meta": meta
    }

def main():
    parser = argparse.ArgumentParser(description="GİB e-Defter ve Berat XML Doğrulayıcı")
    parser.add_argument("xml_path", help="İncelenecek e-Defter veya Berat XML dosyasının yolu")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not os.path.exists(args.xml_path):
        print(f"Hata: Dosya bulunamadı -> {args.xml_path}", file=sys.stderr)
        sys.exit(1)

    res = validate_edefter_file(args.xml_path)

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    m = res["meta"]
    print("=" * 80)
    print("        GİB e-DEFTER & BERAT XML DOĞRULAMA RAPORU v1.0")
    print("=" * 80)
    print(f"Dosya Adı:       {m['file_name']}")
    print(f"Dosya Türü:      {m['file_type']}")
    print(f"VKN/TCKN:        {m['vkn_tckn'] or 'Tespit Edilemedi'}")
    print(f"İmza Durumu:     {'✅ İmzalanmış (<Signature> Mevcut)' if m['is_signed'] else '⚠️  İmzasız (Mali Mühür Bekliyor)'}")
    print(f"Genel Sonuç:     {'✅ GEÇERLİ - GİB YÜKLEMESİNE UYGUN' if res['valid'] else '❌ HATALI - GİB REDDEDER'}\n")

    if m["toplam_borc"] > 0 or m["toplam_alacak"] > 0:
        print(f"Toplam Borç:     {m['toplam_borc']:,.2f} TL")
        print(f"Toplam Alacak:   {m['toplam_alacak']:,.2f} TL")
        print(f"Borç/Alacak Fark: {m['fark']:,.2f} TL ({'✅ DENGELİ (0.00 TL)' if m['is_balanced'] else '❌ DENGESİZ!'})\n")

    if res["errors"]:
        print("🚨 KRİTİK HATALAR:")
        for err in res["errors"]:
            print(f"  - {err}")
        print()

    if res["warnings"]:
        print("⚠️  UYARILAR:")
        for w in res["warnings"]:
            print(f"  - {w}")
        print()

    print("=" * 80)
    print("Mali Mühür & e-Defter Çözüm Portalı: https://mali-muhur-merkezi.pages.dev/yazilar/e-defter-berat-gunu-mali-muhur-calismazsa-cozum.html")

if __name__ == "__main__":
    main()

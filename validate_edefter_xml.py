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

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def clean_tag(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def validate_edefter_file(file_path):
    errors = []
    warnings = []
    meta = {
        "file_name": os.path.basename(file_path),
        "file_path": os.path.abspath(file_path),
        "file_size_bytes": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        "file_type": "Bilinmiyor",
        "vkn_tckn": "",
        "donem": "",
        "digest_method": "",
        "digest_value": "",
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

    start_date = ""
    end_date = ""

    # VKN / TCKN, Tutar ve Digest Taraması
    for elem in root.iter():
        tag = clean_tag(elem.tag)
        val = (elem.text or "").strip()
        
        if tag in ["vkn", "identifier", "VergiKimlikNo", "TCKN"] and not meta["vkn_tckn"]:
            if re.match(r"^\d{10,11}$", val):
                meta["vkn_tckn"] = val

        # İmza Kontrolü (ds:Signature)
        if tag == "Signature":
            meta["is_signed"] = True

        # Digest Method & Value
        if tag == "DigestMethod":
            meta["digest_method"] = elem.attrib.get("Algorithm", "").split("#")[-1] or "Bilinmiyor"
        if tag == "DigestValue" and not meta["digest_value"]:
            meta["digest_value"] = val

        # Dönem Bilgisi
        if tag in ["startDate", "periodStart"] and not start_date:
            start_date = val
        if tag in ["endDate", "periodEnd"] and not end_date:
            end_date = val

        # Tutar Toplamları (Borç / Alacak)
        try:
            val_float = float(val.replace(",", "."))
            if tag in ["totalDebit", "ToplamBorc", "debitAmount"]:
                meta["toplam_borc"] += val_float
            elif tag in ["totalCredit", "ToplamAlacak", "creditAmount"]:
                meta["toplam_alacak"] += val_float
        except ValueError:
            pass

    if start_date and end_date:
        meta["donem"] = f"{start_date} - {end_date}"

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

def print_result_cli(res):
    m = res["meta"]
    print("=" * 80)
    print("        GİB e-DEFTER & BERAT XML DOĞRULAMA RAPORU v1.1")
    print("=" * 80)
    print(f"Dosya Adı:       {m['file_name']}")
    print(f"Dosya Türü:      {m['file_type']}")
    print(f"VKN/TCKN:        {m['vkn_tckn'] or 'Tespit Edilemedi'}")
    if m["donem"]:
        print(f"Dönem:           {m['donem']}")
    if m["digest_value"]:
        print(f"Dosya Özeti:     {m['digest_method']} -> {m['digest_value']}")
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

def main():
    parser = argparse.ArgumentParser(description="GİB e-Defter ve Berat XML Doğrulayıcı")
    parser.add_argument("xml_path", nargs="?", default=None, help="İncelenecek e-Defter veya Berat XML dosyasının yolu")
    parser.add_argument("--dir", help="Belirtilen dizindeki tüm XML dosyalarını toplu inceleme")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    parser.add_argument("--output", help="Raporu belirtilen JSON dosyasına kaydeder")
    parser.add_argument("--strict", action="store_true", help="Hatalı dosya varsa 1 çıkış kodu döndürür")

    args = parser.parse_args()

    if not args.xml_path and not args.dir:
        parser.print_help()
        sys.exit(0)

    if args.dir:
        if not os.path.isdir(args.dir):
            print(f"Hata: Dizin bulunamadı -> {args.dir}", file=sys.stderr)
            sys.exit(1)
        xml_files = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.lower().endswith(".xml")]
        batch_results = []
        any_invalid = False
        for xf in sorted(xml_files):
            r = validate_edefter_file(xf)
            if not r["valid"]:
                any_invalid = True
            batch_results.append(r)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(batch_results, f, ensure_ascii=False, indent=2)
            print(f"[OK] Toplu rapor dosyaya aktarıldı: {args.output}")
        elif args.json:
            print(json.dumps(batch_results, ensure_ascii=False, indent=2))
        else:
            print(f"Toplam {len(batch_results)} adet e-Defter XML dosyası tarandı:")
            for r in batch_results:
                icon = "✅" if r["valid"] else "❌"
                m = r["meta"]
                balans_txt = "DENGELİ" if m["is_balanced"] else "DENGESİZ!"
                print(f"  {icon} {m['file_name']:<35} | {m['file_type']:<28} | VKN: {m['vkn_tckn'] or 'N/A':<11} | Balans: {balans_txt}")

        if args.strict and any_invalid:
            sys.exit(1)
        return

    if not os.path.exists(args.xml_path):
        print(f"Hata: Dosya bulunamadı -> {args.xml_path}", file=sys.stderr)
        sys.exit(1)

    res = validate_edefter_file(args.xml_path)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        print(f"[OK] Rapor dosyaya aktarıldı: {args.output}")
    elif args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print_result_cli(res)

    if args.strict and not res["valid"]:
        sys.exit(1)

if __name__ == "__main__":
    main()


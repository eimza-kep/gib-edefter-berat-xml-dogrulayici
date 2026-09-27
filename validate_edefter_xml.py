#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GİB e-Defter ve Berat XML Sözdizimi, Dosya Adı & Balans Doğrulama Aracı v1.2
===========================================================================
Gelir İdaresi Başkanlığı (GİB) e-Defter standartlarına göre hazırlanan
Yevmiye, Defter-i Kebir ve Berat XML dosyalarını yükleme öncesinde denetler:
Zorunlu alanları, VKN/TCKN, dönem formatını, GİB dosya adlandırma standartlarını,
özet (hash) eşleşmesini ve Borç-Alacak tutar eşitliğini (Balans) inceler.

Özellikler:
- Sıfır bağımlılık (Pure Python Standard Library)
- GİB standart dosya adı kontrolü (VKN-YYYYMM-Y/K/YB/KB formatı)
- Berat içi DigestValue ile defter dosyasının SHA özetini doğrulama (--verify-hash)
- Borç - Alacak kuruş farkı hassasiyetinde balans kontrolü
- CSV, JSON ve Markdown formatında denetim raporu
- Toplu klasör tarama (--dir) ve CI denetimi (--strict)

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://mali-muhur-merkezi.pages.dev/)
Lisans: MIT
"""

import sys
import os
import re
import csv
import json
import hashlib
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

def check_gib_filename_format(filename):
    """
    GİB e-Defter dosya adı formatını denetler:
    Örn: 1234567890-202601-Y-000000.xml veya 1234567890-202601-YB-000000.xml
    """
    pattern = r"^(\d{10,11})-(\d{6})-(Y|K|YB|KB)-(\d{6})\.xml$"
    m = re.match(pattern, filename, re.IGNORECASE)
    if m:
        vkn, donem, tip, no = m.groups()
        tip_map = {
            "Y": "Yevmiye Defteri",
            "K": "Defter-i Kebir",
            "YB": "Yevmiye Beratı",
            "KB": "Kebir Beratı"
        }
        return True, {
            "vkn": vkn,
            "donem": f"{donem[:4]}/{donem[4:]}",
            "tur": tip_map.get(tip.upper(), tip),
            "parca_no": no
        }
    return False, None

def validate_edefter_file(file_path, referenced_defter_path=None):
    errors = []
    warnings = []
    fname = os.path.basename(file_path)
    
    meta = {
        "file_name": fname,
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
        "is_signed": False,
        "filename_conforms_gib": False,
        "hash_verified": None
    }

    # Dosya adı GİB formatı denetimi
    fn_valid, fn_info = check_gib_filename_format(fname)
    meta["filename_conforms_gib"] = fn_valid
    if not fn_valid:
        warnings.append(f"Dosya adı '{fname}' GİB e-Defter isimlendirme şablonuna (VKN-YYYYMM-TUR-NO.xml) uymuyor.")
    else:
        meta["file_type"] = fn_info["tur"]

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {
            "valid": False,
            "errors": [f"XML Sözdizim Hatası (Malformed XML): {e}"],
            "warnings": warnings,
            "meta": meta
        }

    root_tag = clean_tag(root.tag).lower()

    if "berat" in root_tag:
        meta["file_type"] = "e-Defter Beratı (Yevmiye/Kebir)"
    elif "defter" in root_tag or "ledger" in root_tag:
        meta["file_type"] = "e-Defter Dosyası"

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

    # İlgili defter dosyasının özet doğrulaması (--verify-hash)
    if referenced_defter_path and os.path.exists(referenced_defter_path):
        with open(referenced_defter_path, "rb") as df:
            df_bytes = df.read()
        
        algo = meta["digest_method"].lower()
        if "sha256" in algo:
            calc_hash = hashlib.sha256(df_bytes).digest()
        elif "sha1" in algo:
            calc_hash = hashlib.sha1(df_bytes).digest()
        else:
            calc_hash = hashlib.sha256(df_bytes).digest()
        
        import base64
        calc_b64 = base64.b64encode(calc_hash).decode("ascii")
        if meta["digest_value"] == calc_b64:
            meta["hash_verified"] = True
        else:
            meta["hash_verified"] = False
            errors.append(f"KRİTİK HATA: Berat içindeki DigestValue ({meta['digest_value']}) ile defter dosyasının hesaplanan özeti ({calc_b64}) UYUŞMUYOR!")

    is_valid = len(errors) == 0

    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "meta": meta
    }

def generate_markdown_report(results):
    md = "# GİB e-Defter ve Berat XML Doğrulama Raporu\n\n"
    md += f"Toplam **{len(results)}** adet e-Defter dosyası denetlendi.\n\n"
    md += "| Durum | Dosya Adı | Tür | VKN/TCKN | Balans Durumu | İmza |\n"
    md += "|:---:|---|---|---|:---:|:---:|\n"
    for r in results:
        m = r["meta"]
        st = "✅ Geçerli" if r["valid"] else "❌ Hatalı"
        balans = "Dengeli (0.00 TL)" if m["is_balanced"] else f"Fark: {m['fark']:,.2f} TL"
        sig = "İmzalı" if m["is_signed"] else "İmzasız"
        md += f"| {st} | `{m['file_name']}` | {m['file_type']} | {m['vkn_tckn'] or '-'} | {balans} | {sig} |\n"
    
    md += "\n---\n"
    md += "💡 **Mevzuat Notu:** GİB e-Defter uygulamasında Yevmiye ve Kebir beratlarının Borç-Alacak dengesi tam eşit olmak zorundadır.\n"
    return md

def print_result_cli(res):
    m = res["meta"]
    print("=" * 80)
    print("     GİB e-DEFTER & BERAT XML DOĞRULAMA RAPORU v1.2")
    print("=" * 80)
    print(f"Dosya Adı:       {m['file_name']}")
    print(f"Dosya Türü:      {m['file_type']}")
    print(f"GİB Ad Formatı:  {'✅ Standart İsimlendirme' if m['filename_conforms_gib'] else '⚠️ Standart Dışı İsim'}")
    print(f"VKN/TCKN:        {m['vkn_tckn'] or 'Tespit Edilemedi'}")
    if m["donem"]:
        print(f"Dönem:           {m['donem']}")
    if m["digest_value"]:
        print(f"Dosya Özeti:     {m['digest_method']} -> {m['digest_value']}")
    if m["hash_verified"] is not None:
        print(f"Defter Özeti:    {'✅ ÖZET DOĞRULANDI (Dosya Değişmemiş)' if m['hash_verified'] else '❌ ÖZET UYUŞMAZLIĞI (Dosya Bozulmuş/Değişmiş!)'}")
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
    parser = argparse.ArgumentParser(description="GİB e-Defter ve Berat XML Doğrulayıcı v1.2")
    parser.add_argument("xml_path", nargs="?", default=None, help="İncelenecek e-Defter veya Berat XML dosyasının yolu")
    parser.add_argument("--dir", help="Belirtilen dizindeki tüm XML dosyalarını toplu inceleme")
    parser.add_argument("--verify-hash", help="Beratta belirtilen özet değerini karşılaştırmak için ilgili defter XML dosyası")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    parser.add_argument("--markdown", action="store_true", help="Sonucu Markdown tablosu olarak verir")
    parser.add_argument("--csv", help="Sonuçları belirtilen CSV dosyasına kaydeder")
    parser.add_argument("--output", help="Raporu belirtilen JSON/Markdown dosyasına kaydeder")
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

        if args.csv:
            with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Dosya", "Gecerli", "Tur", "VKN", "Borc", "Alacak", "Fark", "Imzali", "Hatalar"])
                for b in batch_results:
                    m = b["meta"]
                    writer.writerow([m["file_name"], "EVET" if b["valid"] else "HAYIR", m["file_type"], m["vkn_tckn"], m["toplam_borc"], m["toplam_alacak"], m["fark"], "EVET" if m["is_signed"] else "HAYIR", " | ".join(b["errors"])])
            print(f"[OK] CSV raporu kaydedildi: {args.csv}")
            return
        elif args.markdown:
            md_text = generate_markdown_report(batch_results)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(md_text)
                print(f"[OK] Markdown raporu kaydedildi: {args.output}")
            else:
                print(md_text)
            return
        elif args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(batch_results, f, ensure_ascii=False, indent=2)
            print(f"[OK] Toplu rapor dosyaya aktarıldı: {args.output}")
            return
        elif args.json:
            print(json.dumps(batch_results, ensure_ascii=False, indent=2))
            return
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

    res = validate_edefter_file(args.xml_path, referenced_defter_path=args.verify_hash)

    if args.markdown:
        md_text = generate_markdown_report([res])
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md_text)
            print(f"[OK] Markdown raporu kaydedildi: {args.output}")
        else:
            print(md_text)
    elif args.output:
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

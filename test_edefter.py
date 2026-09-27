# -*- coding: utf-8 -*-
"""Unit tests for GİB e-Defter and Berat XML Validator v1.2"""
import os
import unittest
from validate_edefter_xml import validate_edefter_file, check_gib_filename_format, generate_markdown_report

class TestEDefterValidator(unittest.TestCase):
    def setUp(self):
        self.sample_berat = os.path.join(os.path.dirname(__file__), "ornek_berat.xml")

    def test_filename_check(self):
        valid, info = check_gib_filename_format("1234567890-202601-YB-000000.xml")
        self.assertTrue(valid)
        self.assertEqual(info["vkn"], "1234567890")
        self.assertEqual(info["tur"], "Yevmiye Beratı")

        valid_k, info_k = check_gib_filename_format("9876543210-202602-K-000001.xml")
        self.assertTrue(valid_k)
        self.assertEqual(info_k["tur"], "Defter-i Kebir")

        invalid, _ = check_gib_filename_format("rastgele_dosya.xml")
        self.assertFalse(invalid)

    def test_validate_berat(self):
        res = validate_edefter_file(self.sample_berat)
        self.assertTrue(res["valid"])
        self.assertIn("Berat", res["meta"]["file_type"])
        self.assertEqual(res["meta"]["vkn_tckn"], "1234567890")
        self.assertTrue(res["meta"]["is_signed"])

    def test_unbalanced_defter(self):
        dummy_defter = os.path.join(os.path.dirname(__file__), "temp_unbalanced.xml")
        try:
            with open(dummy_defter, "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="UTF-8"?>
<defter>
  <identifier>1234567890</identifier>
  <totalDebit>5000.00</totalDebit>
  <totalCredit>4500.00</totalCredit>
</defter>""")
            res = validate_edefter_file(dummy_defter)
            self.assertFalse(res["valid"])
            self.assertFalse(res["meta"]["is_balanced"])
            self.assertAlmostEqual(res["meta"]["fark"], 500.00)
            self.assertTrue(any("eşit değil" in err.lower() for err in res["errors"]))

            md = generate_markdown_report([res])
            self.assertIn("Hatalı", md)
        finally:
            if os.path.exists(dummy_defter):
                os.remove(dummy_defter)

if __name__ == "__main__":
    unittest.main()

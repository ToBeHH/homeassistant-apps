import unittest

from okmcp.places import format_hits


class FormatTest(unittest.TestCase):
    def test_hits(self):
        text = format_hits("elb", [
            {"name": "Elbphilharmonie", "kind": "attraction", "near": "Hamburg", "country": "DE",
             "lat": 53.5413, "lon": 9.98413},
            {"name": "Elbe", "kind": "water", "near": "", "country": "", "lat": 53.9, "lon": 9.0},
        ])
        self.assertIn("- Elbphilharmonie (attraction, Hamburg, DE): 53.54130, 9.98413", text)
        self.assertIn("- Elbe (water): 53.90000, 9.00000", text)

    def test_none(self):
        self.assertIn("No place found", format_hits("x", []))


if __name__ == "__main__":
    unittest.main()

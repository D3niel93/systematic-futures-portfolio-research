import unittest
import pandas as pd
from robustness import day_block_intervals

class RobustnessChecks(unittest.TestCase):
    def test_reproducible_conditional_samples(self):
        ledger=pd.DataFrame(dict(time=pd.bdate_range('2025-01-01',periods=20),
            pnl=[10,-5]*10,quantity=[1]*20))
        a=day_block_intervals(ledger,iterations=20)
        b=day_block_intervals(ledger,iterations=20)
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(list(a.block_days),[5,10,20])
        self.assertTrue((a.iterations==20).all())

    def test_invalid_pnl_rejected(self):
        ledger=pd.DataFrame(dict(time=['2025-01-01'],pnl=[float('nan')],quantity=[1]))
        with self.assertRaises(ValueError):day_block_intervals(ledger,iterations=2)

import random

from src.retrieval.significance import holm, paired_bootstrap, sign_flip_p


def test_holm_keeps_order_and_is_monotone():
    adj = holm([0.04, 0.01, 0.03])
    assert adj == [0.06, 0.03, 0.06]


def test_constant_diff_gives_tight_ci_and_small_p():
    diffs = [0.5] * 30
    lo, hi = paired_bootstrap(diffs, 500, random.Random(0))
    assert lo == hi == 0.5
    assert sign_flip_p(diffs, 500, random.Random(0)) < 0.01


def test_zero_diff_is_not_significant():
    assert sign_flip_p([0.0] * 20, 200, random.Random(0)) == 1.0

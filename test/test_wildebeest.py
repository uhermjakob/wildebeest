"""
Written by Ulf Hermjakob, USC/ISI
Pytest for wildebeest.py
"""
# -*- encoding: utf-8 -*-
import wildebeest as wb
import logging as log

log.basicConfig(level=log.INFO)

__version__ = '0.2'
last_mod_date = 'September 23, 2020'


def test_indic_diacritics():
    s = 'बड़े टुकड़े गाज़ा क़ख़ग़ज़ड़ढ़फ़य़ क़ख़ग़ज़ड़ढ़फ़य़ ऩऱऴ  ऩऱऴ टुकडे़ बडे़'
    norm_s = wb.normalize_indic_diacritics(s)
    ref_norm_s = 'बड़े टुकड़े गाज़ा क़ख़ग़ज़ड़ढ़फ़य़ क़ख़ग़ज़ड़ढ़फ़य़ ऩऱऴ  ऩऱऴ टुकड़े बड़े'
    assert norm_s == ref_norm_s


def test_indic_numbers():
    s = '₹९० ₹൯൦'
    norm_s = wb.map_digits_to_ascii(s)
    ref_norm_s = '₹90 ₹90'
    assert norm_s == ref_norm_s

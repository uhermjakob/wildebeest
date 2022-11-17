__version__ = '0.9.0'
__description__ = '''This wildebeest script repairs common encoding errors, normalizes characters into their canonical form, maps digits and some punctuation to ASCII, deletes many non-printable characters and performs other repair, normalization and cleaning steps.'''
last_mod_date = 'November 17, 2022'
from . import wb_normalize, wb_analysis
__all__ = [wb_normalize, wb_analysis]

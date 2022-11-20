__version__ = '0.9.2'
__description__ = '''The wildebeest scripts investigate, repair and normalize a wide range of text file problems at the character level, e.g. encoding errors, normalization of characters into their canonical form, mapping digits and some punctuation to ASCII, deletion of some non-printable characters.'''
last_mod_date = 'November 19, 2022'
from . import wb_normalize, wb_analysis
__all__ = [wb_normalize, wb_analysis]

r"""Wildebeest documentation: https://github.com/uhermjakob/wildebeest
Main modules: wildebeest.wb_analysis, wildebeest.wb_normalize
Argument help: wb_analysis.py -h, wb_normalize.py -h; or, alternatively: wb-ana -h, wb-norm -h"""
__version__ = '0.9.2'
__description__ = '''The wildebeest scripts investigate, repair and normalize a wide range of text file problems at the character level, e.g. encoding errors, normalization of characters into their canonical form, mapping digits and some punctuation to ASCII, deletion of some non-printable characters.'''
last_mod_date = 'November 19, 2022'
from . import wb_normalize, wb_analysis
__all__ = [wb_normalize, wb_analysis]

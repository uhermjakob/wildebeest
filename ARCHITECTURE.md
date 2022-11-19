# Wildebeest Architecture

## wb_analysis.pl

An initial overview.
See also the usage examples in README.md

#### Input

Text
* for CLI typcially as a file, or a batch directory of files (*.txt)
* for a python function call ("process") as a string, a list of strings, or an input filename.

#### Algorithm

In phase 1, functions collect_counts_and_examples_in_file/collect_counts_and_examples_in_line iterate over the text, collecting counts of characters and tokens of interest.
In phase 2, function aggregate aggregates these raw counts into an analysis dictionary.
The resulting wb.analysis directory can be dumped as a json file or output using a pretty_print method.

#### Output

The result analysis for an object wb of type Wildebeest will be stored in dictionary wb.analysis

Example:
```
wb.analysis['n_lines']          # type: int
wb.analysis['n_characters']	# type: int
wb.analysis['letter-script']    # type: dict, records scripts that letters are written in
wb.analysis['letter-script']['LATIN']['count']
wb.analysis['letter-script']['GREEK']['ex']    # string of characters
wb.analysis['number-script']    # type: dict, records scripts that numbers are written in
wb.analysis['number-script']['KANNADA']['count']
wb.analysis['number-script']['KANNADA']['ex']
wb.analysis['other-script']     # type: dict, records scripts and blocks that other characters are written in
wb.analysis['other-script']['ASCII_PUNCTUATION']['!']['char']
wb.analysis['other-script']['ASCII_PUNCTUATION']['!']['id']      # Unicode, e.g. 'U+0021'
wb.analysis['other-script']['ASCII_PUNCTUATION']['!']['name']    # Unicode name, e.g. 'EXCLAMATION MARK'
wb.analysis['other-script']['ASCII_PUNCTUATION']['!']['count']   # type: int
wb.analysis['other-script']['ASCII_PUNCTUATION']['!']['ex']      # examples, e.g. list of [instance, snt_id/line_number] pairs
wb.analysis['non-canonical']    # type: dict, records non-canonical characters, e.g. letter modifiers in wrong order, or letter modifiers should or should not be integrated with main character
wb.analysis['non-canonical']['é']['orig']         # é (two UTF8 characters: e + ́)
wb.analysis['non-canonical']['é']['norm']         # é (one UTF8 character)
wb.analysis['non-canonical']['é']['orig-count']
wb.analysis['non-canonical']['é']['norm-count']
wb.analysis['non-canonical']['é']['orig-form']    # NFD
wb.analysis['non-canonical']['é']['norm-form']    # NFC
wb.analysis['non-canonical']['é']['changes']      # compose
wb.analysis['char-conflict']    # type: dict, records when competing characters occur in the same text, e.g. both an Arabic and a Persian k
wb.analysis['char-conflict']['ك/ک']               # type: list
wb.analysis['char-conflict']['ك/ک'][0]['char']    # 'ك'
wb.analysis['char-conflict']['ك/ک'][0]['id']
wb.analysis['char-conflict']['ك/ک'][0]['name']    # 'ARABIC LETTER KAF'
wb.analysis['char-conflict']['ك/ک'][0]['count']
wb.analysis['char-conflict']['ك/ک'][1]['char']    # 'ک'
wb.analysis['char-conflict']['ك/ک'][1]['name']    # 'ARABIC LETTER KEHEH'
wb.analysis['notable-token']    # type: dict, records tokens with likely issues
wb.analysis['notable-token']['WORDS WITH CHARACTERS FROM MULTIPLE SCRIPTS (CYRILLIC, GREEK, LATIN)']['Hеllο']['token']
wb.analysis['notable-token']['WORDS WITH CHARACTERS FROM MULTIPLE SCRIPTS (CYRILLIC, GREEK, LATIN)']['Hеllο']['count']
wb.analysis['notable-token']['WORDS WITH CHARACTERS FROM MULTIPLE SCRIPTS (CYRILLIC, GREEK, LATIN)']['Hеllο']['ex']
wb.analysis['pattern']          # type: dict, records tokens of certain patterns, that e.g. include punctuation of interest
wb.analysis['pattern']['TOKENS WITH @ (U+0040 COMMERCIAL AT)']['Word@Word.Word']['pattern']
wb.analysis['pattern']['TOKENS WITH @ (U+0040 COMMERCIAL AT)']['Word@Word.Word']['count']
wb.analysis['pattern']['TOKENS WITH @ (U+0040 COMMERCIAL AT)']['Word@Word.Word']['ex']      # e.g. [["president@whitehouse.org", 1]]
wb.analysis['block']            # type: dict, records characters by block
wb.analysis['block']['BASIC_LATIN']['A']['char']
wb.analysis['block']['BASIC_LATIN']['A']['id']
wb.analysis['block']['BASIC_LATIN']['A']['name']
wb.analysis['block']['BASIC_LATIN']['A']['count']
wb.analysis['block']['BASIC_LATIN']['A']['ex']
wb.analysis['block']['ASCII_PUNCTUATION']['.']['count']
```


# wildebeest

## normalize.py

Script repairs common encoding errors, normalizes characters into their canonical form, maps digits and some
punctuation to ASCII, deletes many non-printable characters and performs other repair, normalization and cleaning steps.
A few steps are specific to Pashto, Farsi, or Devanagari (Hindi etc.).
The script contains a list of normalization modules as listed below. The script argument `--skip` allows users to specify
any normalization modules they want to skip.

## Usage &nbsp; (click below for details)
<details>
<summary>CLI to normalize a file: <code>python -m wildebeest</code> or its alias <code>wb-norm</code> </summary>

```
python -m wildebeest  [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [--lc LANGUAGE-CODE] [--skip NORM-STEPS] [-v] [--version]
optional arguments:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  --skip NORM-STEPS     comma-separated list of normalization/cleaning steps to be skipped: repair-encodings-errors,del-surrogate,del-
                        ctrl-char,del-arabic-diacr,del-hebrew-diacr,core-compat,pres-form,ligatures,signs-and-
                        symbols,cjk,width,font,small,vertical,enclosure,hangul,repair-combining,combining-compose,combining-
                        decompose,punct,punct-dash,punct-arabic,punct-cjk,punct-greek,punct-misc-f,space,digit,arabic-char,farsi-
                        char,pashto-char,georgian-char,look-alike,repair-xml,repair-url-escapes,repair-token (default: nothing skipped)
  -v, --verbose         write change log etc. to STDERR
  --version             show program's version number and exit
```
Example:
```
python -m wildebeest -i corpus-raw.txt -o corpus-wb.txt --lc eng --skip punct-dash,enclosure,del-arabic-diacr
```
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
Note: For robustness regarding input files that do not fully conform to UTF8, please use -i (rather than STDIN), as it includes UTF8-encoding error handling.
</details>

<details>
<summary>norm_clean_string (Python function call to normalize a string)</summary>
 
```python 
from wildebeest.normalize import Wildebeest
wb = Wildebeest()
ht = {}                             # dictionary sets/resets steps to be skipped (default: not skipped)
# ht['SKIP-punct-dash'] = 1         # optionally skip normalization of ndash, mdash etc. to ASCII hyphen-minus.
# ht['SKIP-enclosure'] = 1          # optionally skip 'enclosure' normalization
# ht['SKIP-del-arabic-diacr'] = 1   # optionally skip 'delete arabic diacritic' normalization
wb.load_look_alike_file()           # optional
print(wb.norm_clean_string('🄐…25kmÂ²', ht, lang_code='eng'))
print(wb.norm_clean_string('೧೯೨೩', ht, lang_code='kan'))
``` 
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
</details>

<details>
<summary>Installation</summary>

```bash
# from PyPi (after public release)
pip install wildebeest

# Latest master branch: either https or git/ssh 
pip install git+https://github.com/uhermjakob/wildebeest.git

# For editing/development
git clone https://github.com/uhermjakob/wildebeest.git
# or git clone git://github.com/uhermjakob/wildebeest.git
cd wildebeest
pip install --editable .   # run it from dir having setup.py
```

To call wildebeest after installation, run `python -m wildebeest` or its alias `wb-norm`. 
</details>

## List of Normalization Steps

### repair-encodings-errors
The script generally expects input encoded in UTF8. However, it will recognize and repair some common text encoding
errors:
* (Some) text is still encoded in Windows1252 or Latin1. Any byte that is not part of a well-formed UTF8 character will
 be interpreted as a Windows1252 character (and mapped to UTF8). This includes printable Latin1 characters as a subset.
* Text in Windows1252 was incorrectly converted to UTF8 by a Latin1-to-UTF8 converter. This maps Windows1252 characters
 \x80-\x9F to \u0080-\uu009F, which is the Unicode block of C1 control characters. These C1 control characters are
 extremely rare, and so our script will interpret such C1 control characters as ill-converted Windows1252 characters,
 as do many major software applications such as Google Chrome, Microsoft Outlook, Github (text files) and PyCharm 
 (where they are often displayed in a slightly different form).
* Text in Windows1252 or Latin1 was converted twice, using some combination of Latin1-to-UTF8 converter and
 Windows1252-to-UTF converter; or a file already in UTF8 was incorrectly subjected to another conversion.
 Sample *wildebeest* repair:
    * Input: Donât tell your âfiancÃ©â â SchÃ¶ne GrÃ¼Ãe aus MÃ¤hrenâ¦ â Ma sÅur trouve Ã§a Â«bÃªteÂ». Â¡CoÃ±o! â¬50 â¢ 25kmÂ² â¢ Â½Âµm
    * Output: Don’t tell your “fiancé” — Schöne Grüße aus Mähren… – Ma sœur trouve ça «bête». ¡Coño! €50 • 25km² • ½µm

### Other normalization modules
* `del-surrogate` (deletes surrogate characters (representing non-UTF8 characters in input), alternative/backup to windows-1252)
* `del-ctrl-char` (deletes control characters (expect tab and linefeed), zero-width characters, byte order mark, directional marks, join marks, variation selectors, Arabic tatweel)
* `core-compat` (normalizes Hangul Compatibility characters to Unicode standard Hangul characters)
* `arabic-char` (to Arabic canonical forms, e.g. maps Farsi kaf/yeh to Arabic versions)
* `farsi-char` (to Farsi canonical forms, e.g. maps Arabic yeh, kaf to Farsi versions)
* `pashto-char` (to Pashto canonical forms, e.g. maps Arabic kaf to Farsi version)
* `georgian-char` (to Georgian canonical forms, e.g. to standard script, map archaic characters)
* `pres-form` (e.g. maps from presentation form (isolated, initial, medial, final) to standard form)
* `ligatures` (e.g. decomposes non-Arabic ligatures (e.g. ĳ, ﬃ, Ǆ, ﬓ))
* `signs-and-symbols` (e.g. maps symbols (e.g. kappa symbol) and signs (e.g. micro sign µ))
* `cjk` (e.g. CJK square composites (e.g. ㋀㏾))
* `width` (e.g. maps fullwidth and halfwidth characters to ASCII, e.g. Ａ to A)
* `font` (maps font-variations characters such as ℂ, ℹ, 𝒜 to regular characters)
* `small` (maps small versions of characters to normal versions, such as small ampersand ﹠ to regular &)
* `vertical` (maps vertical versions of punctuation characters with normal horizontal version, such as vertical em-dash ︱ to horizontal em-dash —)
* `enclosure` (decomposes circled, squared and parenthesized characters, e.g. 🄐 to (A))
* `hangul` (combine Hangul jamos onto Hangul syllables)
* `repair-combining` (e.g. order of nukta/vowel-sign)
* `combining-compose` (e.g. applies combining-modifiers to preceding character, e.g. ö (o +  ̈) -> ö)
* `combining-decompose` (e.g. for some Indian characters, splits off Nukta)
* `del-arabic-diacr` (e.g. deletes optional Arabic diacritics such as fatha, damma, kasra)
* `del-hebrew-diacr` (e.g. deletes Hebrew points)
* `digit` (e.g. maps decimal-system digits of 54 scripts to ASCII digits)
* `punct` (e.g. maps ellipsis … to periods ... and two-dot-lead ‥ to ..; a few math symbols ∭; ⒛ 🄆 )
* `punct-dash` (e.g. maps various dashes, hyphens, minus signs to ASCII hyphen-minus)
* `punct-arabic` (e.g. Arabic exclamation mark etc. to ASCII equivalent)
* `punct-cjk` (e.g. Chinese Ideographic Full Stop etc. to ASCII equivalent)
* `punct-greek` (e.g. Greek question mark etc. to ASCII equivalent)
* `punct-misc-f` (e.g. Tibetan punctuation to ASCII equivalent)
* `space` (e.g. maps non-zero spaces to normal space)
* `look-alike` (normalizes Latin/Cyrillic/Greek look-alike characters, e.g. Latin character A to Greek Α (capital alpha) in otherwise Greek word)
* `repair-xml` (e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;)
* `repair-url-escapes` (e.g. repairs multi-escaped url substrings such as Jo%25C3%25ABlle_Aubron)
* `repair-token` (e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen)

## wb_analysis.py

Script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, zero-with characters,
letters/numbers/punctuation/letter-modifiers from various scripts,
tokens with letters from different scripts, XML tokens, tokens with certain
punctuation of interest, orphan letter modifiers, non-canonical character
combinations.

```
usage: wb_analysis.py [-h] [-i INPUT-FILENAME] [--batch BATCH] [-s] [-o OUTPUT-FILENAME] [-j JSON-OUTPUT-FILENAME] [--file_id FILE_ID]
                      [--lc LANGUAGE-CODE] [-v] [-pb] [-n MAX_CASES] [-x MAX_EXAMPLES] [-r REF-FILENAME] [--version]

Analyzes a given text for a wide range of anomalies

options:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  --batch BATCH_DIR     Directory with batch of input files (BATCH_DIR/*.txt)
  -s, --summary         single summary line per file
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  -j JSON-OUTPUT-FILENAME, --json JSON-OUTPUT-FILENAME
                        (default: None)
  --file_id FILE_ID
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  -v, --verbose         write change log etc. to STDERR
  -pb, --progress_bar   Show progress bar
  -n MAX_CASES, --max_cases MAX_CASES
                        max number of cases per group
  -x MAX_EXAMPLES, --max_examples MAX_EXAMPLES
                        max number of examples per line
  -r REF-FILENAME, --ref_id_file REF-FILENAME
                        (optional file with sentence reference IDs)
  --version             show program's version number and exit
```

Sample calls:
```
wb_analysis.py --help
echo 'Hеllο!' | wb_analysis.py
wb_analysis.py -i test/data/hello.txt
wb_analysis.py -i test/data/wildebeest-test.txt -o test/data/wildebeest-test-out
wb_analysis.py --batch test/data/phrasebook -s -o test/data/phrasebook-dir-out
wb_analysis.py -i test/data/phrasebook/deu.txt -r test/data/phrasebook/eng.txt -o test/data/phrasebook-deu-out
wb_analysis.py -i test/data/wildebeest-test-invalid-utf8.txt
```
## wb-analysis.pl

Old Perl script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, non-ASCII punctuation,
characters from a variety of language groups, very long tokens, unsplit 's,
unsplit punctuation, script mixing; split URLs, email addresses, filenames,
XML tokens.

It will report the number of instances in each category and give examples.

Currently available: wildebeest_analysis.pl (Perl) v2.6 (April 28, 2021)



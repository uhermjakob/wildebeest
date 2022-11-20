# wildebeest

The wildebeest scripts investigate, repair and normalize text for a wide range of issues at the character level.

**wb-ana** (or wb_analysis.py)

This script searches a tokenized text for a range of potential problems, 
such as UTF-8 encoding violations, control characters, zero-with characters, 
letters/numbers/punctuation/letter-modifiers from various scripts 
(e.g. Latin and Cyrillic), tokens with letters from different scripts, 
XML tokens, tokens with certain punctuation of interest, orphan letter modifiers, 
non-canonical character combinations.

**wb-norm** (or wb_normalize.py)

This script automatically corrects some of the issues raised by wb-ana.
The script can repair common encoding errors, normalize characters into their UTF8-canonical form, map digits and some
punctuation to ASCII, delete many non-printable characters and perform other repair, normalization and cleaning steps.
A few steps are specific to Pashto, Farsi, or Devanagari (Hindi etc.).
Normalization steps can be activated *à la carte*.

## Installation

<details>
<summary>Click here for installation info</summary>

```bash
# Install from PyPi:
pip install wildebeest-nlp

# Alternatively, pip-install from GitHub master branch:
pip install git+https://github.com/uhermjakob/wildebeest.git

# Alternatively, clone GitHub, which might be useful for editing/development:
git clone https://github.com/uhermjakob/wildebeest.git
# or git clone git://github.com/uhermjakob/wildebeest.git
cd wildebeest
pip install --editable .   # run it from dir having setup.py
```

A pip-install will provide commands `wb-norm` and `wb-ana` as well as their alternate forms `wb_normalize.py` and `wb_analysis.py`.

After a regular `git clone` (without pip-install), in order to be able to call the Python scripts `wb_normalize.py` and `wb_analysis.py`, make sure that:
1. `wb_normalize.py` and `wb_analysis.py` are executable (i.e. 'x' mode bits are set)
2. your $PYTHONPATH includes the directory in which this README file resides in ("outer wildebeest") and
3. your $PATH includes the directory that includes `wb_normalize.py` and `wb_analysis.py` ("inner wildebeest")

</details>
  
## wb-norm (or wb_normalize.py)

The script repairs common encoding errors, normalizes characters into their canonical form,
deletes many non-printable characters and performs other repair, normalization and cleaning steps.
The script can be parameterized to include or exclude specific normalization steps (e.g. whether
or not to map non-ASCII digits and punctuation to ASCII).
A few steps are specific to Pashto, Farsi, or Devanagari (Hindi etc.).

### Usage &nbsp; (click below for details)
<details>
<summary>CLI to normalize a file: <code>wb-norm</code> or <code>wb_normalize.py</code></summary>

```
usage: wb-norm [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [--lc LANGUAGE-CODE] [--skip NORM-STEPS]
               [--add NORM-STEPS] [--all] [--all-except NORM-STEPS] [--only NORM-STEPS] [-v] [--version]
# or wb_normalize.py [-h] ...

Normalizes and cleans a given text

options:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  --skip NORM-STEPS     perform all default normalization/cleaning steps except those specified in comma-separated list
                        (default normalization/cleaning steps: repair-encoding-errors,del-surrogate,del-ctrl-char,
                        del-tatweel,core-compat,pres-form,hangul,repair-combining,combining-compose,combining-decompose,
                        repair-xml,repair-url-escapes)
  --add NORM-STEPS      perform all default normalization/cleaning steps plus those specified in comma-separated list 
                        (non-default normalization/cleaning steps: del-zero-width,del-arabic-diacr,del-hebrew-diacr,
                        ligatures,signs-and-symbols,cjk,width,font,small,vertical,enclosure,punct,punct-dash,punct-arabic,
                        punct-cjk,punct-greek,punct-misc-f,space,digit,arabic-char,farsi-char,pashto-char,georgian-char,
                        look-alike,repair-token)
  --all                 perform all normalization/cleaning steps, i.e. repair-encoding-errors,del-surrogate,
                        del-zero-width,del-ctrl-char,del-tatweel,del-arabic-diacr,del-hebrew-diacr,core-compat,pres-form,
                        ligatures,signs-and-symbols,cjk,width,font,small,vertical,enclosure,hangul,repair-combining,
                        combining-compose,combining-decompose,punct,punct-dash,punct-arabic,punct-cjk,punct-greek,
                        punct-misc-f,space,digit,arabic-char,farsi-char,pashto-char,georgian-char,look-alike,repair-xml,
                        repair-url-escapes,repair-token
  --all-except NORM-STEPS
                        perform all normalization/cleaning steps except those specified in comma-separated list
  --only NORM-STEPS     perform only normalization/cleaning steps specified in comma-separated list
  -v, --verbose         write change log etc. to STDERR
  --version             show program's version number and exit
```
Examples:
```
wb-norm -h  # for full usage info
wb-norm --version
cd `pip show wildebeest-nlp | grep ^Location | cut -d ' ' -f 2`  # go to directory where wildebeest-nlp is installed
cd wildebeest/test/data
wb-norm --lc fas -i wildebeest-test.txt -o wildebeest-test-norm.txt
wb-norm --lc fas --verbose --skip del-ctrl-char,del-tatweel < wildebeest-test.txt > wildebeest-test-norm-custom.txt
wb-norm --all < wildebeest-test.txt > wildebeest-test-norm-all.txt
wb-norm --all-except del-arabic-diacr,del-hebrew-diacr < wildebeest-test.txt
wb-norm --only del-arabic-diacr,del-hebrew-diacr < wildebeest-test.txt
wb-norm --add del-arabic-diacr,del-hebrew-diacr --skip del-ctrl-char,del-tatweel < wildebeest-test.txt
```
<details>
<summary>Same for alternate script name wb_normalize.py</summary>

```
wb_normalize.py -h  # for full usage info
wb_normalize.py --version
cd `pip show wildebeest-nlp | grep ^Location | cut -d ' ' -f 2`
cd wildebeest/test/data
wb_normalize.py --lc fas -i wildebeest-test.txt -o wildebeest-test-norm.txt
wb_normalize.py --lc fas --verbose --skip del-ctrl-char,del-tatweel < wildebeest-test.txt > wildebeest-test-norm-custom.txt
wb_normalize.py --all < wildebeest-test.txt > wildebeest-test-norm-all.txt
wb_normalize.py --all-except del-arabic-diacr,del-hebrew-diacr < wildebeest-test.txt
wb_normalize.py --only del-arabic-diacr,del-hebrew-diacr < wildebeest-test.txt
wb_normalize.py --add del-arabic-diacr,del-hebrew-diacr --skip del-ctrl-char,del-tatweel < wildebeest-test.txt
```
</details>

Note: For robustness regarding input files that do not fully conform to UTF8, please use -i (rather than STDIN), as it includes UTF8-encoding error handling.
</details>

<details>
<summary>norm_clean_string (Python function call to normalize a string)</summary>

Note: When working on a clone (as opposed to a pip-install), please make sure that your $PYTHONPATH includes the directory in which this README file resides.
```python 
from wildebeest.wb_normalize import Wildebeest
wb = Wildebeest()
ht = wb.build_norm_step_dict(base='ALL')  # base values: 'NONE', 'DEFAULT', 'ALL' (normalization steps)
# ht = wb.build_norm_step_dict()  # defaults: base = 'DEFAULT', skip = None, add = None
# ht = wb.build_norm_step_dict(base='NONE', add=['digit', 'enclosure'])  # normalize only digits (to ASCII) and enclosures
# ht = wb.build_norm_step_dict(base='DEFAULT', skip=['del-tatweel'], add=['digit', 'space'])
# ht = wb.build_norm_step_dict(base='ALL', skip=['punct-dash', 'enclosure', 'del-arabic-diacr'])
wb.load_look_alike_file()           # optional
print(wb.norm_clean_string('🄐…25kmÂ²', ht, lang_code='eng'))
print(wb.norm_clean_string('೧೯೨೩', ht, lang_code='kan'))
``` 
</details>

### Normalization Steps

The script can perform a wide variety of normalization steps.

* 12 normalization steps are performed by default, including basic character repair and UTF8 encoding normalization. The default is generally suitable for applications that largely need to preserve the original text.
* Another 25 normalization steps are available through options `--add (list of steps)`, `--all`, `--all-except (list of steps)`. The `--all` and `--all-excpet` settings are suitable for many NLP applications.
* Default normalization steps can be disabled by option `--skip (list of steps)`.
* Option `--only (list of steps)` applies only the normalization steps listed (without default normalization steps unless explicitly listed).
* Option `--all-except (list of steps)` is equivalent to `--all --skip (list of steps)`

<details>
<summary>List of normalization steps included by default</summary>

* `repair-encoding-errors` The script generally expects input encoded in UTF8. However, it will recognize and repair some common text encoding errors:
  -  (Some) text is still encoded in Windows1252 or Latin1. Any byte that is not part of a well-formed UTF8 character will be interpreted as a Windows1252 character (and mapped to UTF8). This includes printable Latin1 characters as a subset.
  - Text in Windows1252 was incorrectly converted to UTF8 by a Latin1-to-UTF8 converter. This maps Windows1252 characters \x80-\x9F to \u0080-\uu009F, which is the Unicode block of C1 control characters. These C1 control characters are extremely rare, and so our script will interpret such C1 control characters as ill-converted Windows1252 characters, as do many major software applications such as Google Chrome, Microsoft Outlook, Github (text files) and PyCharm (where they are often displayed in a slightly different form).
  -  Text in Windows1252 or Latin1 was converted twice, using some combination of Latin1-to-UTF8 converter and Windows1252-to-UTF converter; or a file already in UTF8 was incorrectly subjected to another conversion. Sample *wildebeest* repair:
    - Input: Donât tell your âfiancÃ©â â SchÃ¶ne GrÃ¼Ãe aus MÃ¤hrenâ¦ â Ma sÅur trouve Ã§a Â«bÃªteÂ». Â¡CoÃ±o! â¬50 â¢ 25kmÂ² â¢ Â½Âµm
    - Output: Don’t tell your “fiancé” — Schöne Grüße aus Mähren… – Ma sœur trouve ça «bête». ¡Coño! €50 • 25km² • ½µm
* `del-surrogate` deletes surrogate characters (representing non-UTF8 characters in input), alternative/backup to windows-1252
* `del-ctrl-char` deletes control characters (expect tab and linefeed), some variation selectors
* `del-tatweel` deletes Arabic tatweel (a text alignment character that increases the distance between Arabic letters)
* `core-compat` normalizes Hangul Compatibility characters to Unicode standard Hangul characters
* `pres-form` e.g. maps from presentation form (isolated, initial, medial, final) to standard form
* `hangul` combine Hangul jamos onto Hangul syllables
* `repair-combining` e.g. order of nukta/vowel-sign
* `combining-compose` e.g. applies combining-modifiers to preceding character, e.g. ö (o +  ̈) -> ö
* `combining-decompose` e.g. for some Indian characters, splits off Nukta
* `repair-xml` e.g. repairs multi-escaped tokens such as &amp;quot; or &amp;amp;#x200C;
* `repair-url-escapes` e.g. repairs multi-escaped url substrings such as Jo%25C3%25ABlle_Aubron
</details>

<details>
<summary>List of additional normalization steps included by --all option</summary>

* `del-zero-width` deletes zero-width characters, byte order mark, directional marks, join marks
* `arabic-char` to Arabic canonical forms, e.g. maps Farsi kaf/yeh to Arabic versions
* `farsi-char` to Farsi canonical forms, e.g. maps Arabic yeh, kaf to Farsi versions
* `pashto-char` to Pashto canonical forms, e.g. maps Arabic kaf to Farsi version
* `georgian-char` to Georgian canonical forms, e.g. to standard script, map archaic characters
* `ligatures` e.g. decomposes non-Arabic ligatures (e.g. ĳ, ﬃ, Ǆ, ﬓ)
* `signs-and-symbols` e.g. maps symbols (e.g. kappa symbol) and signs (e.g. micro sign µ)
* `cjk` e.g. CJK square composites (e.g. ㋀㏾)
* `width` e.g. maps fullwidth and halfwidth characters to ASCII, e.g. Ａ to A
* `font` maps font-variations characters such as ℂ, ℹ, 𝒜 to regular characters
* `small` maps small versions of characters to normal versions, such as small ampersand ﹠ to regular &
* `vertical` maps vertical versions of punctuation characters with normal horizontal version, such as vertical em-dash ︱ to horizontal em-dash —
* `enclosure` decomposes circled, squared and parenthesized characters, e.g. 🄐 to (A)
* `del-arabic-diacr` e.g. deletes optional Arabic diacritics such as fatha, damma, kasra
* `del-hebrew-diacr` e.g. deletes Hebrew points
* `digit` e.g. maps decimal-system digits of 54 scripts to ASCII digits
* `punct` e.g. maps ellipsis … to periods ... and two-dot-lead ‥ to ..; a few math symbols ∭; ⒛ 🄆 
* `punct-dash` e.g. maps various dashes, hyphens, minus signs to ASCII hyphen-minus
* `punct-arabic` e.g. Arabic exclamation mark etc. to ASCII equivalent
* `punct-cjk` e.g. Chinese Ideographic Full Stop etc. to ASCII equivalent
* `punct-greek` e.g. Greek question mark etc. to ASCII equivalent
* `punct-misc-f` e.g. Tibetan punctuation to ASCII equivalent
* `space` e.g. maps non-zero spaces to normal space
* `look-alike` normalizes Latin/Cyrillic/Greek look-alike characters, e.g. Latin character A to Greek Α (capital alpha) in otherwise Greek word
* `repair-token` e.g. splits +/-/*/digits off Arabic words; maps not-sign inside Arabic to token-separating hyphen
</details>

## wb-ana (or wb_analysis.py)

Script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, zero-with characters,
letters/numbers/punctuation/letter-modifiers from various scripts,
tokens with letters from different scripts, XML tokens, tokens with certain
punctuation of interest, orphan letter modifiers, non-canonical character
combinations.

### Usage

<details>
<summary>CLI to analyze a file: <code>wb-ana</code> or <code>wb_analysis.py</code> </summary>

```
usage: wb-ana  [-h] [-i INPUT-FILENAME] [--batch BATCH] [-s] [-o OUTPUT-FILENAME] [-j JSON-OUTPUT-FILENAME] [--file_id FILE_ID]
               [--lc LANGUAGE-CODE] [-v] [-pb] [-n MAX_CASES] [-x MAX_EXAMPLES] [-r REF-FILENAME] [--version]
# or wb_analysis.py  [-h] ... 
  
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

Examples:
```
wb-ana --help
echo 'Hеllο!' | wb-ana                  # 'Hеllο!' mischievously includes a Cyrillic and a Greek character
echo 'Hеllο!' | wb-norm --all | wb-ana  # different result
cd `pip show wildebeest-nlp | grep ^Location | cut -d ' ' -f 2`  # go to directory where wildebeest-nlp is installed
cd wildebeest/test/data
wb-ana -i hello.txt
wb-ana -i wildebeest-test.txt -o wildebeest-test-out
wb-ana --batch phrasebook -s -o phrasebook-dir-out
wb-ana -i phrasebook/deu.txt -r phrasebook/eng.txt -o phrasebook-deu-out
wb-ana -i wildebeest-test-invalid-utf8.txt
```

<details>
<summary>Same for alternate script name wb_analysis.py</summary>

```
wb_analysis.py --help
echo 'Hеllο!' | wb_analysis.py
echo 'Hеllο!' | wb_normalize.py --all | wb_analysis.py
cd `pip show wildebeest-nlp | grep ^Location | cut -d ' ' -f 2`
cd wildebeest/test/data
wb_analysis.py -i hello.txt
wb_analysis.py -i wildebeest-test.txt -o wildebeest-test-out
wb_analysis.py --batch phrasebook -s -o phrasebook-dir-out
wb_analysis.py -i phrasebook/deu.txt -r phrasebook/eng.txt -o phrasebook-deu-out
wb_analysis.py -i wildebeest-test-invalid-utf8.txt
```
</details>
</details>

<details>
<summary>wildebeest.wb_analysis.process (Python function call to analyze a string, a list of strings, or a file)</summary>

Note: When working on a clone (as opposed to a pip-install), please make sure that your $PYTHONPATH includes the directory in which this README file resides.
```python 
import pprint
import sys
import wildebeest.wb_analysis as wb_ana
wb = wb_ana.process(string="Hеllο!")   # "Hеllο!" mischievously includes a Cyrillic and a Greek character
wb.pretty_print(sys.stdout)            # custom pretty-print with OVERVIEW and DETAIL sections to STDOUT
pprint.pprint(wb.analysis)             # generic pretty-print
```
  
```python 
import wildebeest.wb_analysis as wb_ana
wb = wb_ana.process(strings=["Hеllο!", "Tschüß"])
print(wb.analysis)  # print analysis object (nested dictionary)
```

Assuming an input file `corpus.txt`, e.g. built by:
```bash
printf 'Hеllο!\nTschüß\n' > corpus.txt
```
  
```python 
import wildebeest.wb_analysis as wb_ana
wb = wb_ana.process(in_file='corpus.txt')
print(wb.analysis)
```
  
```python 
import wildebeest.wb_analysis as wb_ana
with open(f'out.txt', 'w') as out, open('out.json', 'w') as json:
    wb_ana.process(in_file='corpus.txt', pp_output=out, json_output=json)
```  
</details>

### wb-analysis.pl

Old Perl script searches a tokenized text for a range of potential problems,
such as UTF-8 encoding violations, control characters, non-ASCII punctuation,
characters from a variety of language groups, very long tokens, unsplit 's,
unsplit punctuation, script mixing; split URLs, email addresses, filenames,
XML tokens.

Reports the number of instances in each category and give examples.
Currently available: wildebeest_analysis.pl (Perl) v2.6 (April 28, 2021)

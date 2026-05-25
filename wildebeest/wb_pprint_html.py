#!/usr/bin/env python
# #!/Users/ulf2/anaconda3/envs/NLP_3_12/bin/python

import argparse
# try:
#     import cgi
# except ImportError:
#     cgi = None
from collections import defaultdict
import datetime
import json
import os
from pathlib import Path
import re
import regex
import sys
from typing import Optional
import unicodedata as ud
from utilities import ScriptDirection
import wb_analysis as wb_ana
from gr_versification import BackVersification
from gr_utilities import general_util


js_functions = """
        function set_status(new_status) {
            if ((s = document.getElementById('status')) != null) {
                s.innerHTML = new_status;
            }
        }

        function add_status(new_status) {
            if ((s = document.getElementById('status')) != null) {
                s.innerHTML = s.innerHTML + '<br>' + new_status;
            }
        }

        function build_examples(title, in_file, out_file, snt_id_file, ex_list, ex_class) {
            html_content = '<html><head><title>build</title></head><body>Building examples ...</body></html>\\n';
            var myWindow = window.open('', '_build');
                var tmp = myWindow.document;
                tmp.open();
                tmp.write(html_content);
            tmp.close();

            var form = document.createElement("form");
            form.setAttribute("enctype","multipart/form-data");
            form.setAttribute("action","http://localhost/cgi-bin/wb_pprint_ex_html.py");
            form.setAttribute("method","post");
            // form.setAttribute("display","none");

            var input1 = document.createElement("input");
            input1.setAttribute("type","hidden");
            input1.setAttribute("name","ex_title");
            input1.setAttribute("id","ex_title");
            input1.value = title;
            form.appendChild(input1);

            input2 = document.createElement("input");
            input2.setAttribute("type","hidden");
            input2.setAttribute("name","ex_list");
            input2.setAttribute("id","ex_list");
            input2.value = ex_list;
            form.appendChild(input2);

            input3 = document.createElement("input");
            input3.setAttribute("type","hidden");
            input3.setAttribute("name","ex_class");
            input3.setAttribute("id","ex_class");
            input3.value = ex_class;
            form.appendChild(input3);

            input4 = document.createElement("input");
            input4.setAttribute("type","hidden");
            input4.setAttribute("name","input_filename");
            input4.setAttribute("id","input_filename");
            input4.value = in_file;
            form.appendChild(input4);

            input5 = document.createElement("input");
            input5.setAttribute("type","hidden");
            input5.setAttribute("name","output_filename");
            input5.setAttribute("id","output_filename");
            input5.value = out_file;
            form.appendChild(input5);

            input6 = document.createElement("input");
            input6.setAttribute("type","hidden");
            input6.setAttribute("name","snt_id_filename");
            input6.setAttribute("id","snt_id_filename");
            input6.value = snt_id_file;
            form.appendChild(input6);

            // use defaults for now: line_list; max_number_output_snt; print_to_stdout; no_cache

            var submit = document.createElement("input");
            submit.setAttribute("type","submit");
            form.appendChild(submit);

            tmp.body.appendChild(form);
            submit.click();
            // document.body.removeChild(form);
            // myWindow.close();
        }

        function old_build_examples(title, in_file, out_file, ref_file, ex_list, ex_class) {
            html_content = '<html><head><title>ex-stub</title></head><body>Building examples ...</body></html>\\n';
            newwindow = window.open('');
                var tmp = newwindow.document;
                tmp.open();
                tmp.write(html_content);
            tmp.close();
            newwindow.close();
        }

        function show_examples(out_file) {
           html_file = 'file://' + out_file
           myWindow = window.open(html_file, '_' + out_file);
           myWindow.focus();
           add_status('Point T ' + html_file);
        }

        function show_examples_old(title, in_file, out_file, ref_file, ex_list) {
                command = '/Users/ulf/wildebeest/wildebeest/wb_pprint_ex_html.py';
                command = command.concat(' -t "' + title + '"');
                command = command.concat(' -i ' + in_file);
                command = command.concat(' -o ' + out_file);
                command = command.concat(' -s ' + ref_file);
                command = command.concat(' -e "' + ex_list + '"');
            add_status(command);
                // require('child_process').exec;
            const execSync = require('child_process').execSync;
            add_status('Point C');
                exec(command);
            add_status('Executed');
        }

        function show_examples_test() {
            build_examples('Latin letters',
                           '/Users/ulf/projects/NLP/bible-parallel-corpus-internal/corpus/scripture/pa-panirv.txt',
                           'www/tmp22.html',
                           '/Users/ulf/projects/NLP/bible-parallel-corpus-internal/corpus/scripture/vref.txt',
                           'a d e f l n o t',
                           'string');
            show_examples('/Users/ulf/wildebeest/wildebeest/tmp22.html');
        }
"""


def html_head(title: str, date: str, meta_title: str) -> str:
    return f"""<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
        <link rel="shortcut icon" href="../images/GreekRoomFavicon-32x32.png">
        <title>{meta_title}</title>
        <style>
          [patitle]:hover:after {{opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}}
          [patitle]:after {{
            content: attr(patitle);
            position: absolute;
            bottom: 1.4em;
            left: -9px;
            padding: 5px 10px 5px 10px;
            color: #000;
            font-weight: normal;
            white-space: wrap;
            -moz-border-radius: 5px;
            -webkit-border-radius: 5px;
            border-radius: 5px;
            -moz-box-shadow: 0px 0px 4px #222;
            -webkit-box-shadow: 0px 0px 4px #222;
            box-shadow: 0px 0px 4px #222;
            font-size: 100%;
            background-color: #E0E7FF;
            opacity: 0;
            z-index: 99999;
            visibility: hidden;}}
          [patitle] {{position: relative; }}
          [patitle] {{word-break: keep-all; }}
          [patitle] {{line-break: strict; }}
          [pbtitle]:hover:after {{opacity: 1; transition: all 0.05s ease 0.1s; visibility: visible;}}
          [pbtitle]:after {{
            content: attr(pbtitle);
            position: absolute;
            top: 1.4em;
            left: -9px;
            padding: 5px 10px 5px 10px;
            color: #000;
            font-weight: normal;
            white-space: wrap;
            -moz-border-radius: 5px;
            -webkit-border-radius: 5px;
            border-radius: 5px;
            -moz-box-shadow: 0px 0px 4px #222;
            -webkit-box-shadow: 0px 0px 4px #222;
            box-shadow: 0px 0px 4px #222;
            font-size: 100%;
            background-color: #FFE0E7;
            opacity: 0;
            z-index: 99999;
            visibility: hidden;}}
          [pbtitle] {{position: relative; }}
          [pbtitle] {{word-break: keep-all; }}
          [pbtitle] {{line-break: strict; }}
        </style>
        <script type="text/javascript">
        <!--
        function toggle_info(j) {{
            if ((s = document.getElementById(j)) != null) {{
                if (s.style.display == 'inline') {{
                    s.style.display = 'none';
                }} else {{
                    s.style.display = 'inline';
                }}
            }}
        }}
        {js_functions}
        -->
        </script>
    </head>
    <body bgcolor="#FFFFEE" onload="set_status('START');">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr bgcolor="#BBCCFF">
                <td><table border="0" cellpadding="3" cellspacing="0">
                        <tr>
                            <td><b><font class="large" size="+1">&nbsp; {title}</font></b></td>
                            <td>&nbsp;&nbsp;&nbsp;{date}&nbsp;&nbsp;&nbsp;</td>
                            <td style="color:#777777;font-size:80%;">Script wb_pprint_html.py &nbsp; 
                                                                    by Ulf Hermjakob</td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table><p>
"""


def html_foot() -> str:
    return """    </body>
</html>
"""


def print_text_to_outputs(s: str, outputs: list) -> None:
    for output in outputs:
        output.write(s)


def highlight_other_paired_delimiters_in_text(text: str, wb) -> str:
    if wb:
        delimiters = wb.punct_analysis['matching_punct']
        g_delimiters = regex.sub(r'([\(\)\[\]{}])', r'\\\1', delimiters)
        regex_s = fr'([{g_delimiters}])'
        try:
            return regex.sub(regex_s, r'<span style="background-color:#7DF9FF;font-weight:bold;">\1</span>', text)
        except regex.error:
            pass
    return text


def highlight_search_term_tokens_in_text(text, search_term, full_token_only_p: bool = False,
                                         _line_number=None, column_position=None, wb=None):
    """returns text with search_term highlighted in red, token in yellow background"""
    # Identify text tokens to be highlighted
    verbose = False  # ("[" in search_term) and ("[" in text)
    try:
        column_char = text[column_position]
    except TypeError or IndexError:
        column_char = None
    if verbose:
        sys.stderr.write(f"  highlight {text} {search_term} {full_token_only_p} {_line_number} {column_position} "
                         f"{column_char}\n")
    if column_char is None:
        n_matches = 0
        result = ''
        rest = text
        if full_token_only_p:
            regex_s = rf'(.*?)(\s*)(?<!\S)({search_term})(?!\S)(\s*)(.*)$'
        else:
            regex_s = rf'(.*?)(\s?\S*?)({search_term})(\S*\s|\S*)(.*)$'
        try:
            regex.match(regex_s, text, regex.IGNORECASE)
        except re.error:
            print('Error HL', regex_s)
            # if verbose: sys.stderr.write(f"    highlight R3 {search_term} {text} (Error HL)\n")
            return text, 0
        while m5 := regex.match(regex_s, rest, regex.IGNORECASE):
            pre_tokens, pre, term, post, post_tokens = m5.group(1, 2, 3, 4, 5)
            result += (guard_html(pre_tokens)
                       + '<span style="background-color:yellow;">'
                       + guard_html(pre)
                       + '<span style="color:red;font-weight:bold;">'
                       + guard_html(term)
                       + '</span>')
            n_matches += 1
            rest2 = post
            while m3 := regex.match(rf'(.*?)({search_term})(.*)$', rest2, regex.IGNORECASE):
                pre2, term2, post2 = m3.group(1, 2, 3)
                result += guard_html(pre2) + '<span style="color:red;">' + guard_html(term2) + '</span>'
                rest2 = post2
                n_matches += 1
            result += guard_html(rest2) + '</span>'
            rest = post_tokens
        result += guard_html(rest)
        # if verbose: sys.stderr.write(f"    highlight R4 {search_term} {result} {n_matches}\n")
        return result, n_matches
    else:
        m2l = regex.match(r'(.*?)(\S*)$', text[0:column_position])
        m2r = regex.match(r'(\S*)(.*)$', text[column_position+1:])
        pre_tokens, pre = m2l.group(1, 2)
        term = regex.sub(r'\\([()])', r'\1', search_term)  # remove some regex guards: \( \) -> ( )
        post, post_tokens = m2r.group(1, 2)
        result = (highlight_other_paired_delimiters_in_text(guard_html(pre_tokens), wb)
                  + '<span style="background-color:yellow;">'
                  + guard_html(pre)
                  + '<span style="color:red;">'
                  + guard_html(column_char or term)
                  + '</span>'
                  + guard_html(post)
                  + '</span>'
                  + highlight_other_paired_delimiters_in_text(guard_html(post_tokens), wb))
        # if verbose: sys.stderr.write(f"    highlight R5 {search_term} {result}\n")
        return result, 1


def example_sort_key(example) -> int:
    if isinstance(example, int):
        return example
    try:
        return int(example[1])
    except (ValueError, BaseException):
        return 0


def highlight_examples_in_corpus(wb: wb_ana.WildebeestAnalysis, examples: list, s: str, bv: BackVersification,
                                 output_filename=None, regex_p=False, regex_descr=None,
                                 filename_base_core='', full_token_only_p=False,
                                 args: argparse.Namespace | None = None) -> None:
    verbose = args.verbose if args else False
    # noinspection SpellCheckingInspection
    if regex.match(r'^[\u0000-\u0020\u007F-\u00A0\u2002-\u200D\u3000\u303F\uFEFF]$', s):  # invisible characters
        regex_descr = f"{ud.name(s, s)} &nbsp; (U+{ord(s):04X})"
    line_dict = defaultdict(bool)
    prev_printed_dict = defaultdict(bool)
    examples = sorted(examples, key=example_sort_key)
    corpus_rtl = wb.script_direction.is_right_to_left()
    with open(output_filename, 'w') as f:
        f.write(html_head(f'Wildebeest analysis examples for: &nbsp; {filename_base_core} &nbsp; {regex_descr or s}',
                          datetime.datetime.now().strftime('%B %d, %Y at %H:%M'), 'wb-examples'))
        f.write('<table>')
        for example in examples:
            if isinstance(example, int):
                line_number = example
                column_position = None
            else:
                try:
                    example_s, line_number = example[0], int(example[1])
                except IndexError:
                    print(f"Index Error: {examples}")
                try:
                    column_position = int(example[2])
                except IndexError:
                    column_position = None
            if not line_dict[line_number]:
                if wb.ref_id_dict:
                    ref_id = wb.ref_id_dict.get(line_number, None)
                    bv_ref_id = bv.mh(ref_id)
                    ref_id_clause = '' if ref_id is None else bv_ref_id
                else:
                    ref_id = line_number
                    ref_id_clause = ''
                if wb.corpus:
                    if prev_printed_dict[ref_id]:
                        continue
                    if line := wb.corpus.get(ref_id).rstrip():
                        line_rtl = ScriptDirection.string_is_right_to_left(line)
                        if line_rtl:
                            if not wb.corpus_w_rtf_delimiter_adjustments.get(ref_id):
                                if wb.script_direction.text_contains_switchable_chars(line):
                                    line2 = wb.script_direction.switch_delimiters_for_rtl_scripts(line)
                                    wb.corpus_w_rtf_delimiter_adjustments[ref_id] = line2
                        dir_clause = " dir='rtl'" if line_rtl else ""
                        if regex_p:
                            s1 = s
                            s = regex.sub(r"’\\?\s”", r"’\\s”", s)
                            s = regex.sub(r"”\\?\s’", r"”\\s’", s)
                            s = regex.sub(r"“\\?\s‘", r"“\\s‘", s)
                            s = regex.sub(r"‘\\?\s“", r"‘\\s“", s)
                            if verbose and (s1 != s):
                                print('PAT-CHANGE', s1, ' -> ', s)
                            pattern = s
                        else:
                            pattern = re.escape(s)
                        hl_text = highlight_search_term_tokens_in_text(line, pattern, _line_number=line_number,
                                                                       column_position=column_position,
                                                                       full_token_only_p=full_token_only_p, wb=wb)[0]
                        line_number_column = f'<td align="right" style="color:#AAAAAA;">{line_number}</td>'
                        ref_column = f'<td><nobr>&nbsp;&nbsp;{ref_id_clause}&nbsp;&nbsp;</nobr></td>'
                        text_column = f'<td{dir_clause}>{hl_text}</td>'
                        if corpus_rtl:
                            f.write(f'<tr>{text_column} {ref_column} {line_number_column}</tr>')
                        else:
                            f.write(f'<tr>{line_number_column} {ref_column} {text_column}</tr>')
                        prev_printed_dict[ref_id] = True
        f.write('</table>')
        f.write(html_foot())


def format_examples(wb: wb_ana.WildebeestAnalysis, examples: list, s: str, bv: BackVersification) -> str:
    """Group examples in pretty format string"""
    max_display_len = wb.max_n_viz_examples
    display_len = 0
    ex_l_dict = defaultdict(list)
    ex_r_dict = defaultdict(list)
    ref_id_p = False
    for example in examples:
        example_s, line_number_s = example[0], str(example[1])
        if line_number_s not in ex_l_dict[example_s]:
            ex_l_dict[example_s].append(line_number_s)
            if wb.ref_id_dict and (ref_id := wb.ref_id_dict[int(line_number_s)]):
                bv_ref_id = bv.mh(ref_id)
                ex_r_dict[example_s].append(bv_ref_id)
                ref_id_p = True
            else:
                ex_r_dict[example_s].append(f'l.{line_number_s}')
    if (len(ex_l_dict) == 1) and ex_l_dict.get(s) and not ref_id_p:
        line_numbers = ex_l_dict[s]
        line_kw_clause = 'line' if len(line_numbers) == 1 else 'lines'
        return f"{line_kw_clause}: {', '.join(line_numbers[:max_display_len])}"
    else:
        formatted_examples = []
        for example in ex_l_dict.keys():
            if ref_id_p:
                formatted_examples.append(f"{example} "
                                          f"({', '.join(ex_r_dict[example][:max_display_len-display_len])})")
            else:
                formatted_examples.append(f"{example} "
                                          f"(l.{', '.join(ex_l_dict[example][:max_display_len-display_len])})")
            display_len += len(ex_l_dict[example])
            if display_len >= max_display_len:
                break
        example_kw_clause = 'example' if len(formatted_examples) == 1 else 'examples'
        return f"{example_kw_clause}: " \
               f"{', '.join(formatted_examples)}"


def guard_html(s: str, p_title: bool = False) -> str:
    s = re.sub('&', '&amp;', s)
    s = re.sub('<', '&lt;', s)
    s = re.sub('>', '&gt;', s)
    s = re.sub('"', '&quot;', s)
    if p_title:
        s = s.replace('&amp;#xA;', '&#xA;')
        # noinspection SpellCheckingInspection
        s = s.replace('&amp;nbsp;', '&nbsp;')
        s = s.replace(' ', '&nbsp;')    # non-breakable space
        s = regex.sub('(&nbsp;){2,}', ' ', s)  # unless there are multiple spaces
        # noinspection SpellCheckingInspection
        s = s.replace('&amp;xxxnbsp;', '&nbsp;'*30)
        # noinspection SpellCheckingInspection
        s = s.replace('&amp;xxnbsp;', '&nbsp;'*20)
        # noinspection SpellCheckingInspection
        s = s.replace('&amp;xnbsp;', '&nbsp;'*10)
        s = s.replace('-', '&#x2011;')   # non-breakable hyphen
        s = s.replace('&#xA;', ' ')
    return s


def g(s: str) -> str:
    # guard with left-to-right marker if string contains character from right-to-left script
    # result = guard_html(s)
    matches, start_positions, inter_matches = general_util.findall3(r'<span.*?>.*?</span>', s)
    result = ""
    for i in range(len(matches)):
        result += guard_html(inter_matches[i]) + matches[i]
    result += inter_matches[-1]
    if regex.search(r'(?V1)[[\p{Arabic}||\p{Hebrew}||\p{Syriac}||\p{Thaana}]&&\pL]', s):
        return '‎' + result
    else:
        return result


def pretty_print_to_html_string(wb: wb_ana.WildebeestAnalysis, example_dir: str,
                                bv: BackVersification, args: argparse.Namespace | None = None) -> str:
    """Output Wildebeest analysis in human-readable format."""
    example_file_index = 0
    if example_dir and not os.path.isdir(example_dir):
        os.mkdir(example_dir)
        os.chmod(example_dir, 0o777)
    result = ''
    result += "This page lists a wide range of character level problems such as encoding errors, " \
              "characters in the wrong script, characters in non-canonical forms, missing or spurious " \
              "spaces around punctuation/space issues, and spurious control characters.<br>\n"
    result += """<span style="text-decoration:underline" onclick="toggle_info('top-note');">""" \
              "Click here</span> for more information about the purpose and the features of this page.\n"
    result += """<div id="top-note" style="display:none"><p><ul style="margin-top:0px;">\n"""
    result += "<li> The Wildebeest tool provides and overview of the characters used in a text corpus and flags " \
              "a number of potential issues, but it is always the human translator who will make the final decision " \
              "regarding any corrections.\n"
    result += "<li> Many texts use only one script (e.g. the Latin alphabet), " \
              "so the use of additional scripts might be inadvertent.\n"
    result += """<li> Generally, you might want to look out for very rare characters (i.e. with a low count).\n"""
    result += "<li> As a special case, a text might contain very few digits (e.g. '12'), " \
              "possibly because most numbers are spelled out as words (e.g. 'twelve'), " \
              "in which case the rare use of digits might be reflect a stylistic inconsistency.\n"
    result += "<li> When checking for unmatched delimiters (such as left and right parenthesis), " \
              "Wildebeest checks across sentences, " \
              "but it only displays the line containing an unmatched delimiter.\n"
    result += "<li> Rival character sets\n<ul>\n"
    result += "<li> Generally, you might want to avoid using multiple styles of punctuation such as both plain " \
              "QUOTATION MARK (\") and the directional LEFT/RIGHT DOUBLE QUOTATION MARK (“...”).\n"
    result += "</ul>\n"
    title = "In examples following below,  hovering over an item in red  will reveal an explanation  why it is flagged."
    result += """<li> For token patterns in <span style="color:red;font-weight:bold;" """ \
              f"""patitle="{guard_html(title, True)}">red</span>, """ \
              """you may hover over it with your mouse pointer to get more information.\n"""
    result += """<li> Token patterns in <span style="color:green;font-weight:bold;">green</span> are probably OK.\n"""
    result += "<li> Special pattern representations\n<ul>\n"
    result += """<li> The pattern <b>Modifier</b> represents a letter modifier (e.g. a diacritic) """ \
              """that usually follows a letter.\n"""
    result += """<li> The pattern <b>Word</b> represents a sequence of letters (e.g. "love").\n"""
    # noinspection SpellCheckingInspection
    result += """<li> The pattern <b>WordWLM</b> represents a sequence of letters (e.g. "love") """ \
              """preceded by a leading Modifier likely to be legitimate (e.g. Arabic fatha).\n"""
    result += """<li> The pattern <b>Number</b> represents a sequence of digits (e.g. "12" or "2000").\n"""
    result += """<li> The pattern <b>NumberCC</b> represents a sequence of comma-separated digits in groups of 4 """ \
              """(i.e. "Chinese-style", e.g. "1234,5678").\n"""
    result += """<li> The pattern <b>NumberIC</b> represents a sequence of comma-separated digits in groups of 2 """ \
              """and 3 (i.e. "Indian-style, e.g. "1,23,45,678").\n"""
    result += """<li> The pattern <b>NumberWC</b> represents a sequence of comma-separated digits in groups of 3 """ \
              """(i.e. "Western-style", e.g. "12,345,678").\n"""
    result += """<li> The pattern <b>NumberWP</b> represents a sequence of period-separated digits in groups of 3 """ \
              """(i.e. "Western-style", e.g. "12.345.678").\n"""
    result += "</ul>\n"
    result += "</ul></div>\n<p>\n<hr>\n<p>\n"
    result += '<h3>Overview</h3>\n'
    result += '<ul>\n'
    n_lines = wb.analysis['n_lines']
    n_empty_lines = wb.analysis['n_empty_lines']
    n_non_empty_lines = n_lines - n_empty_lines
    result += f"  <li> File size: {wb_ana.count_plus_noun(n_lines, 'line')}"
    if wb.analysis['n_empty_lines']:
        result += f" ({wb_ana.count_plus_noun(n_non_empty_lines, 'non-empty line')}," \
                  f" {wb_ana.count_plus_noun(n_empty_lines, 'empty line')})"
    result += f", {wb_ana.count_plus_noun(wb.analysis['n_characters'], 'character')}\n"
    # result += "  <li> <div id='status' name='status'>DEFAULT</div>\n"
    # result += f"  <li> <div title='Test click'" \
    #           f" style='color:#0000FF;text-decoration:underline;'" \
    #           f" onclick='show_examples_test();'>TEST</div>\n"
    for heading, keyword in (('Letter scripts', 'letter-script'),
                             ('Number scripts', 'number-script'),
                             ('Other character groups', 'other-script')):
        result += f"  <li> {heading}: {len(wb.analysis[keyword])}\n"
        result += "  <ul>\n"
        for unicode_script in wb.analysis[keyword].keys():
            letter_script_dict = wb.analysis[keyword][unicode_script]
            count = letter_script_dict.get('count', 0)
            if count == 0:
                continue
            result += f"    <li> {unicode_script} ({wb_ana.count_plus_noun(count, 'instance')})"
            if ((unicode_script not in ('C0_CONTROL', 'C1_CONTROL', 'SPACE', 'ZERO_WIDTH', 'DIRECTIONAL',
                                        'VARIATION_SELECTORS', 'LOW_SURROGATES'))
                    and (ex_s := letter_script_dict.get('ex', None))):
                try:
                    ex_for_print = wb.insert_spaces_before_any_letter_modifiers(ex_s)
                    result += f": {ex_for_print}"
                except UnicodeError as error:
                    sys.stderr.write(f"*** Unicode error: {error}\n")
                if example_dir and os.path.isdir(example_dir) and count < 10000:
                    lines_default = letter_script_dict['lines']
                    lines_by_char = set()
                    if keyword == 'number-script' and len(ex_s) < 100:
                        for ex_char in ex_s:
                            d = wb.analysis['block'][wb.unicode_block(ex_char)][ex_char]
                            for example in d['ex']:
                                if isinstance(example, int):
                                    lines_by_char.add(example)
                                else:
                                    try:
                                        example_s, line_number = example[0], int(example[1])
                                        lines_by_char.add(line_number)
                                    except IndexError:
                                        pass
                        lines_by_char = sorted(lines_by_char)
                        lines = lines_by_char if len(lines_by_char) < len(lines_default) else lines_default
                    else:
                        lines = lines_default
                    if lines:
                        example_file_index += 1
                        ex_for_regex = f"(?:{'|'.join(list(map(regex.escape, ex_s)))})"
                        output_filename_basename = f'ex-{example_file_index:05d}.html'
                        output_filename = f'{example_dir}/{output_filename_basename}'
                        highlight_examples_in_corpus(wb, lines, ex_for_regex, bv,
                                                     output_filename=output_filename, regex_p=True,
                                                     regex_descr=unicode_script,
                                                     filename_base_core=os.path.basename(example_dir),
                                                     args=args)
                        result += f" &nbsp; <a target='_EX' href='{output_filename_basename}'>show</a>"
                    else:
                        result += f" &nbsp; <span style='color:#AAAAAA;' " \
                                  f"title='Page generated with detailed examples disabled.'>show</span>"
        result += "\n"
        result += "  </ul>\n"
    non_canonical_char_combs = wb.analysis['non-canonical'].keys()
    if n_non_canonical_char_combs := len(non_canonical_char_combs):
        result += f"  <li> Non-canonical character combinations: {n_non_canonical_char_combs}\n"
    char_conflicts = wb.analysis['rival-char-sets'].keys()
    if n_char_conflicts := len(char_conflicts):
        result += f"  <li> Rival character sets: {n_char_conflicts}\n"
    notable_dict = defaultdict(dict)
    # {'XML escape tokens': {'GROUP_COUNT': 0, 'TYPE_COUNT': 0, 'TOKEN_COUNT': 0}, ...}
    for notable_heading in sorted(wb.analysis['notable-token'].keys()):
        if re.search(r'XML', notable_heading, re.IGNORECASE):
            key1 = 'XML escape tokens'
        elif re.search(r'multi.*script', notable_heading, re.IGNORECASE):
            key1 = 'Words with characters from multiple scripts'
        else:
            continue
        notable_dict[key1]['GROUP_COUNT'] = notable_dict[key1].get('GROUP_COUNT', 0) + 1
        tokens = wb.analysis['notable-token'][notable_heading].keys()
        for token in tokens:
            notable_dict[key1]['TYPE_COUNT'] = notable_dict[key1].get('TYPE_COUNT', 0) + 1
            notable_dict[key1]['TOKEN_COUNT'] = (notable_dict[key1].get('TOKEN_COUNT', 0)
                                                 + wb.analysis['notable-token'][notable_heading][token]['count'])
    for key1 in notable_dict.keys():
        group_count = notable_dict[key1]['GROUP_COUNT']
        type_count = notable_dict[key1]['TYPE_COUNT']
        token_count = notable_dict[key1]['TOKEN_COUNT']
        result += f"  <li> {key1}: " \
                  f"{group_count} {'category' if (group_count == 1) else 'categories'}, " \
                  f"{type_count} {'unique type' if type_count == 1 else 'unique types'}, " \
                  f"{token_count} {'instance' if token_count == 1 else 'instances'}\n"
    result += '</ul>\n'
    result += '<hr>\n'
    result += '<h3>Details</h3>\n'
    index_elements = []
    if wb.analysis['notable-token'].keys():
        index_elements.append('<a href="#notable">notable tokens</a>')
    if wb.analysis['block'].keys():
        index_elements.append('<a href="#block">character blocks</a>')
    if wb.analysis['pattern'].keys():
        index_elements.append('<a href="#pattern">tokens with patterns</a>')
    if index_elements:
        result += f'Jump to: {", ".join(index_elements)}<br>'
    result += '<ul>\n'
    result += f"  <li> Non-canonical character combinations: {len(non_canonical_char_combs)}\n"
    result += '  <table>\n'
    for char_comb in wb.analysis['non-canonical'].keys():
        non_canonical_dict = wb.analysis['non-canonical'][char_comb]
        orig = non_canonical_dict.get('orig')
        norm = non_canonical_dict.get('norm')
        orig_seq = ' + '.join(list(orig))
        norm_seq = ' + '.join(list(norm))
        orig_count = non_canonical_dict.get('orig-count')
        norm_count = non_canonical_dict.get('norm-count')
        orig_form = non_canonical_dict.get('orig-form')
        norm_form = non_canonical_dict.get('norm-form')
        changes = non_canonical_dict.get('changes')
        result += f'    <tr><td>&nbsp; &nbsp; &nbsp;</td>' \
                  f" <td>Non-canonical: {g(orig)} ({g(orig_form)}{g(orig_seq)}, count: {orig_count})</td>" \
                  f" <td>&nbsp; Canonical: {g(norm)} ({g(norm_form)}{g(norm_seq)}, count: {norm_count})</td> <td>"
        if changes and not norm_form:
            result += f"&nbsp; Changes: {', '.join(changes)}"
        result += "</td></tr>\n"
    result += '  </table>\n'
    result += f"  <li> Rival character sets: {len(char_conflicts)}\n"
    if char_conflicts:
        result += "  <table>\n"
        for i, char_conflict_key in enumerate(char_conflicts):
            if i:
                result += "<tr><td></td><td colspan='4'><hr></td></tr>\n"
            info_list = wb.analysis['rival-char-sets'][char_conflict_key]
            for info_elem in info_list:
                result += f"<tr><td>&nbsp; &nbsp; &nbsp;</td>" \
                          f" <td>{g(info_elem['char'])}</td> " \
                          f" <td>&nbsp; {info_elem['id']}</td> " \
                          f" <td>({info_elem['name']})</td> " \
                          f" <td>&nbsp; count: {info_elem['count']}</td></tr>\n"
        result += "  </table>\n"
    if n := wb.n_tatweels():
        result += f"<p>\n  <li> Number of Arabic tatweel characters: {n}\n"
    if wb.analysis['notable-token'].keys():
        result += '<a name="notable"><p><br><p>\n'
    for notable_heading in sorted(wb.analysis['notable-token'].keys()):
        tokens = wb.analysis['notable-token'][notable_heading].keys()
        if tokens:
            examples = []
            for token in tokens:
                examples.extend(wb.analysis['notable-token'][notable_heading][token]['ex'])
            unmatched_delimiter_p = regex.search('delimiters', notable_heading, regex.IGNORECASE)
            if example_dir and os.path.isdir(example_dir):
                if wb.max_notable_token_lines:
                    example_file_index += 1
                    output_filename_basename = f'ex-{example_file_index:05d}.html'
                    output_filename = f'{example_dir}/{output_filename_basename}'
                    ex_for_regex = f"(?:{'|'.join(list(map(regex.escape, tokens)))})"
                    examples2 = examples[:wb.max_notable_token_lines]
                    highlight_examples_in_corpus(wb, examples2, ex_for_regex, bv, regex_p=True,
                                                 regex_descr=notable_heading,
                                                 output_filename=output_filename,
                                                 filename_base_core=os.path.basename(example_dir))
                    show_clause = "" if unmatched_delimiter_p \
                        else f"<a target='_EX' href='{output_filename_basename}'>show</a>"
                else:
                    show_clause = (f"<span style='color:#AAAAAA;' "
                                   f"title='Page generated with detailed examples disabled.'>show</span>")
            else:
                show_clause = ''
            span_clause = ''
            # print('ASS_CLASS', notable_heading)
            if wb.analysis['notable-token-meta'].get(notable_heading) is not None:
                ass_class = wb.analysis['notable-token-meta'][notable_heading]['ass-class']
                ass_descr = wb.analysis['notable-token-meta'][notable_heading]['ass-descr']
            else:
                ass_class = ''
                ass_descr = ''
            if ass_class.startswith('+'):
                span_clause += f' style="color:green;"'
            elif ass_class.startswith('-'):
                span_clause += f' style="color:red;"'
            if ass_descr:
                span_clause += f' patitle="{guard_html(ass_descr, p_title=True)}"'
            # result += "<p>\n"
            result += f"  <li> <span{span_clause}>{notable_heading}</span> &nbsp; {show_clause}\n"
            result += "  <table>\n"
            for i, token in enumerate(tokens, 1):
                if i > wb.max_n_cases:
                    result += ' &nbsp; ...\n'
                    break
                d = wb.analysis['notable-token'][notable_heading][token]
                id_name_clause = f"<td>{g(d['id'])}</td> <td>{g(d['name'])}</td>" if unmatched_delimiter_p else ""
                if example_dir and os.path.isdir(example_dir):
                    if wb.max_notable_token_lines:
                        example_file_index += 1
                        output_filename_basename = f'ex-{example_file_index:05d}.html'
                        output_filename = f'{example_dir}/{output_filename_basename}'
                        d_ex = d['ex'][:wb.max_notable_token_lines]
                        highlight_examples_in_corpus(wb, d_ex, token, bv, output_filename=output_filename,
                                                     filename_base_core=os.path.basename(example_dir))
                        show_clause = f"<a target='_EX' href='{output_filename_basename}'>show</a> &nbsp; "
                    else:
                        show_clause = (f"<span style='color:#AAAAAA;' "
                                       f"title='Page generated with detailed examples disabled.'>show</span> &nbsp; ")
                else:
                    show_clause = ''
                result += f"    <tr><td>&nbsp; &nbsp; &nbsp;</td> " \
                          f" <td>{g(d['token'])}</td> {id_name_clause}<td>&nbsp; count: {d['count']}</td> " \
                          f" <td>&nbsp; {show_clause}{g(format_examples(wb, d['ex'], token, bv))}</td></tr>"
            result += "  </table>\n"
    if wb.analysis['block'].keys():
        result += '<a name="block"><p><br><p>\n'
    for unicode_block in wb.analysis['block'].keys():
        chars = wb.analysis['block'][unicode_block].keys()
        if chars:
            result += f"  <li> {unicode_block} characters\n"
            result += " <table>\n"
            for i, char in enumerate(chars, 1):
                if i > wb.max_n_cases:
                    result += ' &nbsp; ...\n'
                    break
                d = wb.analysis['block'][unicode_block][char]
                d_ex = d['ex'][:wb.max_n_token_examples]
                d_ex_viz = d['ex'][:wb.max_n_viz_examples]
                if example_dir and os.path.isdir(example_dir):
                    if d_ex:
                        example_file_index += 1
                        output_filename_basename = f'ex-{example_file_index:05d}.html'
                        output_filename = f'{example_dir}/{output_filename_basename}'
                        highlight_examples_in_corpus(wb, d_ex, char, bv, output_filename=output_filename,
                                                     filename_base_core=os.path.basename(example_dir))
                        show_clause = f"<a target='_EX' href='{output_filename_basename}'>show</a> &nbsp; "
                    else:
                        show_clause = (f"<span style='color:#AAAAAA;' "
                                       f"title='Page generated with detailed examples disabled.'>show</span> &nbsp; ")
                else:
                    show_clause = ''
                result += f"    <tr><td>&nbsp; &nbsp; &nbsp;</td>" \
                          f" <td>{g(wb.insert_spaces_before_any_letter_modifiers(d['char']))}</td>" \
                          f" <td>&nbsp; {d['id']}</td> <td>&nbsp; {d['name']}</td>" \
                          f" <td>&nbsp; count: {d['count']}</td>" \
                          f" <td>&nbsp; {show_clause}{g(format_examples(wb, d_ex_viz, char, bv))}</td> <td>"
                if (decomp_s := ud.decomposition(char)) \
                        and re.match(r'[0-9A-Z]{4,}$', decomp_s) \
                        and (decomp_c := chr(int(f"0x{decomp_s}", 0))):
                    decomp_name = wb.unicode_name(decomp_c)
                    result += f"&nbsp; decomposition: {g(decomp_c)} ({decomp_name})"
                result += f'</td></tr>\n'
            result += "  </table>\n"
    if wb.analysis['pattern'].keys():
        result += '<a name="pattern"><p><br><p>\n'
    # for pattern_heading in sorted(wb.analysis['pattern'].keys(),
    # key=lambda ph: wb.pattern_class_counts[(ph, None)], reverse=True):
    for pattern_heading in wb.analysis['pattern'].keys():
        patterns = wb.analysis['pattern'][pattern_heading].keys()
        if patterns:
            result += f"  <li> {pattern_heading}\n"
            result += "  <table>\n"
            # for i, pattern in enumerate(sorted(patterns,
            # key=lambda p: wb.pattern_class_counts[(pattern_heading, p)], reverse=True), 1):
            for i, pattern in enumerate(patterns, 1):
                if i > wb.max_n_cases:
                    result += '    ...\n'
                    break
                d = wb.analysis['pattern'][pattern_heading][pattern]
                ass_class = d.get('ass-class', '')
                ass_descr = d.get('ass-descr', '')
                td_clause = ""
                if ass_class.startswith('-'):
                    td_clause = f' style="color:red;font-weight:bold;" patitle="{guard_html(ass_descr, p_title=True)}"'
                elif ass_class.startswith('+'):
                    td_clause = ' style="color:green;"'
                    if ass_descr:
                        td_clause += f' patitle="{guard_html(ass_descr, p_title=True)}"'
                if example_dir and os.path.isdir(example_dir):
                    if d['lines']:
                        # d['lines'] might have as many as wb.max_bad_pattern_lines lines
                        if not ass_class.startswith('-'):
                            if len(d['lines']) > wb.max_pattern_lines:
                                d['lines'] = d['lines'][:wb.max_pattern_lines]
                        example_file_index += 1
                        output_filename_basename = f'ex-{example_file_index:05d}.html'
                        output_filename = f'{example_dir}/{output_filename_basename}'
                        ex_for_regex = wb.pattern_to_regex(pattern)
                        # Next line: pattern with U+02BC MODIFIER LETTER APOSTROPHE
                        full_token_only_p = not (regex.search(r"^Word([ʼ'\u00AD]Word)+$", pattern))
                        highlight_examples_in_corpus(wb, d['lines'], ex_for_regex, bv, regex_descr=pattern,
                                                     output_filename=output_filename, regex_p=True,
                                                     full_token_only_p=full_token_only_p,
                                                     filename_base_core=os.path.basename(example_dir))
                        show_clause = f"<a target='_EX' href='{output_filename_basename}'>show</a> &nbsp; "
                    else:
                        show_clause = (f"<span style='color:#AAAAAA;' "
                                       f"title='Page generated with detailed examples disabled.'>show</span> &nbsp; ")
                else:
                    show_clause = ''
                result += f"    <tr><td>&nbsp; &nbsp; &nbsp;</td>" \
                          f" <td{td_clause}>{g(d['pattern'])}</td> <td><nobr>&nbsp; count: {d['count']}</nobr></td>" \
                          f" <td><nobr>&nbsp; {show_clause}{g(format_examples(wb, d['ex'], pattern, bv))}</nobr>" \
                          f"</td></tr>\n"
            result += "  </table>\n"
    result += '</ul>\n'
    return result


def main_batch_print_html(input_dir: str, root_output_dir: str, title: str, prefix: str, no_cache: bool,
                          snt_id_filename: Optional[str] = None) -> None:
    script = sys.argv[0]
    n_files = 0
    n_columns = 10
    input_dir_path = Path(input_dir)
    input_files = list(Path(input_dir_path).glob('*.txt'))
    potential_vref_files = [f'{input_dir_path}/vref.txt', f'{input_dir_path}/../metadata/vref.txt']
    vref_filename = snt_id_filename
    if vref_filename is None or not os.path.isfile(vref_filename):
        for potential_vref_file in potential_vref_files:
            if os.path.isfile(potential_vref_file):
                vref_filename = potential_vref_file
                break
    if vref_filename:
        vref_path = Path(vref_filename)
        if vref_path in input_files:
            input_files.remove(vref_path)
    input_files.sort()
    top_output_index_filename = f'{root_output_dir}/index.html'
    with open(top_output_index_filename, 'w') as f:
        f.write(html_head(f'Wildebeest analysis examples for: &nbsp; {title} ({len(input_files)} files)',
                          datetime.datetime.now().strftime('%B %d, %Y at %H:%M'), 'wb-examples'))
        f.write('<table>')
        for input_file in input_files:
            base_filename = os.path.basename(input_file)
            base_filename_core = base_filename.removesuffix('.txt')
            output_dir = f'{root_output_dir}/{base_filename_core}'
            output_filename = f'{output_dir}/index.html'
            relative_output_filename = f'{base_filename_core}/index.html'
            summary_filename = f'{output_dir}/summary.txt'
            if base_filename_core.startswith(prefix):
                command = f'{script} -i {input_file} -o {output_filename} -x {output_dir}'\
                          f' --summary_file {summary_filename}'
                if vref_filename:
                    command += f' -s {vref_filename}'
                if no_cache:
                    command += ' -n'
                # print('Command:', command)
                print('Processing', base_filename, '...')
                if no_cache or not os.path.isfile(output_filename):
                    system_code = os.system(command)
                    if system_code:
                        print('   System code:', system_code)
            if n_files % n_columns == 0:
                f.write('<tr>')
            n_files += 1
            summary = None
            title_clause = ''
            if os.path.isfile(summary_filename):
                with open(summary_filename) as f_summary:
                    summary = f_summary.readline().strip()
            if summary:
                title_clause = f' patitle="{guard_html(summary, p_title=True)}"'
            if os.path.isfile(output_filename):
                if summary:
                    file_color = 'orange'
                    for problem in ['non-canonical', 'C1_CONTROL', 'Tatweel']:
                        if problem in summary:
                            file_color = 'red'
                            break
                else:
                    file_color = 'green'
                f.write(f'<td><a href="{relative_output_filename}" '
                        f'target="_FILE"{title_clause} style="color:{file_color};">'
                        f'{base_filename_core}</a></td>')
            else:
                f.write(f'<td>{base_filename_core}</td>')
            if n_files % n_columns == 0:
                f.write('</tr>\n')
        if n_files % n_columns:
            f.write('<td></td>' * (n_columns - n_files % n_columns) + '</tr>\n')
        f.write('</table>')
        f.write(html_foot())
        print(f'Processed {n_files} files. Output index: {top_output_index_filename}')


def default_out_dir(input_filename: str, root_output_dir: str) -> str:
    base_filename = 'wildebeest-' + os.path.basename(input_filename)
    base_filename_core = base_filename.removesuffix('.txt')
    return f'{root_output_dir}/{base_filename_core}'


def get_form_value(form, slot):
    if form:
        return form.getvalue(slot)
    else:
        return None


def main():
    out_help = 'Format: HTML. For defined -i eng.txt -x out_dir, default -o is out_dir/eng/index.html; otherwise None'
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_filename', type=str)
    parser.add_argument('--batch', type=Path, default=None, metavar='BATCH_DIR',
                        help='Directory with batch of input files (BATCH_DIR/*.txt)')
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-t', '--title', type=str, default=None)
    parser.add_argument('--prefix', type=str, default='')
    parser.add_argument('-s', '--snt_id_filename', type=str, default=None)
    parser.add_argument('-o', '--output_filename', type=str, default=None, help=f'{out_help}')
    parser.add_argument('-x', '--example_dir', type=str, default=None)
    parser.add_argument('-X', '--example_root_dir', type=str, default=None, help='provides defaults for -o, -x')
    parser.add_argument('-p', '--print_to_stdout', action='count', default=0, help='Boolean')
    parser.add_argument('-n', '--no_cache', action='count', default=0, help='Boolean')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('--summary_file', type=Path, default=None, help='file with single summary line')
    parser.add_argument('--out_cross_snt_span_file', type=Path, default=None, help='(format: json)')
    parser.add_argument('--ref_cross_snt_span_files', type=Path, nargs='*', default=(),
                        help='optional; input; format: json; content: cross-sentence quotations, open quotation marks')
    parser.add_argument('--max_cases', type=int, default=500, help='max number of cases per group')
    parser.add_argument('--max_examples', type=int, default=100, help='max number of examples per line')
    parser.add_argument('--max_examples_viz', type=int, default=5, help='max number of examples per viz line')
    parser.add_argument('--max_pattern_lines', type=int, default=200)
    parser.add_argument('--max_bad_pattern_lines', type=int, default=2000)
    parser.add_argument('--max_script_lines', type=int, default=200)
    parser.add_argument('--max_non_canonical_lines', type=int, default=100)
    parser.add_argument('--max_char_conflict_lines', type=int, default=100)
    parser.add_argument('--max_notable_token_lines', type=int, default=1000)
    parser.add_argument('--back_versification', type=str, default='vers/back_versification.json')
    args = parser.parse_args()
    main_with_args(args, None)


def main_with_args(args, wb: wb_ana.WildebeestAnalysis | None) -> None:
    date = datetime.datetime.now().strftime('%B %-d, %Y at %-H:%M')

    # adjust args from wb_analysis to wb_pprint_html
    if (not hasattr(args, "input_filename")) and hasattr(args, "input"):
        args.input_filename = args.input.name
    if (not hasattr(args, "snt_id_filename")) and hasattr(args, "ref_id_file"):
        args.snt_id_filename = args.ref_id_file
    if (not hasattr(args, "output_filename")) and hasattr(args, "html_output_filename"):
        args.output_filename = args.html_output_filename
    if (not hasattr(args, "example_dir")) and hasattr(args, "html_example_dir"):
        args.example_dir = args.html_example_dir
    if not hasattr(args, "out_cross_snt_span_file"):
        args.out_cross_snt_span_file = None
    if not hasattr(args, "example_root_dir"):
        args.example_root_dir = None
    if not hasattr(args, "print_to_stdout"):
        args.print_to_stdout = None
    if not hasattr(args, "no_cache"):
        args.no_cache = False
    if hasattr(args, "input_filename"):
        args.input_filename = str(args.input_filename)

    # form = cgi.FieldStorage() if cgi else None
    form = None
    input_filename = get_form_value(form, 'input_filename') or args.input_filename
    snt_id_filename = get_form_value(form, 'snt_id_filename') or args.snt_id_filename
    output_filename = get_form_value(form, 'output_filename') or args.output_filename
    out_cross_snt_span_file = get_form_value(form, 'out_cross_snt_span_file') or args.out_cross_snt_span_file
    example_dir = get_form_value(form, 'example_dir') or args.example_dir
    if args.example_root_dir:
        if not os.path.exists(args.example_root_dir):
            os.makedirs(args.example_root_dir)
        if input_filename:
            if not example_dir:
                example_dir = f'{default_out_dir(input_filename, args.example_root_dir)}'
            if not output_filename:
                output_filename = f'{example_dir}/index.html'
        elif args.batch and not example_dir:
            example_dir = args.example_root_dir
    print_to_stdout = get_form_value(form, 'print_to_stdout') or args.print_to_stdout
    no_cache = get_form_value(form, 'no_cache') or args.no_cache
    summary_file = get_form_value(form, 'summary_file') or args.summary_file
    max_cases = get_form_value(form, 'max_cases') or args.max_cases
    max_examples = get_form_value(form, 'max_examples') or args.max_examples
    max_examples_viz = get_form_value(form, 'max_examples_viz') or args.max_examples_viz
    max_pattern_lines = get_form_value(form, 'max_pattern_lines') or args.max_pattern_lines
    max_bad_pattern_lines = get_form_value(form, 'max_bad_pattern_lines') or args.max_bad_pattern_lines
    max_script_lines = get_form_value(form, 'max_script_lines') or args.max_script_lines
    max_non_canonical_lines = get_form_value(form, 'max_non_canonical_lines') or args.max_non_canonical_lines
    max_char_conflict_lines = get_form_value(form, 'max_char_conflict_lines') or args.max_char_conflict_lines
    max_notable_token_lines = get_form_value(form, 'max_notable_token_lines') or args.max_notable_token_lines
    ref_cross_snt_span_files = get_form_value(form, 'ref_cross_snt_span_files') or args.ref_cross_snt_span_files
    bv = BackVersification(args.back_versification)

    if args.batch and args.example_dir:
        main_batch_print_html(args.batch, args.example_dir, args.title, args.prefix, args.no_cache,
                              args.snt_id_filename)
        return None
    snt_id_dict = defaultdict(str)
    if snt_id_filename:
        with open(snt_id_filename) as f_snt_id:
            line_number = 0
            for line in f_snt_id:
                line_number += 1
                snt_id_dict[line_number] = line.strip()
    else:
        sys.stderr.write('No argument for snt_id_filename ("-s")\n')

    if output_filename and os.path.isfile(output_filename) and os.access(output_filename, os.R_OK) \
            and print_to_stdout \
            and not no_cache:
        try:
            f = open(output_filename, "r")
            sys.stdout.write(f.read())
        except Exception as e:
            sys.stderr.write(f"Cannot read {output_filename}; {e}")
        finally:
            return
    outputs = []
    output_file_handle = None
    if output_filename:
        output_dir = os.path.dirname(output_filename)
        if output_dir and not os.path.isdir(output_dir):
            try:
                os.mkdir(output_dir)
                os.chmod(output_dir, 0o777)
            except Exception as e:
                sys.stderr.write(f"Cannot mkdir {output_dir}; {e}")
        try:
            output_file_handle = open(output_filename, "w")
            outputs.append(output_file_handle)
        except Exception as e:
            sys.stderr.write(f"Cannot write to {output_filename}; {e}")
    if print_to_stdout:
        outputs.append(sys.stdout)
    input_file_basename = os.path.basename(input_filename)
    meta_title = f'WB {input_file_basename}'
    print_text_to_outputs(html_head(f'Wildebeest analysis for: &nbsp; {input_file_basename}',
                                    date, meta_title), outputs)
    if wb is None:
        wb = wb_ana.process(in_file=input_filename,
                            lang_code=args.lc,
                            ref_id_dict=snt_id_dict,
                            ref_cross_snt_span_files=ref_cross_snt_span_files,
                            summary_file=summary_file,
                            max_cases=max_cases,
                            max_examples=max_examples,
                            max_examples_viz=max_examples_viz,
                            max_pattern_lines=max_pattern_lines,
                            max_bad_pattern_lines=max_bad_pattern_lines,
                            max_script_lines=max_script_lines,
                            max_non_canonical_lines=max_non_canonical_lines,
                            max_char_conflict_lines=max_char_conflict_lines,
                            max_notable_token_lines=max_notable_token_lines)
    wb.ref_id_dict = snt_id_dict   # wb.load_ref_ids(args.snt_id_filename)
    sys.stderr.write(bv.report_stats())

    for output in outputs:
        output.write(pretty_print_to_html_string(wb, example_dir, bv, args=args))
    print_text_to_outputs(html_foot(), outputs)
    if output_file_handle:
        output_file_handle.close()
    if args.verbose and output_filename:
        full_out_filename = output_filename if output_filename.startswith("/") else f'{os.getcwd()}/{output_filename}'
        sys.stderr.write(f'Output: {full_out_filename}\n')
    if args.out_cross_snt_span_file:
        d = {}
        if snt_id_dict and (snt_id_dict[1] == 'GEN 1:1'):
            d['corpus'] = 'Bible'
        if args.input_filename:
            base_filename = os.path.basename(args.input_filename)
            base_filename_core = base_filename.removesuffix('.txt')
            d['translation'] = base_filename_core
        if wb.punct_analysis['cross_snt_spans']:
            d['cross-snt-spans'] = wb.punct_analysis['cross_snt_spans']
        if wb.punct_analysis['refresher_lefts']:
            d['refresher-lefts'] = wb.punct_analysis['refresher_lefts']
        if wb.punct_analysis['triple_nesting']:
            d['triple-nesting'] = wb.punct_analysis['triple_nesting']
        with open(out_cross_snt_span_file, 'w') as f:
            f.write(json.dumps(d) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
#
# lab is a Python API for running and evaluating algorithms.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from lab.external import txt2tags


TABLE_HEAD_BG = '#aaa'
ESCAPE_WORDBREAK = 'xWBRx'

CSS = """\
<style type="text/css">
    body {
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
    }
    blockquote {
        margin: 1em 2em;
        border-left: 2px solid #999;
        font-style: oblique;
        padding-left: 1em;
    }
    blockquote:first-letter {
        margin: .2em .1em .1em 0;
        font-size: 160%%;
        font-weight: bold;
    }
    blockquote:first-line {
        font-weight: bold;
    }
    table {
        border-collapse: collapse;
    }
    td, th {
        <!--border: 1px solid #888;--> <!--Allow tables without borders-->
        padding: 3px 7px 2px 7px;
    }
    th {
        text-align: left;
        padding-top: 5px;
        padding-bottom: 4px;
        background-color: %(TABLE_HEAD_BG)s;
        color: #ffffff;
    }
    hr.heavy {
        height: 2px;
        background-color: black;
    }
</style>
""" % globals()


def raw(s):
    return '""%s""' % s


def _get_config(target):

    config = {}

    # Set the configuration on the 'config' dict.
    config = txt2tags.ConfigMaster()._get_defaults()

    # The Pre (and Post) processing config is a list of lists:
    # [ [this, that], [foo, bar], [patt, replace] ]
    config['postproc'] = []
    config['preproc'] = []

    config['preproc'].append([r'\{(.*?)\|color:(.+?)\}',
                              r'BEGINCOLOR\1SEP\2ENDCOLOR'])

    if target in ['xhtml', 'html']:
        config['encoding'] = 'UTF-8'       # document encoding
        config['toc'] = 0
        config['css-inside'] = 1
        config['css-sugar'] = 1

        # Custom css
        config['postproc'].append([r'</head>', CSS + '</head>'])

        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config['postproc'].append([r'\\\\', r'<br />'])

        # {{red text|color:red}} -> <span style="color:red">red text</span>
        config['postproc'].append([r'BEGINCOLOR(.*?)SEP(.*?)ENDCOLOR',
                                   r'<span style="color:\2">\1</span>'])

        # Allow line-breaking at additional places.
        config['postproc'].append([ESCAPE_WORDBREAK, r'<wbr>'])

    elif target == 'tex':
        # AUtomatically add \usepackage directives.
        config['style'] = []
        config['style'].append('color')
        config['style'].append('geometry')
        config['style'].append('rotating')

        # Do not clear the title page
        config['postproc'].append([r'\\clearpage', r''])

        # Make some color names available e.g. Gray (case-sensitive).
        config['postproc'].append([r'usepackage{color}',
                                   r'usepackage[usenames,dvipsnames]{color}'])

        # Use landscape orientation.
        config['postproc'].append([r'usepackage{geometry}',
                                   r'usepackage[landscape,margin=1.5cm,a4paper]'
                                   '{geometry}'])

        config['encoding'] = 'utf8'
        config['preproc'].append(['€', 'Euro'])

        # Latex only allows whitespace and underscores in filenames if
        # the filename is surrounded by "...". This is in turn only possible
        # if the extension is omitted
        config['preproc'].append([r'\[""', r'["""'])
        config['preproc'].append([r'""\.', r'""".'])

        # For images we have to omit the file:// prefix
        config['postproc'].append([r'includegraphics\{(.*)"file://',
                                   r'includegraphics{"\1'])

        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config['postproc'].append([r'\$\\backslash\$\$\\backslash\$', r'\\\\'])

        # Add default \numtasks command.
        config['postproc'].append([r'\\title',
                    r'\\newcommand{\\numtasks}[1]{\\small{(#1)}}\n\n\\title'])

        # (35) --> \numtasks{35}
        config['postproc'].append([r'\((\d+?)\)', r'\\numtasks{\1}'])

    elif target == 'txt':
        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config['postproc'].append([r'\\\\', '\n'])

    # Disable some filters for all other targets.
    config['postproc'].append([r'BEGINCOLOR(.*?)SEP(.*?)ENDCOLOR', r'\1'])
    config['postproc'].append([ESCAPE_WORDBREAK, r''])

    return config


class Document(object):
    def __init__(self, title='', author='', date='%%date(%Y-%m-%d)'):
        self.title = title
        self.author = author
        self.date = date

        self.text = ''

    def add_text(self, text):
        self.text += text + '\n'

    def __str__(self):
        return self.text

    def render(self, target, options=None):
        # We always want xhtml
        if target == 'html':
            target = 'xhtml'

        # Bug in txt2tags: Titles are not escaped
        if target == 'tex':
            self.title = self.title.replace('_', r'\_')

        # Here is the marked body text, it must be a list.
        txt = self.text.split('\n')

        # Set the three header fields
        headers = [self.title, self.author, self.date]

        config = _get_config(target)

        config['outfile'] = txt2tags.MODULEOUT  # results as list
        config['target'] = target

        if options is not None:
            config.update(options)

        # Let's do the conversion
        try:
            headers = txt2tags.doHeader(headers, config)
            body, toc = txt2tags.convert(txt, config)
            footer = txt2tags.doFooter(config)
            toc = txt2tags.toc_tagger(toc, config)
            toc = txt2tags.toc_formatter(toc, config)
            full_doc = headers + toc + body + footer
            finished = txt2tags.finish_him(full_doc, config)
            result = '\n'.join(finished)

        # Txt2tags error, show the messsage to the user
        except txt2tags.error, msg:
            logging.error(msg)
            result = msg

        # Unknown error, show the traceback to the user
        except:
            result = txt2tags.getUnknownErrorMessage()
            logging.error(result)

        if target == 'tex':
            # Omit hlines for latex. Only keep the first two and last two hlines.
            hline = '\\hline '
            lines = result.splitlines()
            new_lines = []
            table_row = 0
            for line in lines:
                if line.startswith(hline):
                    table_row += 1
                    if table_row in [1, 2]:
                        new_lines.append(line)
                    else:
                        new_lines.append(line[len(hline):])
                else:
                    # Reinsert the last hline (or two if the last row is a
                    # summary row).
                    if table_row >= 3:
                        new_lines.insert(-1, hline)
                        if new_lines[-3].startswith('\\textbf'):
                            new_lines.insert(-3, hline)
                    table_row = 0
                    new_lines.append(line)
            result = '\n'.join(new_lines)

        return result

if __name__ == '__main__':
    doc = Document('MyTitle', 'Max Mustermann')
    doc.add_text('{{red text|color:red}}')
    print doc
    print
    print doc.render('tex')

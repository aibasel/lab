# -*- coding: utf-8 -*-

import logging

from lab.external import txt2tags


TABLE_HEAD_BG = '#aaa'
BLOCKQUOTE_BG = '#ccc'

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

    if target in ['xhtml', 'html']:
        config['encoding'] = 'UTF-8'       # document encoding
        config['toc'] = 0
        config['css-inside'] = 1
        config['css-sugar'] = 1

        # Custom css
        config['postproc'].append([r'</head>', CSS + '</head>'])

        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config['postproc'].append([r'\\\\', r'<br />'])

        # {{Roter Text|color:red}} -> <span style="color:red">Roter Text</span>
        config['postproc'].append([r'\{\{(.*?)\|color:(.+?)\}\}',
                                   r'<span style="color:\2">\1</span>'])

    elif target == 'tex':
        config['style'] = []
        config['style'].append('color')

        # Do not clear the title page
        config['postproc'].append([r'\\clearpage', r''])

        config['postproc'].append([r'usepackage{color}',
                                   r'usepackage[usenames,dvipsnames]{color}'])

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

        # {{Roter Text|color:red}} -> \textcolor{red}{Roter Text}
        config['postproc'].append([r'\\{\\{(.*?)\$\|\$color:(.+?)\\}\\}',
                                   r'\\textcolor{\2}{\1}'])

    elif target == 'txt':
        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config['postproc'].append([r'\\\\', '\n'])

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

        return result

if __name__ == '__main__':
    doc = Document('MyTitle', 'Max Mustermann')
    doc.add_text('{{Roter Text|color:red}}')
    print doc
    print
    print doc.render('tex')

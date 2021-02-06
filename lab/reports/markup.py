import datetime
import logging

import txt2tags


ESCAPE_WORDBREAK = "xWBRx"
ESCAPE_WHITESPACE = "xWHITESPACEx"

CSS = """\
<style type="text/css">
    body {
        font-family: Ubuntu, Helvetica, Arial, sans-serif;
    }
    table {
        border-collapse: collapse;
    }
    table th {
        text-align: left;
        padding-top: 5px;
        padding-bottom: 4px;
        background-color: #aaa;
        color: #ffffff;
    }
</style>
"""

JAVASCRIPT = """\
<script type="text/javascript">
function toggle_element(element) {
    if (element.style.display == "none") {
        element.style.display = "";
    } else {
        element.style.display = "none";
    }
}

function find_next(element, classname) {
    element = element.nextSibling;
    while(element.nodeName != classname)
        element = element.nextSibling;
    return element;
}

function toggle_table(toggle_button) {
    var table = find_next(toggle_button, "TABLE");
    toggle_element(table);
    if (toggle_button.innerHTML == "Show table") {
        toggle_button.innerHTML = "Hide table";
    } else {
        toggle_button.innerHTML = "Show table";
    }
}

function show_table(section) {
    heading = section.children[0];
    var toggle_button = find_next(heading, "BUTTON");
    var table = find_next(toggle_button, "TABLE");
    table.style.display = "";
    toggle_button.innerHTML = "Hide table";
}

function show_main_tables() {
    var names = ["unexplained-errors", "info", "summary"];
    for (var i = 0; i < names.length; i++) {
        var section = document.getElementById(names[i]);
        try {
            show_table(section);
        } catch (e) {
            console.log("No table found for " + names[i]);
        }
    }

    // If there is only one table, show it and hide the button.
    var buttons = document.getElementsByTagName('button');
    var tables = document.getElementsByTagName('table');
    if (buttons.length == 1 && tables.length == 1) {
        tables[0].style.display = "";
        buttons[0].style.display = "none";
    }
}

document.addEventListener("DOMContentLoaded", show_main_tables);
</script>
"""


def escape(text):
    return f'""{text}""'


def _get_config(target):
    config = {}

    # The Pre (and Post) processing config is a list of lists:
    # [ [this, that], [foo, bar], [patt, replace] ]
    config["postproc"] = []
    config["preproc"] = []

    config["preproc"].append([r"\{(.*?)\|color:(.+?)\}", r"BEGINCOLOR\1SEP\2ENDCOLOR"])

    if target == "html":
        config["toc"] = 0

        # Use custom CSS.
        config["postproc"].append([r"</head>", CSS + "</head>"])

        # Add javascript.
        config["postproc"].append([r"</head>", JAVASCRIPT + "</head>"])

        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config["postproc"].append([r"\\\\", r"<br />"])

        # {{red text|color:red}} -> <span style="color:red">red text</span>
        config["postproc"].append(
            [r"BEGINCOLOR(.*?)SEP(.*?)ENDCOLOR", r'<span style="color:\2">\1</span>']
        )

        # Allow line-breaking at additional places.
        config["postproc"].append([ESCAPE_WORDBREAK, r"<wbr>"])

        config["postproc"].append([ESCAPE_WHITESPACE, r"&nbsp;"])

        # Hide tables by default.
        config["postproc"].append(
            [
                r'<table class="tableborder">',
                r'<button type="button" class="toggle-table" '
                'onclick="toggle_table(this)">Show table</button><p></p>\n\n'
                '<table class="tableborder" style="display:none">',
            ]
        )
        # Automatically show tables when their links are clicked.
        config["postproc"].append(
            [
                r'<a href="#(.+?)">',
                r"""<a href="#\1" onclick="show_table("""
                r"""document.getElementById('\1'));">""",
            ]
        )

    elif target == "tex":
        # Automatically add \usepackage directives.
        config["style"] = ["color", "geometry", "rotating"]

        # Do not clear the title page
        config["postproc"].append([r"\\clearpage", r""])

        # Make some color names available, e.g., Gray (case-sensitive).
        config["postproc"].append(
            [r"usepackage{color}", r"usepackage[usenames,dvipsnames]{color}"]
        )

        # Use landscape orientation.
        config["postproc"].append(
            [
                r"usepackage{geometry}",
                r"usepackage[landscape,margin=1.5cm,a4paper]" "{geometry}",
            ]
        )

        config["preproc"].append(["€", "Euro"])

        # Latex only allows whitespace and underscores in filenames if
        # the filename is surrounded by "...". This is in turn only possible
        # if the extension is omitted
        config["preproc"].append([r'\[""', r'["""'])
        config["preproc"].append([r'""\.', r'""".'])

        # For images we have to omit the file:// prefix
        config["postproc"].append(
            [r'includegraphics\{(.*)"file://', r'includegraphics{"\1']
        )

        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config["postproc"].append([r"\$\\backslash\$\$\\backslash\$", r"\\\\"])

        # Add default \numtasks command.
        config["postproc"].append(
            [r"\\title", r"\\newcommand{\\numtasks}[1]{\\small{(#1)}}\n\n\\title"]
        )

        # (35) --> \numtasks{35}
        config["postproc"].append([r"\((\d+?)\)", r"\\numtasks{\1}"])

    elif target == "txt":
        # Allow line breaks, r'\\\\' are 2 \ for regexes
        config["postproc"].append([r"\\\\", "\n"])

    # Disable some filters for all other targets.
    config["postproc"].append([r"BEGINCOLOR(.*?)SEP(.*?)ENDCOLOR", r"\1"])
    config["postproc"].append([ESCAPE_WORDBREAK, r""])
    config["postproc"].append([ESCAPE_WHITESPACE, r" "])

    return config


class Document:
    def __init__(self, title="", author="", date=""):
        self.title = title
        self.author = author
        self.date = date or datetime.datetime.today().strftime("%Y-%m-%d")

        self.text = ""

    def add_text(self, text):
        self.text += text + "\n"

    def __str__(self):
        return self.text

    def render(self, target, options=None):
        # Here is the marked body text, it must be a list.
        body = self.text.split("\n")

        # Set the three header fields
        headers = [self.title, self.author, self.date]

        config = _get_config(target)

        config["infile"] = txt2tags.MODULEIN
        config["outfile"] = txt2tags.MODULEOUT  # results as list
        config["target"] = target

        if options is not None:
            config.update(options)

        try:
            result = "\n".join(txt2tags.convert_file(headers, body, config))
        except txt2tags.error as msg:
            # Txt2tags error, show the message to the user.
            logging.error(msg)
            result = msg
        except Exception:
            # Unknown error, show the traceback to the user.
            result = txt2tags.getUnknownErrorMessage()
            logging.error(result)
            raise

        return result

# -*- coding: utf-8 -*-

from collections import defaultdict


def escape(text):
    return str(text).replace("_", r"\_")


class Document(object):
    def __init__(self, documentclass, *options):
        docclass = r"\documentclass%s{%s}" % (
            self._format_options(options), documentclass)
        self.header = [docclass]
        self.definitions = []
        self.parts = []

    def _format_options(self, options):
        if options:
            return "[%s]" % ",".join(options)
        else:
            return ""

    def add_package(self, package, *options):
        header_line = r"\usepackage%s{%s}" % (
            self._format_options(options), package)
        if header_line not in self.header:
            self.header.append(header_line)

    def add_definition(self, definition):
        self.definitions.append(definition)

    def _render_preamble(self, out=None):
        for block in [self.header, self.definitions]:
            for line in block:
                print >> out, line

    def render(self, out=None):
        for part in self.parts:
            part.prepare(self)

        self._render_preamble(out)
        print >> out
        print >> out, r"\begin{document}"
        for part in self.parts:
            part.render(out)
            print >> out
        print >> out, r"\end{document}"

    def add(self, *new_parts):
        for part in new_parts:
            if isinstance(part, basestring):
                part = Text(part)
            self.parts.append(part)


class LatexObject(object):
    def prepare(self, document):
        pass


class Text(LatexObject):
    def __init__(self, *lines):
        self.lines = lines

    def render(self, out):
        for line in self.lines:
            print >> out, line


class Table(LatexObject):
    def __init__(self, column_styles):
        self.coldesc = "".join(column_styles)
        self.num_columns = 0
        self.vlines = defaultdict(str)
        for part in column_styles:
            if part == "|" or part == "||":
                assert not self.vlines[self.num_columns]
                self.vlines[self.num_columns] = part
            elif part.startswith(("l", "c", "r", "p")):
                self.num_columns += 1
            else:
                assert part.startswith("@")
        self.supertabular = False
        self._head = TableSegment(self)
        self._body = TableSegment(self)
        self._foot = TableSegment(self)
        self.add_cell = self._body.add_cell
        self.add_row = self._body.add_row
        self.add_hline = self._body.add_hline

    def head(self):
        return self._head

    def foot(self):
        return self._foot

    def allow_page_breaks(self):
        self.supertabular = True

    def prepare(self, document):
        if self.supertabular:
            document.add_package("supertabular")

    def render(self, out):
        if self.supertabular:
            print >> out, r"\tablehead{"
            self._head.render(out)
            print >> out, r"}"
            print >> out, r"\tabletail{"
            self._foot.render(out)
            print >> out, r"}"
            print >> out, r"\begin{supertabular}{%s}" % self.coldesc
            self._body.render(out)
            print >> out, r"\end{supertabular}%"
        else:
            print >> out, r"\begin{tabular}{%s}" % self.coldesc
            self._head.render(out)
            self._body.render(out)
            self._foot.render(out)
            print >> out, r"\end{tabular}%"


class TableSegment(object):
    def __init__(self, owner):
        self.owner = owner
        self.lines = []
        self.current_column = 0

    def add_cell(self, text="", span=1, format=None, align=None):
        # Three ways of calling this:
        # - no span/format/align: just a regular cell
        # - align + span: multicolumn that automatically
        #   inherits the appropriate vertical lines from the table
        # - format + span: custom multicolumn that does not inherit
        #   vertical lines
        if align is None and format is None:
            assert span == 1
        if align is not None:
            assert format is None
            format = align + self.owner.vlines[self.current_column + span]
        if format is not None:
            text = r"\multicolumn{%d}{%s}{%s}" % (span, format, text)
        if self.current_column != 0:
            text = "& " + text
        self.lines.append(text)
        self.current_column += span

    def add_row(self):
        self.lines.append(r"\\")
        self.current_column = 0

    def add_hline(self):
        self.lines.append(r"\hline")

    def render(self, out):
        for line in self.lines:
            print >> out, line

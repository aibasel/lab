import sys
import os
import logging
from collections import defaultdict

from lab.reports import Report, ReportArgParser
from lab.external.datasets import missing
from lab import tools


SCORES = ['expansions', 'evaluations', 'search_time', 'total_time',
          'coverage', 'quality']


def get_date_and_time():
    return r"\today\ \thistime"


def escape(text):
    return text.replace('_', r'\_')

def remove_missing(iterable):
    return [value for value in iterable if value is not missing]


class IpcReport(Report):
    def __init__(self, attribute, squeeze=True, page_size='a4', **kwargs):
        """
        attribute: The analyzed attribute (e.g. "expanded")
        squeeze: Use small fonts to fit in more data
        page_size: Set the page size for the latex report
        """
        Report.__init__(self, **kwargs)
        # TODO: rename focus to attribute
        assert attribute in SCORES
        assert page_size in ['a2', 'a3', 'a4']

        self.attribute = attribute
        self.attribute_name = self.attribute
        self.squeeze = squeeze
        self.page_size = page_size

        self.score = 'score_' + self.attribute
        if self.attribute == 'coverage':
            self.attribute = 'cost'
            self.score = 'coverage'
        elif self.attribute == 'quality':
            self.attribute = 'cost'
            self.score = 'quality'

        self.normalize = True
        self.best_value_column = True

    def _tiny_if_squeeze(self):
        if self.squeeze:
            return r"\tiny"
        else:
            return ""

    def _compute_total_scores(self):
        total_scores = {}
        domain_dict = self.data.group_dict('domain')
        for domain, runs in domain_dict.items():
            config_dict = runs.group_dict('config')
            for config in self.configs:
                config_group = config_dict.get(config)
                assert config_group, ('Config %s was not found in dict %s' %
                        (config, config_dict))
                scores = config_group[self.score]
                scores = remove_missing(scores)
                total_score = sum(scores)
                total_scores[config, domain] = total_score
        return total_scores

    def write(self):
        logging.info('Using score attribute "%s"' % self.score)
        logging.info('Adding column with best value: %s' %
                     self.best_value_column)

        # Get set of configs
        self.configs = tools.natural_sort(self.data.group_dict('config').keys())
        self.total_scores = self._compute_total_scores()

        filename = self.get_filename()
        with open(filename, 'w') as file:
            sys.stdout = file
            self.print_report()
            sys.stdout = sys.__stdout__
        logging.info('Wrote file://%s' % filename)

    def print_report(self):
        self.print_header()
        # Group by domain
        self.data.sort('domain', 'problem', 'config')
        domain_dict = self.data.group_dict('domain')
        for index, (domain, group) in enumerate(sorted(domain_dict.items())):
            if index:
                self.print_between_domains()
            self.print_domain(domain, group)
        self.print_summary()
        self.print_footer()

    def print_header(self):
        print r"\documentclass{article}"
        if self.squeeze:
            margin = "0.5cm"
        else:
            margin = "2.5cm"
        print (r"\usepackage[%spaper,landscape,margin=%s]{geometry}" %
                (self.page_size, margin))
        print r"\usepackage{supertabular}"
        print r"\usepackage{scrtime}"
        print r"\begin{document}"
        if self.squeeze:
            print r"\scriptsize"
            print r"\setlength{\tabcolsep}{1pt}"
        print r"\centering"

    def _format_item(self, item):
        if item is None:
            return ""
        elif isinstance(item, float):
            return "%.2f" % item
        else:
            return str(item)

    def _format_result(self, run):
        status = run.get_single_value('status')
        if status == "ok":
            return r"{\tiny %s} \textbf{%s}" % (
                self._format_item(run.get_single_value(self.attribute)),
                self._format_item(run.get_single_value(self.score)))
        else:
            SHORTHANDS = {"unsolved": "uns.", None: "---"}
            return SHORTHANDS.get(status, status)

    def print_domain(self, domain, runs):
        print r"\section*{%s %s --- %s}" % (
            escape(self.attribute_name), escape(domain), get_date_and_time())
        print r"\tablehead{\hline"
        print r"\textbf{prob}"
        for config in self.configs:
            print r"& %s\textbf{%s}" % (self._tiny_if_squeeze(),
                                        escape(config))
        if self.best_value_column:
            print r"& %s\textbf{BEST}" % self._tiny_if_squeeze()
        print r"\\ \hline}"
        print r"\tabletail{\hline}"
        column_desc = "|l|%s|" % ("r" * len(self.configs))
        if self.best_value_column:
            column_desc += "r|"
        print r"\begin{supertabular}{%s}" % column_desc

        quality_total_scores = defaultdict(float)

        for problem, probgroup in sorted(runs.group_dict('problem').items()):
            print r"\textbf{%s}" % problem.replace('.pddl', '')
            scores = []
            # Compute best value if we are comparing quality
            if self.score == 'quality':
                # self.attribute is "cost"
                lengths = probgroup.get(self.attribute)
                lengths = remove_missing(lengths)
                best_length = min(lengths) if lengths else None
            config_dict = probgroup.group_dict('config')
            for config in self.configs:
                run = config_dict.get(config)
                assert len(run) == 1, run
                if self.score == 'quality':
                    length = run.get_single_value('cost')
                    quality = None
                    if length is not missing:
                        if length == 0:
                            assert best_length == 0
                            quality = 1.0
                        else:
                            quality = float(best_length) / length
                        quality_total_scores[config] += quality
                    run['quality'] = quality
                    scores.append(quality)
                print r"& %s" % self._format_result(run)
            if self.best_value_column:
                if self.score == 'quality':
                    best = max(scores) if scores else None
                else:
                    values = probgroup.get(self.attribute)
                    values = remove_missing(values)
                    best = min(values) if values else None
                print r"& %s" % ("---" if best is None else best)
            print r"\\"
        print r"\hline"
        print r"\textbf{total}"
        for config in self.configs:
            if self.score == 'quality':
                score = quality_total_scores[config]
                self.total_scores[config, domain] = score
            print r"& \textbf{%.2f}" % self.total_scores[config, domain]
        if self.best_value_column:
            print r"&"
        print r"\\"
        print r"\end{supertabular}"

    def print_between_domains(self):
        print r"\clearpage"

    def print_summary(self):
        self._print_summary(False, "overall")
        if self.normalize:
            self._print_summary(True, "normalized overall")

    def _print_summary(self, normalize, title):
        print r"\clearpage"
        from collections import defaultdict
        overall = defaultdict(float)

        print r"\section*{%s %s --- %s}" % (
            escape(self.attribute_name), escape(title), get_date_and_time())
        print r"\tablehead{\hline"
        print r"\textbf{domain}"
        for config in self.configs:
            print r"& %s\textbf{%s}" % (self._tiny_if_squeeze(),
                                        escape(config))
        print r"\\ \hline}"
        print r"\tabletail{\hline}"
        print r"\begin{supertabular}{|l|%s|}" % ("r" * len(self.configs))
        domain_dict = self.data.group_dict('domain')
        for domain, group in sorted(domain_dict.items()):
            num_instances = len(group.group_dict('problem'))
            print r"\textbf{%s} {\scriptsize(%s)}" % (domain, num_instances)
            for config in self.configs:
                score = self.total_scores[config, domain]
                if normalize:
                    score = float(score) * 100 / num_instances
                overall[config] += score
                entry = "%.2f" % score
                print r"& %s" % entry
            print r"\\"
        print r"\hline"
        print r"\textbf{overall}"
        for config in self.configs:
            overall_score = overall[config]
            if normalize:
                num_domains = len(domain_dict)
                overall_score = float(overall_score) / num_domains
            print r"& \textbf{%.2f}" % overall_score
        print r"\\ \hline"
        print r"\end{supertabular}"

    def print_footer(self):
        print r"\end{document}"

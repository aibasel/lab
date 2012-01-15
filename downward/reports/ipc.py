import sys
import logging
from collections import defaultdict

from downward.reports import PlanningReport
from lab import tools


SCORES = ['expansions', 'evaluations', 'search_time', 'total_time',
          'coverage', 'quality']


def get_date_and_time():
    return r"\today\ \thistime"


def escape(text):
    return text.replace('_', r'\_')

def remove_missing(iterable):
    return [value for value in iterable if value is not None]


class IpcReport(PlanningReport):
    def __init__(self, squeeze=True, page_size='a4', **kwargs):
        """
        squeeze: Use small fonts to fit in more data
        page_size: Set the page size for the latex report
        """
        PlanningReport.__init__(self, **kwargs)
        assert len(self.attributes) == 1, self.attributes
        self.attribute = self.attributes[0]
        assert self.attribute in SCORES
        assert page_size in ['a2', 'a3', 'a4']

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
        for (domain, config), runs in self.domain_runs.items():
            scores = [run.get(self.score) for run in runs]
            total_score = sum(remove_missing(scores))
            total_scores[config, domain] = total_score
        return total_scores

    def write(self):
        logging.info('Using score attribute "%s"' % self.score)
        logging.info('Adding column with best value: %s' %
                     self.best_value_column)

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
        for index, (domain, problems) in enumerate(self.domains.items()):
            if index:
                self.print_between_domains()
            self.print_domain(domain, problems)
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
        status = run.get('status')
        if status == "ok":
            return r"{\tiny %s} \textbf{%s}" % (
                self._format_item(run.get(self.attribute)),
                self._format_item(run.get(self.score)))
        else:
            SHORTHANDS = {"unsolved": "uns.", None: "---"}
            return SHORTHANDS.get(status, status)

    def print_domain(self, domain, problems):
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

        for problem in problems:
            problem_runs = self.problem_runs[(domain, problem)]
            print r"\textbf{%s}" % problem.replace('.pddl', '')
            scores = []
            for run in problem_runs:
                if self.score == 'quality':
                    quality = run.get('quality')
                    scores.append(quality)
                print r"& %s" % self._format_result(run)
            if self.best_value_column:
                if self.score == 'quality':
                    best = max(scores)
                else:
                    values = [run.get(self.attribute) for run in problem_runs]
                    values = remove_missing(values)
                    best = tools.minimum(values)
                print r"& %s" % ("---" if best is None else best)
            print r"\\"
        print r"\hline"
        print r"\textbf{total}"
        for config in self.configs:
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
        for domain, problems in self.domains.items():
            num_instances = len(problems)
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
                overall_score = float(overall_score) / len(self.domains)
            print r"& \textbf{%.2f}" % overall_score
        print r"\\ \hline"
        print r"\end{supertabular}"

    def print_footer(self):
        print r"\end{document}"

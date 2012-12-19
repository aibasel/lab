import re
import logging
from collections import defaultdict

from lab.reports import TableColumn
from downward.reports.absolute import AbsoluteReport

def _format_banker(value, other_values, min_wins):
    if value == 0:
        color = 'Gray'
    elif value is None or min_wins is None:
        return str(value)
    elif value > 0 ^ min_wins:
        color = 'Green'
    else:
        color = 'Red'
    return '{%s|color:%s}' % (value, color)

def _format_empty(value, other_values, min_wins):
    return ''

class CompareRevisionsReport(AbsoluteReport):
    def __init__(self, revisions, **kwargs):
        AbsoluteReport.__init__(self, **kwargs)
        assert len(revisions) == 2, revisions
        self.revisions = revisions

    def _split_config(self, config):
        pattern = r'([^-]*)-(.*)'
        match = re.match(pattern, config)
        if not match:
            logging.critical('CompareRevisionsReport currently only supports configs ' +
                             'where the same revision is used for all components. ' +
                             'Please use a filter that excludes the config \'%s\'' %
                             config)
        return match.group(1), match.group(2)

    def _get_config_order(self):
        """
        Reorder configs such that it contains only those that for
        self.revisions and the configs that only differ in their revisions
        are next to each other.
        """
        config_order = AbsoluteReport._get_config_order(self)
        new_order = []
        self.config_nicks = []
        for config in config_order:
            _, config_nick = self._split_config(config)
            self.config_nicks.append(config_nick)
            if config not in new_order:
                new_order.extend(['%s-%s' % (rev, config_nick)
                                  for rev in self.revisions])
        return new_order

    def _get_columns(self, existing_columns):
        """Adds diff columns to compare two revisions."""
        columns = []
        last_config_nick = None
        last_revision = None
        for column in existing_columns:
            rev, config_nick = self._split_config(column)
            # insert empty column between two configs
            if last_config_nick is None and columns:
                columns.append(TableColumn('', format_function=_format_empty))
            columns.append(column)
            if last_config_nick is None:
                last_config_nick = config_nick
                assert rev == self.revisions[0], rev
            else:
                assert last_config_nick == config_nick, (last_config_nick, config_nick)
                assert rev == self.revisions[1], rev
                # insert diff column after two revisions for one config
                diff_name = 'diff-%s-%s-%s' % tuple([config_nick] + self.revisions)
                columns.append(TableColumn(diff_name, format_function=_format_banker))
                last_config_nick = None
                last_revision = None
        return columns

    def _get_empty_table(self, attribute=None, title=None, columns=None):
        columns = self._get_columns(columns or self._get_config_order())
        return AbsoluteReport._get_empty_table(self, attribute, title, columns)

    # TODO: Avoid code duplication
    def _get_suite_table(self, attribute):
        assert self.attribute_is_numeric(attribute), attribute
        table = self._get_empty_table(attribute)
        self._add_summary_functions(table, attribute)
        func_name, func = self._get_group_func(attribute)
        num_probs = 0
        self._add_table_info(attribute, func_name, table)
        domain_config_values = defaultdict(list)
        for domain, problems in self.domains.items():
            for problem in problems:
                runs = self.problem_runs[(domain, problem)]
                if (not attribute.absolute and
                        any(run.get(attribute) is None for run in runs)):
                    continue
                num_probs += 1
                for run in runs:
                    value = run.get(attribute)
                    if value is not None:
                        domain_config_values[(domain, run['config'])].append(value)


        # TODO: everything above here is the same as in the base class. Avoid this repetition.



        # If the attribute is absolute (e.g. coverage, search_error) we may have
        # added problems for which not all configs have a value. Therefore, we
        # can only print the number of instances (in brackets after the domain
        # name) if that number is the same for all configs. If not all configs
        # have values for the same number of problems, we write the full list of
        # different problem numbers.
        num_values_lists = defaultdict(list)
        for domain in self.domains:
            for config_nick in self.config_nicks:
                for rev in self.revisions:
                    config = '%s-%s' % (rev, config_nick)
                    values = domain_config_values.get((domain, config), [])
                    num_values_lists[domain].append(str(len(values)))
        num_values_text = {}
        for domain, num_values_list in num_values_lists.items():
            if len(set(num_values_list)) == 1:
                text = num_values_list[0]
            else:
                text = ','.join(num_values_list)
            num_values_text[domain] = text

        for domain in self.domains:
            row_name = domain
            if self.resolution == 'combined':
                row_name = '[""%s"" #%s-%s]' % (domain, attribute, domain)
            row_name = '%s (%s)' % (row_name, num_values_text[domain])
            for config_nick in self.config_nicks:
                domain_values = []
                for rev in self.revisions:
                    config = '%s-%s' % (rev, config_nick)
                    values = domain_config_values[(domain, config)]
                    domain_values.append(func(values))
                    table.add_cell(row_name, config, domain_values[-1])
                if all(v is not None for v in domain_values):
                    diff_value = domain_values[1] - domain_values[0]
                    diff_column_name = 'diff-%s-%s-%s' % tuple([config_nick] + self.revisions)
                    table.add_cell(row_name, diff_column_name, diff_value)
                # Add value to placeholder so it shows up
                table.add_cell(row_name, '', 0)
        table.num_values = num_probs
        return table


import logging

from lab.downward.reports import PlanningReport
from lab.reports import avg, gm
from lab.external.datasets import missing, not_missing


class AbsoluteReport(PlanningReport):
    """
    Write an absolute report about the attribute attribute, e.g.

    || expanded        | fF               | yY               |
    | **gripper     ** | 118              | 72               |
    | **zenotravel  ** | 21               | 17               |
    """
    def __init__(self, resolution, *args, **kwargs):
        """
        resolution: One of "domain" or "problem".
        """
        self.resolution = resolution
        PlanningReport.__init__(self, *args, **kwargs)
        self._orig_groups = None
        self._orig_groups_domain_prob = None

    @property
    def orig_groups(self):
        if not self._orig_groups:
            # Save the unfiltered groups for faster retrieval
            if self.resolution == 'domain':
                self._orig_groups = self.data.groups('config', 'domain')
            else:
                self._orig_groups = self.data.groups('config', 'domain', 'problem')
        return self._orig_groups

    @property
    def orig_groups_domain_prob(self):
        if not self._orig_groups_domain_prob:
            self._orig_groups_domain_prob = self.data.groups('domain', 'problem')
        return self._orig_groups_domain_prob

    def _attribute_is_absolute(self, attribute):
        """
        The domain-wise sum of the values for coverage and *_error even makes
        sense if not all configs have values for those attributes.
        """
        return attribute == 'coverage' or attribute.endswith('_error')

    def _get_filtered_groups(self, attribute):
        """
        for an attribute include or ignore problems for which not all configs
        have this attribute.
        """
        logging.info('Filtering run groups where %s is missing' % attribute)
        del_probs = set()
        for (domain, problem), group in self.orig_groups_domain_prob:
            if any(value is missing for value in group[attribute]):
                del_probs.add(domain + problem)

        def delete_runs_with_missing_attributes(run):
            return not run['domain'] + run['problem'] in del_probs

        data = self.data.filtered(delete_runs_with_missing_attributes)

        if self.resolution == 'domain':
            return data.groups('config', 'domain')
        else:
            return data.groups('config', 'domain', 'problem')

    def _get_group_func(self, attribute):
        """Decide on a group function for this attribute."""
        if 'score' in attribute:
            return 'average', avg
        elif attribute in ['search_time', 'total_time']:
            return 'geometric mean', gm
        return 'sum', sum

    def _get_table(self, attribute):
        table = PlanningReport._get_empty_table(self, attribute)
        func_name, func = self._get_group_func(attribute)

        # If we don't have to filter the runs, we can use the saved group_dict
        if (self.resolution == 'problem' or
            self._attribute_is_absolute(attribute)):
            groups = self.orig_groups
        else:
            groups = self._get_filtered_groups(attribute)
            table.info.append('Only instances where all configurations have a '
                              'value for "%s" are considered.' % attribute)
            table.info.append('Each table entry gives the %s of "%s" for that '
                              'domain.' % (func_name, attribute))
            summary_names = [name.lower()
                             for name, sum_func in table.summary_funcs]
            if len(summary_names) == 1:
                table.info.append('The last row gives the %s across all '
                                  'domains.' % summary_names[0])
            elif len(summary_names) > 1:
                table.info.append('The last rows give the %s across all '
                                  'domains.' % ' and '.join(summary_names))

        def show_missing_attribute_msg(name):
            msg = '%s: The attribute "%s" was not found. ' % (name, attribute)
            logging.debug(msg)

        if self.resolution == 'domain':
            for (config, domain), group in groups:
                values = filter(not_missing, group[attribute])
                if not values:
                    show_missing_attribute_msg(config + '-' + domain)
                    continue
                num_instances = len(group.group_dict('problem'))
                table.add_cell('%s (%s)' % (domain, num_instances), config,
                                            func(values))
        elif self.resolution == 'problem':
            for (config, domain, problem), group in groups:
                value = group.get_single_value(attribute)
                name = domain + ':' + problem
                if value is missing:
                    show_missing_attribute_msg(name)
                    table.add_cell(name, config, None)
                else:
                    table.add_cell(name, config, value)
        return table

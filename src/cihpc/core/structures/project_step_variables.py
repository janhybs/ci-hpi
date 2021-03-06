#!/bin/python3
# author: Jan Hybs

from loguru import logger
import itertools

from cihpc.core.structures.a_project import ComplexClass


class ProjectStepVariables(ComplexClass):
    def __init__(self, kwargs):
        super(ProjectStepVariables, self).__init__(kwargs)

        if not self:
            values = list()

        # single matrix or table
        elif isinstance(kwargs, dict):
            values = [kwargs]

        elif isinstance(kwargs, list):
            values = kwargs
        else:
            raise ValueError('kwargs must be list or dict')

        self.values = values.copy()

    @staticmethod
    def _expand_variables(section):
        def extract_first(iterator):
            return next(iter(iterator))

        def ensure_list(o):
            if isinstance(o, list):
                return o
            return [o]

        section_name = extract_first(section.keys())
        variables = extract_first(section.values())
        names = [extract_first(y.keys()) for y in variables]

        if section_name in ('values', 'table'):
            total = max([len(ensure_list(extract_first(y.values()))) for y in variables])
            values = list()
            for y in variables:
                value = extract_first(y.values())
                if isinstance(value, list):
                    values.append(value)
                else:
                    values.append(list(itertools.repeat(value, total)))

            product = [{names[v_j]: values[v_j][v_i] for v_j in range(len(names))} for v_i in range(total)]
            logger.debug(f'created value matrix with {len(product)} configurations')

        elif section_name == 'matrix':
            values = [ensure_list(extract_first(y.values())) for y in variables]
            product = list(dict(zip(names, x)) for x in itertools.product(*values))
            logger.debug(f'created build matrix with {len(product)} configurations')
            
        else:
            raise Exception(f'Invalid variable type {section_name}')

        return product

    def unique(self):
        import uuid
        return uuid.uuid4().hex

    def expand(self):
        # empty matrix will yield single variables
        if not self.values:
            yield dict(
                __total__=1,
                __current__=1,
                __unique__=self.unique(),
            )

        else:
            for section in self.values:
                var_list = self._expand_variables(section)
                total = len(var_list)
                for i, variables in enumerate(var_list):
                    variables.update(dict(
                        __total__=total,
                        __current__=i + 1,
                        __unique__=self.unique(),
                    ))
                    yield variables

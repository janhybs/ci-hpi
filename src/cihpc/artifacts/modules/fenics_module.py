#!/usr/bin/python
# author: Jan Hybs


import cihpc.artifacts.base as artifact_base
import re


class CollectModule(artifact_base.AbstractCollectModule):
    """
    This module excepts a dictionary as a first and only argument to the
    method process

    It simply merges system wide information and given object together
    Assuming the structure of the output report:
    {
        system:     { ... }
        problem:    { ... }
        result:     { ... }
        git:        { ... }
        timers:     [ { ... }, { ... }, ... ]
        libs:       [ { ... }, { ... }, ... ]
    }
    """

    _floats = [
        re.compile('wall_.+'),
    ]

    _ints = [
        re.compile('num_iter'),
        re.compile('num_cpus'),
        re.compile('size'),
    ]

    def process(self, object, from_file=None):
        # tweak given object a bit

        # rename frames to timers
        object['timers'] = object['frames']
        del object['frames']

        # add version which is in a libs[0]
        object['git'] = dict()
        object['git']['version'] = object['libs'][0]['version']

        # trim libs, duplicate of what is already in a git field
        object['libs'] = object['libs'][1:]

        # converts some fields to ints and floats, saving space and increasing effectivity of the DB
        object = self.convert_fields(object, self._floats, float, recursive=True)
        object = self.convert_fields(object, self._ints, int, recursive=True)

        report = artifact_base.CIHPCReport()
        report.merge(object)

        return artifact_base.CollectResult([report])

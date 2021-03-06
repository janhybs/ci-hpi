#!/usr/bin/python
# author: Jan Hybs


import glob
import importlib
import json
from loguru import logger
import os
from collections import namedtuple

import yaml

from cihpc.cfg.cfgutil import configure_object, configure_string
from cihpc.core.processing.step_collect_parse import process_step_collect_parse
import cihpc.artifacts.base as artifacts_base


def convert_method(type):
    return dict(json=json.loads, yaml=yaml.load).get(type, lambda x: x)


def iter_reports(reports, conversion, is_file):
    index = 0
    for r in reports:
        index += 1

        if is_file:
            with open(r, 'r') as fp:
                try:
                    yield conversion(fp.read()), r
                except Exception as e:
                    continue

        else:
            try:
                yield conversion(r), 'parse-result-%02d' % index
            except Exception as e:
                continue


def process_step_collect(project, step, process_result, format_args=None):
    """
    Function will collect artifacts for the given step
    :type step:           cihpc.core.structures.project_stage.ProjectStage
    :type project:        structures.project.Project
    :type process_result: proc.step.step_shell.ProcessStepResult
    """
    logger.debug(f'collecting artifacts')
    result = namedtuple('CollectResult', ['total', 'items'])(total=[], items=[])

    logger.info(f'loading module {step.collect.module}')
    module = importlib.import_module(step.collect.module)
    CollectModule = module.CollectModule

    # obtain git information
    artifacts_base.CIHPCReport.init(step.collect.repo)

    # enrich result section
    if step.collect.extra:
        extra = configure_object(step.collect.extra, format_args)
        artifacts_base.CIHPCReport.global_problem.update(extra)

    # if ord is set
    if step.index:
        index = configure_object(step.index, format_args)
        artifacts_base.CIHPCReport.global_index.update(index)

    # create instance of the CollectModule
    instance = CollectModule(project.name)  # type: artifacts_base.AbstractCollectModule

    # get either yaml or json
    conversion = convert_method(step.collect.type)

    # --------------------------------------------------

    results = list()
    timers_info = []
    timers_total = 0

    if step.collect.parse:
        reports = process_step_collect_parse(project, step, process_result, format_args)
        logger.debug(f'artifacts: found {len(reports)} reports to process')

        for report, file in iter_reports(reports, conversion, is_file=False):
            try:
                collect_result = instance.process(report, file)
                timers_total += len(collect_result.items)
                timers_info.append((os.path.basename(file), len(collect_result.items)))
                results.append(collect_result)
            except Exception as e:
                logger.exception(
                    f'artifact processing failed (parse method) \n'
                    f'module: {CollectModule}\n'
                    f'file: {file}\n'
                )
                logger.debug(str(report))

        for file, timers in timers_info:
            logger.debug(f'%20s: %5d timers found' % (file, timers))
        logger.debug(f'artifacts: found {timers_total} timer(s) in {len(reports)} file(s)')

        # insert artifacts into db
        if step.collect.save_to_db:
            instance.save_to_db(results)

    if timers_total:
        result.total.append(timers_total)

    if timers_info:
        result.items.append(timers_info)

    # --------------------------------------------------

    results = list()
    timers_info = []
    timers_total = 0

    if step.collect.files:
        files_glob = configure_string(step.collect.files, format_args)
        files = glob.glob(files_glob, recursive=True)
        logger.debug(f'artifacts: found {len(files)} files to process')

        for report, file in iter_reports(files, conversion, is_file=True):
            try:
                collect_result = instance.process(report, file)
                timers_total += len(collect_result.items)
                timers_info.append((os.path.basename(file), len(collect_result.items)))
                results.append(collect_result)
            except Exception as e:
                logger.warning(
                    f'artifact processing failed (files method) \n'
                    f'module: {CollectModule}\n'
                    f'file: {file}\n'
                )
                logger.debug(str(report))

        for file, timers in timers_info:
            logger.debug(f'%20s: %5d timers found' % (file, timers))
        logger.debug(f'artifacts: found {timers_total} timer(s) in {len(reports)} file(s)')

        # insert artifacts into db
        if step.collect.save_to_db:
            instance.save_to_db(results)

        # move results to they are not processed twice
        if step.collect.move_to:
            move_to = configure_string(step.collect.move_to, format_args)
            logger.debug(f'artifacts: moving {len(files)} files to {move_to}')

            for file in files:
                old_filepath = os.path.abspath(file)

                # customize location and prefix of the dir structure if set
                if step.collect.cut_prefix:
                    new_rel_filepath = old_filepath.replace(step.collect.cut_prefix, '').lstrip('/')
                    new_dirname = os.path.join(
                        move_to,
                        os.path.dirname(new_rel_filepath),
                    )
                    new_filepath = os.path.join(new_dirname, os.path.basename(file))
                    os.makedirs(new_dirname, exist_ok=True)
                    os.rename(old_filepath, new_filepath)
                else:
                    new_filepath = os.path.join(
                        move_to,
                        os.path.basename(file)
                    )
                    os.makedirs(move_to, exist_ok=True)
                    os.rename(old_filepath, new_filepath)

    if timers_total:
        result.total.append(timers_total)

    if timers_info:
        result.items.append(timers_info)

    return result

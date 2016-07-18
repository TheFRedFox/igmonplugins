#!/usr/bin/env python
#
# Nagios systemd service status check
#
# This is a Nagios script to check all services know to "systemd".
# It checks for anomalies of those services like the ones not anymore
# defined but still running, and them being dead.  Normally returns
# at most warning, if no critical services are specified.  Returns
#
# * critical when a critical service is failed
# * warning when a critical service is not running
# * warning when a non-critical service is failed
# * warning for other anomalies.
#
# Copyright (c) 2016, InnoGames GmbH
#

import subprocess
import sys

from argparse import ArgumentParser


command = 'systemctl --all --no-legend --no-pager list-units'


class Problem:
    """Enum for problems that can apply to the services"""

    # From more important to less
    failed = 0
    dead = 1
    not_loaded_but_not_inactive = 2
    not_loaded_but_not_dead = 3


def parse_args():
    """Parse the arguments

    We are returning them as a dict for callers convenience.
    """
    parser = ArgumentParser()
    parser.add_argument(
        '-s',
        action='append',
        dest='critical_services',
        default=[],
        help='service to return critical when failed',
    )

    return vars(parser.parse_args())


def main(critical_services):
    """The main program"""

    try:
        output = subprocess.check_output(command.split())
    except subprocess.CalledProcessError as error:
        print('UNKNOWN: ' + str(error))
        sys.exit(3)

    criticals = []
    warnings = []
    for line in output.splitlines():
        service_split = line.strip().split(None, 4)
        service_name = service_split[0]
        problem = check_service(*service_split[1:4])

        if problem is not None:
            if service_name in critical_services:
                if problem == Problem.failed:
                    criticals.append((problem, service_name))
                else:
                    warnings.append((problem, service_name))
            elif problem != Problem.dead:
                warnings.append((problem, service_name))

    criticals.sort()
    warnings.sort()

    if criticals:
        print('CRITICAL: ' + get_message(criticals + warnings))
        sys.exit(2)
    elif warnings:
        print('WARNING: ' + get_message(warnings))
        sys.exit(1)
    else:
        print('OK')
        sys.exit(0)


def check_service(serv_load, serv_active, serv_sub):
    """Detect problems of a service"""
    if serv_load == 'loaded':
        if serv_active == 'failed' or serv_sub == 'failed':
            return Problem.failed

        if serv_sub == 'dead':
            return Problem.dead
    else:
        if serv_active != 'inactive':
            return Problem.not_loaded_but_not_inactive

        if serv_sub != 'dead':
            return Problem.not_loaded_but_not_dead


def get_message(problems):
    """Format the message to print out"""
    problem_names = {
        v: k.replace('_', ' ')
        for k, v in vars(Problem).items()
        if isinstance(v, int)
    }
    message = ''
    last_problem = None
    for problem, service in problems:
        if problem != last_problem:
            message += problem_names[problem] + ': '
            last_problem = problem
        message += service + ' '

    return message


if __name__ == '__main__':
    main(**parse_args())
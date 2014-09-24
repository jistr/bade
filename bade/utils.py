# -*- coding: utf-8 -*-

import click
import logging
import os
import pipes
import re
import subprocess
import time
import types


LOG = logging.getLogger('bade')


class ExecutionError(RuntimeError):
    def __init__(self, *args, **kwargs):
        self.stdout = kwargs.pop('stdout')
        self.stderr = kwargs.pop('stderr')
        super(ExecutionError, self).__init__(*args, **kwargs)


# taken from Kanzo (https://github.com/paramite/kanzo) and simplified
def execute(cmd, workdir=None, can_fail=True, log=True):
    """
    Runs shell command cmd. If can_fail is set to True RuntimeError is raised
    if command returned non-zero return code. Otherwise returns return code
    and content of stdout and content of stderr.
    """
    log_msg = ['Executing command: %s' % cmd]

    proc = subprocess.Popen(cmd, cwd=workdir, shell=True, close_fds=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()

    if proc.returncode and can_fail:
        raise ExecutionError('Failed to execute command: %s' % cmd,
                             stdout=out, stderr=err)
    return proc.returncode, out, err


# taken from Kanzo (https://github.com/paramite/kanzo)
def retry(count=1, delay=0, retry_on=Exception):
    """Decorator which tries to run specified callable if the previous
    run ended by given exception. Retry count and delays can be also
    specified.
    """
    if count < 0 or delay < 0:
        raise ValueError('Count and delay has to be positive number.')

    def decorator(func):
        def wrapper(*args, **kwargs):
            tried = 0
            while tried <= count:
                try:
                    return func(*args, **kwargs)
                except retry_on:
                    if tried >= count:
                        raise
                    if delay:
                        time.sleep(delay)
                    tried += 1
        wrapper.func_name = func.func_name
        return wrapper
    return decorator


def shout(msg, verbose=False, nl=True, level='info'):
    getattr(LOG, level)(msg)
    if verbose:
        click.echo('[{0}] {1}'.format(level, msg), nl=nl)


class PuppetFile(object):
    """Puppetfile parser"""
    _content = {}

    def __init__(self, repo):
        self._fpath = os.path.join(
            os.path.abspath(repo),
            'Puppetfile'
        )

    def __getitem__(self, key):
        return self._content[key]

    def __setitem__(self, key, value):
        self._content[key] = value

    def __contains__(self, item):
        return item in self._content

    def __iter__(self):
        return iter(self._content.keys())

    def keys(self):
        return self._content.keys()

    def values(self):
        return self._content.values()

    def items(self):
        return self._content.items()

    def load(self, source=None):
        """Loads modules information from Puppetfile 'source'."""
        # TO-DO: Implement smarter parser
        re_head = re.compile(
            r'^mod\s+["\'](?P<name>[\w\-]+)["\']\s*,\s*\n$'
        )
        re_info = re.compile(
            r'\s+\:(?P<key>\w+)'
                r'\s*=>\s*'
            r'["\'](?P<value>[\w\-\/\.\:]+)["\']\s*,?\s*\n$'
        )
        fpath = source or self._fpath
        with open(fpath) as puppetfile:
            mod = None
            for line in puppetfile:
                match = re_head.match(line)
                if match:
                    mod = match.group('name')
                    continue
                match = re_info.match(line)
                if match:
                    mod_dict = self._content.setdefault(mod, {})
                    key = match.group('key')
                    value = match.group('value')
                    mod_dict[key] = value

    def save(self, destination=None):
        """Saves modules information to Puppetfile 'destination'."""
        fmt_head = "mod '{name}',\n"
        fmt_info = "  :{key} => '{value}'"

        fpath = destination or self._fpath
        with open(fpath, 'w') as puppetfile:
            for module in sorted(self._content.keys()):
                puppetfile.write(fmt_head.format(name=module))
                keys = self._content[module].keys()
                for key in sorted(self._content[module].keys()):
                    value = self._content[module][key]
                    puppetfile.write(
                        fmt_info.format(key=key, value=value)
                    )
                    keys.remove(key)
                    puppetfile.write(',\n' if keys else '\n\n')

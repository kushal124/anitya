# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import re
import socket
# sre_constants contains re exceptions
import sre_constants
import urllib2

import requests
import anitya
import anitya.app
from anitya.lib.exceptions import AnityaPluginException


REGEX = b'%(name)s(?:[-_]?(?:minsrc|src|source))?[-_]([^-/_\s]+?)(?i)(?:[-_]'\
    '(?:minsrc|src|source))?\.(?:tar|t[bglx]z|tbz2|zip)'


class BaseBackend(object):
    ''' The base class that all the different backend should extend. '''

    name = None
    examples = None

    @classmethod
    def get_version(self, project):  # pragma: no cover
        ''' Method called to retrieve the latest version of the projects
        provided, project that relies on the backend of this plugin.

        :arg Project project: a :class:`model.Project` object whose backend
            corresponds to the current plugin.
        :return: the latest version found upstream
        :return type: str
        :raise AnityaPluginException: a
            :class:`anitya.lib.exceptions.AnityaPluginException` exception
            when the version cannot be retrieved correctly

        '''
        pass

    @classmethod
    def get_versions(self, project):  # pragma: no cover
        ''' Method called to retrieve all the versions (that can be found)
        of the projects provided, project that relies on the backend of
        this plugin.

        :arg Project project: a :class:`model.Project` object whose backend
            corresponds to the current plugin.
        :return: a list of all the possible releases found
        :return type: list
        :raise AnityaPluginException: a
            :class:`anitya.lib.exceptions.AnityaPluginException` exception
            when the versions cannot be retrieved correctly

        '''
        pass

    @classmethod
    def get_ordered_versions(self, project):
        ''' Method called to retrieve all the versions (that can be found)
        of the projects provided, ordered from the oldest to the newest.

        :arg Project project: a :class:`model.Project` object whose backend
            corresponds to the current plugin.
        :return: a list of all the possible releases found
        :return type: list
        :raise AnityaPluginException: a
            :class:`anitya.lib.exceptions.AnityaPluginException` exception
            when the versions cannot be retrieved correctly

        '''
        vlist = self.get_versions(project)
        return anitya.order_versions(vlist)

    @classmethod
    def call_url(self, url):
        ''' Dedicated method to query a URL.

        It is important to use this method as it allows to query them with
        a defined user-agent header thus informing the projects we are
        querying what our intentions are.

        :arg url: the url to request (get).
        :type url: str
        :return: the request object corresponding to the request made
        :return type: Request
        '''
        user_agent = 'Anitya %s at upstream-monitoring.org' % \
            anitya.app.__version__
        from_email = anitya.app.APP.config.get('ADMIN_EMAIL')

        if url.startswith('ftp://') or url.startswith('ftps://'):
            socket.setdefaulttimeout(30)

            req = urllib2.Request(url)
            req.add_header('User-Agent', user_agent)
            req.add_header('From', from_email)
            resp = urllib2.urlopen(req)
            content = resp.read()

            return content

        else:
            headers = {
                'User-Agent': user_agent,
                'From': from_email,
            }

            return requests.get(url, headers=headers)


def get_versions_by_regex(url, regex, project):
    ''' For the provided url, return all the version retrieved via the
    specified regular expression.

    '''

    try:
        req = BaseBackend.call_url(url)
    except Exception, err:
        anitya.LOG.debug('%s ERROR: %s' % (project.name, err.message))
        raise AnityaPluginException(
            'Could not call : "%s" of "%s"' % (url, project.name))

    if not isinstance(req, basestring):
        req = req.text

    return get_versions_by_regex_for_text(req, url, regex, project)


def get_versions_by_regex_for_text(text, url, regex, project):
    ''' For the provided text, return all the version retrieved via the
    specified regular expression.

    '''

    try:
        upstream_versions = list(set(re.findall(regex, text)))
    except sre_constants.error:  # pragma: no cover
        raise AnityaPluginException(
            "%s: invalid regular expression" % project.name)

    for index, version in enumerate(upstream_versions):
        if type(version) == tuple:
            version = ".".join([v for v in version if not v == ""])
            upstream_versions[index] = version
        if " " in version:
            raise AnityaPluginException(
                "%s: invalid upstream version:>%s< - %s - %s " % (
                    project.name, version, url, regex))
    if len(upstream_versions) == 0:
        raise AnityaPluginException(
            "%(name)s: no upstream version found. - %(url)s -  "
            "%(regex)s" % {
                'name': project.name, 'url': url, 'regex': regex})

    return upstream_versions

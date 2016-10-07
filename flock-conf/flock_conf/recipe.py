import logging
import os

from configparser import ConfigParser
import zc.buildout


class X:
    def __init__(self, config):
        self.config = config

    def get_distinct_users(self):
        users = dict()

        for section in self.config.sections():
            users.update(
                {
                    k: v
                    for k, v in self.config[section].items()
                    if k.startswith('@')
                }
            )

        return users


class Config:

    def __init__(self, buildout, name, options):
        self.name = name
        self.options = options

        self.logger = logging.getLogger(self.name)

        self.clusters_conf = os.path.join(
            buildout['buildout']['directory'],
            options['clusters_conf'],
        )

        config = ConfigParser()
        config.read(self.clusters_conf)

        x = X(config)
        self.options.update(x.get_distinct_users())

        self.options['all_user_ids'] = (
            '\n'.join(
                '    # {}\n    {}'.format(k, v)
                for k, v in sorted(x.get_distinct_users().items())
            )
        )

        self.logger.info(self.options)

        # self.logger.info(self.config.sections())

    def install(self):

        return ()

    def update(self):
        self.logger.info('Update')

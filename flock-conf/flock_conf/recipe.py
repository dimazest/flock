import logging
import os

from configparser import ConfigParser
from .expander import Expander


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

        ex = Expander(config)
        self.options.update(ex.get_distinct_users())

        self.options['all_user_ids'] = (
            '\n'.join(
                '    # {}\n    {}'.format(k, v)
                for k, v in sorted(ex.get_distinct_users().items())
            )
        )

    def install(self):
        return ()

    def update(self):
        pass

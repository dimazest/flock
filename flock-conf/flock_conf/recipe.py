import base64
import logging
import os

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

        ex = Expander.from_file(self.clusters_conf)
        self.options.update(ex.get_distinct_users())

        self.options['all_user_ids'] = (
            '\n'.join(
                '    # {}\n    {}'.format(k, v)
                for k, v in sorted(ex.get_distinct_users().items())
            )
        )

        self.options['SECRET_KEY'] = base64.b64encode(os.urandom(24)).decode('utf-8')

    def install(self):
        return ()

    def update(self):
        pass

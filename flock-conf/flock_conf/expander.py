from itertools import chain
from configparser import ConfigParser


class Expander:
    def __init__(self, config):
        self.config = config

    def get_distinct_users(self):
        users = dict()

        for section in self.config.sections():
            users.update(
                {
                    k[1:]: v  # Omit the @ sign.
                    for k, v in self.config[section].items()
                    if k.startswith('@')
                }
            )

        return users

    @classmethod
    def from_file(cls, path):
        config = ConfigParser()
        config.read(path)

        return cls(config)

    def users_without_ids(self):
        for section in self.config.sections():
            for k, v in self.config[section].items():
                if not k.startswith('@'):
                    continue

                if not v.strip():
                    yield k

    def user_labels(self):
        """Build a mapping from items to the labels they belong to."""
        result = dict()
        super_labels = dict()

        for section in self.config.sections():
            if not section.startswith('@@'):
                continue

            for screen_name, id_ in self.config[section].items():

                if (not screen_name.startswith('@')) or not id_.strip():
                    continue

                id_ = int(id_)

                result.setdefault(id_, set()).update(
                    [
                        screen_name,
                        section,
                    ]
                )

                super_labels.setdefault(section, set()).add(id_)

            include = self.config[section].get('include', None)
            if include is not None:
                include_sections = tuple(
                    chain.from_iterable(
                        l.split()
                        for l in include.splitlines()
                    )
                )

                for include_section in include_sections:
                    for other_id in super_labels[include_section]:
                        result[other_id].add(section)
                        super_labels.setdefault(section, set()).add(other_id)

        for key in list(result.keys()):
            result[key] = sorted(result[key])

        return result

from configparser import ConfigParser


class Expander:
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

    def expand():
        """Build a mapping from items to the labels they belong to."""
        result = dict()

        for section in self.config.sections():
            pass

        return result

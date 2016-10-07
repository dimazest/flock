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

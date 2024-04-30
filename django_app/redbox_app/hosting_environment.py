import environ

env = environ.Env()


class HostingEnvironment:
    @staticmethod
    def is_local() -> bool:
        return env.str("ENVIRONMENT", "").upper() == "LOCAL"

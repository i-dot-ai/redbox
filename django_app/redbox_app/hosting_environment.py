import environ

env = environ.Env()


class HostingEnvironment:
    @staticmethod
    def is_deployed() -> bool:
        return env.str("ENVIRONMENT", "").upper() in ("DEV", "PROD", "PREPROD")

    @staticmethod
    def is_local() -> bool:
        return env.str("ENVIRONMENT", "").upper() == "LOCAL"

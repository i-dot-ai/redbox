import ast
import os
import subprocess

import environ

env = environ.Env()


class HostingEnvironment:
    @staticmethod
    def is_beanstalk() -> bool:
        """is this application deployed to AWS Elastic Beanstalk?"""
        return os.path.exists("/opt/elasticbeanstalk")

    @staticmethod
    def get_beanstalk_environ_vars() -> dict:
        """get env vars from ec2
        https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/custom-platforms-scripts.html
        """
        completed_process = subprocess.run(
            ["/opt/elasticbeanstalk/bin/get-config", "environment"],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )

        return ast.literal_eval(completed_process.stdout)

    @staticmethod
    def is_local() -> bool:
        return env.str("ENVIRONMENT", "").upper() == "LOCAL"

    @staticmethod
    def is_test() -> bool:
        return env.str("ENVIRONMENT", "").upper() == "TEST"

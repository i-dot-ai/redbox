import json
import logging
import os

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
    try:
        # read FILE_EXPIRY_IN_SECONDS from environment

        logger.info("environment variable:  %s", os.environ['FILE_EXPIRY_IN_SECONDS'])

        # connect to pg database to find relevant files

        # connect to elastic database to delete relevant files

        # update pg database files as required

        # log success and errors + communicate (Slack?)

        return {
            'statusCode': 200,
            'body': json.dumps(os.environ['FILE_EXPIRY_IN_SECONDS'])
        }
    except Exception as ex:
        logger.error(f"Exception {ex} occurred")
        return {"message": f"General exception {ex} occurred. Exiting..."}

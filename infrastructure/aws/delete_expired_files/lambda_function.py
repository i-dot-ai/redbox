import json
import logging
import os

import pg8000.dbapi
from elasticsearch import Elasticsearch, NotFoundError

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):  # noqa: ARG001 unused args
    try:
        # Read FILE_EXPIRY_IN_SECONDS from environment
        logger.info("environment variable:  %s", os.environ["FILE_EXPIRY_IN_SECONDS"])
        # FILE_EXPIRY_IN_SECONDS = os.environ["FILE_EXPIRY_IN_SECONDS"]

        # Connect to pg database to find relevant files
        db_params = {
            "host": os.environ["POSTGRES_HOST"],
            "database": os.environ["POSTGRES_DB"],
            "user": os.environ["POSTGRES_USER"],
            "password": os.environ["POSTGRES_PASSWORD"],
        }
        try:
            connection = pg8000.dbapi.Connection(**db_params)
            cursor = connection.cursor()

            cursor.execute("""SELECT redbox_core_file.core_file_uuid
                FROM redbox_core_file 
                INNER JOIN redbox_core_user
                ON redbox_core_file.user_id = redbox_core_user.id
                WHERE redbox_core_user.email='rachael.robinson@cabinetoffice.gov.uk'""")
            for file_id in cursor.fetchall():
                logger.info("file uuid:  %s", file_id)

                # Connect to elastic database to delete relevant files
                client = Elasticsearch(cloud_id=os.environ["ELASTIC__CLOUD_ID"], api_key=os.environ["ELASTIC__API_KEY"])

                try:
                    resp = client.get(index="redbox-data-file", id=str(file_id))
                    logger.info("File: %s", resp)
                except NotFoundError:
                    logger.info("file/%s not found", file_id)

            connection.close()
            logger.info("Database connection closed.")

        except pg8000.dbapi.DatabaseError:
            logger.exception("Error connecting to the postgres database")

        # TODO: log success and errors + communicate (Slack?)  # noqa: TD003, TD002 no author or issue link

        return {"statusCode": 200, "body": json.dumps(os.environ["FILE_EXPIRY_IN_SECONDS"])}
    except Exception as exception:
        logger.exception("Exception occurred")
        return {"message": f"General exception {exception} occurred. Exiting..."}

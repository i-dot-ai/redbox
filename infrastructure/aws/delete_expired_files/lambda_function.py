import json
import logging
import os

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
import psycopg

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):
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
            connection = psycopg.connect(**db_params)
            cursor = connection.cursor()

            # For now to test the connection
            cursor.execute("""SELECT id FROM redbox_core_user WHERE email='rachael.robinson@cabinetoffice.gov.uk'""")
            for user_id in cursor.fetchall():
                logger.info("user uuid:  %s", user_id)

                # Connect to elastic database to delete relevant files
                client = Elasticsearch(cloud_id=os.environ["ELASTIC__CLOUD_ID"], api_key=os.environ["ELASTIC__API_KEY"])
                results = scan(
                    client=client,
                    index='redbox-data-file',
                    query={
                        "query":{
                            "bool": {
                                "should": [
                                    {"term": {"creator_user_uuid.keyword": str(user_id)}},
                                    {"term": {"metadata.creator_user_uuid.keyword": str(user_id)}},
                                    ]
                                }
                            }
                        },
                    _source=False,
                )

                for r in results:
                    logger.info("file uuid:  %s", r["_id"])
                    # update pg database files as required

        except psycopg.Error as error:
            print(f"Error connecting to the postgres database: {error}")

        finally:
            if connection:
                cursor.close()
                connection.close()
                print("Database connection closed.")

        # TODO: log success and errors + communicate (Slack?)

        return {
            'statusCode': 200,
            'body': json.dumps(os.environ["FILE_EXPIRY_IN_SECONDS"])
        }
    except Exception as ex:
        logger.error(f"Exception {ex} occurred")
        return {"message": f"General exception {ex} occurred. Exiting..."}

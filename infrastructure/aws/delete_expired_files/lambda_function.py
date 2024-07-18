import json
import logging
import os

import boto3
import pg8000.dbapi
from elasticsearch import Elasticsearch
from pg8000.native import literal

logger = logging.getLogger()
logger.setLevel("INFO")


def lambda_handler(event, context):  # noqa: ARG001 unused args
    try:
        file_expiry_in_seconds = os.environ["FILE_EXPIRY_IN_SECONDS"]

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

            cursor.execute(
                # using parameters doesn't work for this statement
                # literal() used to remove risk of SQL injection in f-string
                f"""SELECT id, core_file_uuid, original_file
                        FROM redbox_core_file
                        WHERE redbox_core_file.last_referenced <
                            (NOW() - INTERVAL '{literal(int(file_expiry_in_seconds))} seconds')
                        AND redbox_core_file.status NOT IN ('deleted', 'errored')
                """  # noqa: S608
            )

            successful_ids = []
            failed_ids = []

            for django_id, core_id, name in cursor.fetchall():
                logger.info("file uuid:  %s", core_id)

                # Connect to elastic database and s3 bucket to delete relevant files
                elastic_client = Elasticsearch(
                    cloud_id=os.environ["ELASTIC__CLOUD_ID"], api_key=os.environ["ELASTIC__API_KEY"]
                )
                s3 = boto3.client("s3")

                if elastic_client.exists(index="redbox-data-file", id=str(core_id)):
                    logger.info("deleting file uuid:  %s", core_id)

                    # delete chunks
                    elastic_client.delete_by_query(
                        index="redbox-data-file",
                        body={
                            "query": {
                                "bool": {
                                    "must": [
                                        {
                                            "bool": {
                                                "should": [
                                                    {"term": {"parent_file_uuid.keyword": str(core_id)}},
                                                    {"term": {"metadata.parent_file_uuid.keyword": str(core_id)}},
                                                ]
                                            }
                                        },
                                    ]
                                }
                            }
                        },
                    )

                    # delete file from elastic
                    elastic_client.delete(index="redbox-data-file", id=str(core_id))

                    # delete from S3
                    s3.delete_object(
                        Bucket=os.environ["BUCKET_NAME"],
                        Key=str(name),
                    )

                    logger.info("deleted file uuid: %s", core_id)
                    successful_ids.append(django_id)
                else:
                    logger.info("file uuid not found:  %s", core_id)

                    # delete from S3
                    logger.info("file name: %s", name)
                    if name:  # if not, there isn't a file in S3
                        s3.delete_object(
                            Bucket=os.environ["BUCKET_NAME"],
                            Key=str(name),
                        )

                    failed_ids.append(django_id)

            if successful_ids:
                logger.info(tuple(literal(i)[1:-1] for i in successful_ids))
                cursor.execute(
                    f"""UPDATE redbox_core_file SET status = 'deleted'
                        WHERE id IN {tuple(literal(i)[1:-1] for i in successful_ids)}
                    """  # noqa: S608
                )

            if failed_ids:
                logger.info(tuple(literal(i)[1:-1] for i in failed_ids))
                cursor.execute(
                    f"""UPDATE redbox_core_file SET status = 'errored'
                        WHERE id IN {tuple(literal(i)[1:-1] for i in failed_ids)}
                    """  # noqa: S608
                )

            connection.commit()
            connection.close()
            logger.info("Database connection closed.")

        except pg8000.dbapi.DatabaseError:
            logger.exception("Error connecting to the postgres database")

        # TODO: log success and errors + communicate (Slack?)  # noqa: TD003, TD002 no author or issue link

        return {"statusCode": 200, "body": json.dumps(os.environ["FILE_EXPIRY_IN_SECONDS"])}
    except Exception as exception:
        logger.exception("Exception occurred")
        return {"message": f"General exception {exception} occurred. Exiting..."}

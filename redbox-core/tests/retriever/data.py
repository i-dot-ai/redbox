from uuid import uuid4


from redbox.models.chain import RedboxQuery
from redbox.models.file import ChunkResolution
from redbox.test.data import RedboxTestData, generate_test_cases

ALL_CHUNKS_RETRIEVER_CASES = [
    test_case
    for generator in [
        generate_test_cases(
            query=RedboxQuery(
                question="Irrelevant Question",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[RedboxTestData(8, 8000)],
            test_id="Successful Path",
        )
    ]
    for test_case in generator
]

PARAMETERISED_RETRIEVER_CASES = [
    test_case
    for generator in [
        generate_test_cases(
            query=RedboxQuery(
                question="Irrelevant Question",
                s3_keys=["s3_key"],
                user_uuid=uuid4(),
                chat_history=[],
                permitted_s3_keys=["s3_key"],
            ),
            test_data=[RedboxTestData(8, 8000, ChunkResolution.normal)],
            test_id="Successful Path",
        )
    ]
    for test_case in generator
]

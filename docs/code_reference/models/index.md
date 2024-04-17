# Models

Throughout Redbox Pydantic models are used to define the structure of the data that is being passed around. This is done to ensure that the data is in the correct format and to provide a level of type safety when passing between Microservices, Database and the API.

In combination with FastAPI, Pydantic models are used to define the structure of the request and response bodies for the API endpoints. It also generates the OpenAPI documentation for the API.

To save all all these models we created a `PersistableModel` class that all models that are saved to the database inherit from. This class adds the following fields to all models:

::: redbox.models.base.PersistableModel
    options:
            members:
                - uuid
                - created_datetime
                - creator_user_uuid
                - model_type
    
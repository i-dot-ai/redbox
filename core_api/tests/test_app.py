from core_api.src.app import env


def test_get_health(app_client):
    """
    Given that the app is running
    When I call /health
    I Expect to see the docs
    """
    response = app_client.get("/health")
    assert response.status_code == 200


def test_read_model(client):
    """
    Given that I have a model in the database
    When I GET /model
    I Expect model-info to be returned
    """
    response = client.get("/model")
    assert response.status_code == 200
    assert response.json() == {
        "model": env.embedding_model,
        "vector_size": 768,
    }


def test_embed_sentences_422(client):
    """
    Given that I have a model in the database
    When I POST a mall-formed payload to /embedding
    I Expect a 422 error
    """
    response = client.post(
        "/embedding",
        json={"not": "a well formed payload"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be a valid list"


def test_embed_sentences(client):
    """
    Given that I have a model in the database
    When I POST a valid payload consisting of some sentenced to embed to
    /embedding
    I Expect a 200 response

    N.B. We are not testing the content / efficacy of the model in this test.
    """
    response = client.post(
        "/embedding",
        json=["I am the egg man", "I am the walrus"],
    )
    assert response.status_code == 200

def test_read_all_models(client, example_model_db):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I GET all models /models
    I Expect a list of just one model, paraphrase-albert-small-v2, to be returned
    """
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {
                "max_seq_length": 100,
                "model": "paraphrase-albert-small-v2",
                "vector_size": 768,
            }
        ]
    }


def test_read_one_model(client, example_model_db):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I GET this one model /models/paraphrase-albert-small-v2
    I Expect a single model, paraphrase-albert-small-v2, to be returned
    """
    response = client.get("/models/paraphrase-albert-small-v2")
    assert response.status_code == 200
    assert response.json() == {
        "max_seq_length": 100,
        "model": "paraphrase-albert-small-v2",
        "vector_size": 768,
    }


def test_read_models_404(client, example_model_db):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I GET a non-existent model /models/not-a-model
    I Expect a 404 error
    """
    response = client.get("/models/not-a-model")
    assert response.status_code == 404
    assert response.json() == {"detail": "Model not-a-model not found"}


def test_embed_sentences_422(client):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I POST a mall-formed payload to /models/paraphrase-albert-small-v2/embed
    I Expect a 422 error
    """
    response = client.post(
        "/models/paraphrase-albert-small-v2/embed",
        json={"not": "a well formed payload"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be a valid list"


def test_embed_sentences(client, example_model_db):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I POST a valid payload consisting of some sentenced to embed to
    /models/paraphrase-albert-small-v2/embed
    I Expect a 200 response

    N.B. We are not testing the content / efficacy of the model in this test.
    """
    response = client.post(
        "/models/paraphrase-albert-small-v2/embed",
        json=["I am the egg man", "I am the walrus"],
    )
    assert response.status_code == 200


def test_health_ready(client, example_model_db):
    """
    Given that I have one model, paraphrase-albert-small-v2, in the database
    When I GET the app health /models/health
    I Expect its state to be ready

    N.B. We are not testing the content / efficacy of the model in this test.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["version"] == "0.1.0"

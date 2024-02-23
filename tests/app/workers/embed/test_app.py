def test_read_all_models(client, example_modes):
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == {
        "models": [
            {"max_seq_length": 1, "model": "a", "vector_size": 2},
            {"max_seq_length": 1, "model": "b", "vector_size": 2},
        ]
    }


def test_read_one_model(client, example_modes):
    response = client.get("/models/a")
    assert response.status_code == 200
    assert response.json() == {"max_seq_length": 1, "model": "a", "vector_size": 2}


def test_read_models_404(client, example_modes):
    response = client.get("/models/not-a-model")
    assert response.status_code == 404
    assert response.json() == {"detail": "Model not-a-model not found"}


def test_embed_sentences_422(client):
    response = client.post("/models/a/embed", data={"not": "a well formed payload"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be a valid list"

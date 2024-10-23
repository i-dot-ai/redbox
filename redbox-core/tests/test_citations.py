from uuid import uuid4

import pytest

from redbox.app import Redbox
from redbox.models.chain import AISettings, RedboxQuery, RedboxState


@pytest.mark.asyncio
async def test_citation():
    app = Redbox(debug=False)
    q = RedboxQuery(
        question="@gadget Who is Hello Kitty?",
        s3_keys=[],
        user_uuid=uuid4(),
        chat_history=[],
        ai_settings=AISettings(rag_k=3),
        permitted_s3_keys=[],
    )

    x = RedboxState(
        request=q,
    )

    response = await app.run(x)

    assert len(response.get("text")) > 0
    assert isinstance(response.get("citations"), list)

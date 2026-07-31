import pytest
from loyan.core.loyan_adapter.message import (
    LoyanText, LoyanImage, LoyanAt, LoyanReply,
)
from loyan.core.loyan_adapter.platform.telegram.message import build_send_kwargs


class TestBuildSendKwargs:
    def test_text_only(self):
        segments = [LoyanText(text="Hello")]
        action, kwargs = build_send_kwargs(segments)
        assert action == "text"
        assert kwargs["text"] == "Hello"

    def test_empty_segments(self):
        action, kwargs = build_send_kwargs([])
        assert action == "text"

    def test_image_with_caption(self):
        segments = [LoyanText(text="caption"), LoyanImage(url="https://img.jpg")]
        action, kwargs = build_send_kwargs(segments)
        assert action == "photo"
        assert kwargs["caption"] == "caption"

    def test_mixed_segments(self):
        segments = [
            LoyanText(text="Hello"),
            LoyanAt(target_id="123"),
            LoyanReply(message_id="456"),
        ]
        action, kwargs = build_send_kwargs(segments)
        assert action == "text"
        assert "Hello" in kwargs["text"]

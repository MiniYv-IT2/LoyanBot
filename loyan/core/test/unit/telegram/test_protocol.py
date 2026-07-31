from loyan.core.loyan_adapter.platform.telegram.protocol import update_to_loyan


class TestUpdateToLoyan:
    def test_no_message(self):
        assert update_to_loyan(None, None) is None

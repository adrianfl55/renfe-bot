import os
os.environ["TELEGRAM_TOKEN"] = "123456789:DUMMY_TOKEN_FOR_TESTS"

from models import StationRecord
from bot import build_buy_keyboard


def test_build_buy_keyboard():
    orig = StationRecord(name="Vigo", code="1")
    dest = StationRecord(name="A Coruña", code="2")

    markup = build_buy_keyboard(orig, dest)
    assert markup is not None
    assert len(markup.keyboard) == 2
    assert "https://www.renfe.com/es/es" in markup.keyboard[0][0].url
    assert "https://www.thetrainline.com/es" in markup.keyboard[1][0].url

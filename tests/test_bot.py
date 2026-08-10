from datetime import datetime
from models import StationRecord
from bot import format_station_slug, build_buy_keyboard


def test_format_station_slug():
    assert format_station_slug("A Coruña") == "a-coruna"
    assert format_station_slug("Madrid Puerta De Atocha") == "madrid-puerta-de-atocha"
    assert format_station_slug("Vigo Urzaiz") == "vigo-urzaiz"


def test_build_buy_keyboard():
    orig = StationRecord(name="Vigo", code="1")
    dest = StationRecord(name="A Coruña", code="2")
    dt = datetime(2026, 8, 15)

    markup = build_buy_keyboard(orig, dest, dt)
    assert markup is not None
    assert len(markup.keyboard) == 2
    assert "https://www.thetrainline.com/es/search/vigo/a-coruna/15-08-2026" in markup.keyboard[0][0].url
    assert "https://www.renfe.com/es/es" in markup.keyboard[1][0].url

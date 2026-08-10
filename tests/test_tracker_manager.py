from datetime import datetime
from models import StationRecord
from tracker_manager import TrackerManager, TrackedSearch, MAX_USER_TRACKINGS, MAX_GLOBAL_TRACKINGS


def test_can_add_tracking_limits():
    tm = TrackerManager()
    user_id = 999

    # Initially allowed
    can_add, reason = tm.can_add_tracking(user_id)
    assert can_add is True
    assert reason == ""

    # Add max trackings for user
    for i in range(MAX_USER_TRACKINGS):
        s = TrackedSearch(
            id=0,
            user_id=user_id,
            origin=StationRecord(name="Vigo", code="1"),
            destination=StationRecord(name="Coruña", code="2"),
            departure_date=datetime.now()
        )
        tm.add_tracking(s)

    # Next attempt should be denied for user limit
    can_add, reason = tm.can_add_tracking(user_id)
    assert can_add is False
    assert "límite máximo" in reason

    # Different user can still add
    can_add_other, _ = tm.can_add_tracking(888)
    assert can_add_other is True

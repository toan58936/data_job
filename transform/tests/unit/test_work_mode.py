"""
test_work_mode.py - Unit test cho processor work_mode
"""
import pytest
from transform.src.processors.work_mode import derive_work_mode


@pytest.mark.parametrize("working_time, description, requirements, expected", [
    ("Thứ 2 - Thứ 6 (từ 08:30 đến 18:00)", "", "", ("Onsite", False)),
    ("Làm việc từ xa, Remote", "", "", ("Remote", True)),
    ("Hybrid làm việc", "", "", ("Hybrid", True)),
    ("", "Remote work available", "", ("Remote", True)),
    ("", "", "Work from home", ("Remote", True)),
    ("Onsite tại văn phòng", "", "", ("Onsite", False)),
    ("", "", "", ("Onsite", False)),
    ("", "Hybrid position", "", ("Hybrid", True)),
    ("", "", "Remote is ok", ("Remote", True)),
    ("Work from home allowed", "", "", ("Remote", True)),
    ("", "We have a remote-first culture", "", ("Remote", True)),
])
def test_derive_work_mode(working_time, description, requirements, expected):
    assert derive_work_mode(working_time, description, requirements) == expected
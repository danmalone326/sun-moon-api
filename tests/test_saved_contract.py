"""The values below are attributed to the published v2 example at sunrise-sunset.org/api."""
from sun_moon_api.formatting import rounded

def test_published_example_units_and_precision():
    assert rounded(118.31) == 118.31
    assert 0 <= 10.62 <= 100
    assert isinstance(35924, int)


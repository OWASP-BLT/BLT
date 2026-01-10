from hypothesis import given, strategies as st
from website.models import Project

given_freshness = st.decimals(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)

@given(freshness=given_freshness)
def test_freshness_range(freshness):
    p = Project(freshness=freshness)
    assert 0 <= p.freshness <= 100

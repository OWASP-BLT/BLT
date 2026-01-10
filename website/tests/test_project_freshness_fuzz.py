import random
from website.models import Project

def test_fuzz_freshness():
    for _ in range(100):
        p = Project(
            archived=random.choice([True, False]),
            forked=random.choice([True, False]),
            status=random.choice(["active", "inactive", "lab"]),
        )
        score = p.calculate_freshness()
        assert 0 <= score <= 100

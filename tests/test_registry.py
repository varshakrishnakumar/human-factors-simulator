import pytest

from sim.domain.scenarios import registry


def test_get_all_returns_three_real_scenarios():
    assert len(registry.get_all()) == 3


def test_get_by_id_raises_on_unknown():
    with pytest.raises(KeyError):
        registry.get_by_id(999)


def test_get_by_id_round_trips():
    for s in registry.get_all():
        assert registry.get_by_id(s.id) is s


def test_get_familiarization():
    scenario = registry.get_familiarization()
    assert scenario.is_familiarization is True
    assert scenario.id == 0
    assert len(scenario.linear_checklist.steps) == 4


def test_linear_candidates_match_real_scenarios():
    cands = registry.linear_candidates()
    assert len(cands) == 3
    ids_from_cands = sorted(c.scenario_id for c in cands)
    ids_from_scenarios = sorted(s.id for s in registry.get_all())
    assert ids_from_cands == ids_from_scenarios

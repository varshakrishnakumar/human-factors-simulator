from sim.domain.conditions import balanced_condition


def test_empty_counts_returns_first_key():
    assert balanced_condition("None", {}, ["a", "b", "c"]) == "a"


def test_picks_min_per_experience():
    counts = {("a", "None"): 2, ("b", "None"): 0, ("c", "None"): 1}
    assert balanced_condition("None", counts, ["a", "b", "c"]) == "b"


def test_tie_broken_by_overall_count():
    counts = {
        ("a", "None"): 0, ("b", "None"): 0, ("c", "None"): 0,
        ("a", "Professional"): 5, ("b", "Professional"): 1,
    }
    # All three tie on ("_", "None") = 0. Overall counts: a=5, b=1, c=0.
    assert balanced_condition("None", counts, ["a", "b", "c"]) == "c"


def test_tie_final_fallback_is_list_order():
    counts = {("a", "None"): 0, ("b", "None"): 0}
    assert balanced_condition("None", counts, ["a", "b"]) == "a"


def test_unknown_experience_treated_as_zero():
    counts = {("a", "Known"): 5, ("b", "Known"): 10}
    # "Novel" experience not in counts → both conditions score 0 on first key,
    # tie-broken by overall count. Totals: a=5, b=10. Winner: a.
    assert balanced_condition("Novel", counts, ["a", "b"]) == "a"


def test_empty_condition_keys_returns_empty():
    assert balanced_condition("None", {}, []) == ""

from sim.domain.survey import QUESTIONS


def test_nasa_tlx_questions_use_seven_point_scale():
    assert QUESTIONS
    for question in QUESTIONS:
        assert question.min == 1
        assert question.max == 7
        assert question.default == 4

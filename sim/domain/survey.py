"""NASA-TLX questions as data. Render loop in sim/ui/screens/survey.py iterates
over QUESTIONS; changing wording is a data edit here, not a UI edit."""
from typing import Tuple

from sim.domain.models import SurveyQuestion

QUESTIONS: Tuple[SurveyQuestion, ...] = (
    SurveyQuestion(
        key="nasa_tlx_mental",
        label="Mental demand",
        question="How mentally demanding was operating the console?",
        low_anchor="Very low — easy to think through",
        high_anchor="Very high — had to concentrate hard",
    ),
    SurveyQuestion(
        key="nasa_tlx_temporal",
        label="Temporal demand",
        question="Did you have enough time to do the task well?",
        low_anchor="Very low — plenty of time, never rushed",
        high_anchor="Very high — felt extremely rushed",
    ),
    SurveyQuestion(
        key="nasa_tlx_effort",
        label="Effort",
        question="How hard did you have to work to complete the task?",
        low_anchor="Very low — effortless",
        high_anchor="Very high — had to try very hard",
    ),
    SurveyQuestion(
        key="nasa_tlx_frustration",
        label="Frustration",
        question="How frustrated or annoyed did you feel during the task?",
        low_anchor="Very low — calm and relaxed",
        high_anchor="Very high — very frustrated",
    ),
)

COMMENT_KEYS: Tuple[str, ...] = (
    "tlx_mental_comment",
    "tlx_temporal_comment",
    "tlx_effort_comment",
    "tlx_frustration_comment",
    "general_comment",
)

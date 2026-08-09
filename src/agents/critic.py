from __future__ import annotations

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_llm
from ..schemas.critique import PaperCritique
from ..schemas.paper_summary import PaperSummary
from ..prompts.critic_prompt import CRITIC_SYSTEM_PROMPT


def critique_paper(summary: PaperSummary) -> PaperCritique:
    llm = get_llm().with_structured_output(PaperCritique, method="function_calling")
    prompt = f"""PaperSummary JSON:
{summary.model_dump_json(indent=2)}

Check for:
- Raw RGB usage and privacy discussion
- Skeleton/keypoints/optical flow/anonymized representations
- Dataset size and diversity
- Subject-independent splits / cross-dataset generalization
- Model size/FLOPs/latency and edge deployment tests
- Ablations, recent baselines, failure cases
"""
    return llm.invoke([SystemMessage(content=CRITIC_SYSTEM_PROMPT), HumanMessage(content=prompt)])


def critique_papers(summaries: List[PaperSummary]) -> List[PaperCritique]:
    return [critique_paper(s) for s in summaries]

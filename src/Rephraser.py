from openai_harmony import (
	ReasoningEffort
)
from src.template import REPHRASER_TEMPLATE
from src.utils import llm_answer, ans_to_dict


class Rephraser():
	def __init__(self, model, encoder):
		self.model = model
		self.encoder = encoder
		self.template_rephrase = REPHRASER_TEMPLATE

	def rephrase(self, question, reasoning_effort=ReasoningEffort.MEDIUM):
		print("- Rephrasing ...")
		try:
			rephrased_question = llm_answer(self.model, self.encoder, self.template_rephrase, question, reasoning_effort)
			rephrased_question = ans_to_dict(rephrased_question)
			rephrased_question = [rq["phrase"] for rq in rephrased_question["phrases"]]
		except:
			raise ValueError("Rephrasing failed")

		return rephrased_question
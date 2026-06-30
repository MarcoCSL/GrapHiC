from src.template import REPHRASER_TEMPLATE
from src.utils import llm_answer, ans_to_dict


class Rephraser():
	def __init__(self, model, llm_name, tokenizer):
		self.model = model
		self.llm_name = llm_name
		self.tokenizer = tokenizer
		self.template_rephrase = REPHRASER_TEMPLATE

	def rephrase(self, question):
		print("- Rephrasing ...")
		try:
			rephrased_question = llm_answer(self.model, self.llm_name, self.tokenizer, self.template_rephrase, question)
			rephrased_question = ans_to_dict(rephrased_question)
			rephrased_question = [rq["phrase"] for rq in rephrased_question["phrases"]]
		except:
			raise ValueError("Rephrasing failed")

		return rephrased_question
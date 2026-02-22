from openai_harmony import (
	ReasoningEffort
)
from src.template import parser_template_builder
from src.utils import llm_answer, ans_to_dict


class Parser():
	def __init__(self, model, encoder, db_interviewer):
		self.model = model
		self.encoder = encoder
		relations = db_interviewer.get_relations()
		self.template = parser_template_builder(relations)

	def parse_intent_aux(self, question, reasoning_effort):
		ans = llm_answer(self.model, self.encoder, self.template, question, reasoning_effort)
		ans = ans_to_dict(ans)

		return ans
	
	def parse_intent(self, question):
		print("- Parsing the question")
		reasoning_efforts = [ReasoningEffort.HIGH, ReasoningEffort.MEDIUM, ReasoningEffort.LOW]
		
		for i, effort in enumerate(reasoning_efforts, start=1):
			answer = self.parse_intent_aux(question, effort)

			cleaned_answer = self.normalize_data(answer)

			if self.is_valid_answer(cleaned_answer):
				return cleaned_answer

			print(f"Retrying with different reasoning effort ({i}/{len(reasoning_efforts)})")

		raise ValueError("Reasoning failed")
	
	# Strips everything and ensures all values are lists of one or more strings
	def normalize_data(self, data):
		cleaned = {}

		for k, v in data.items():
			key = k.strip()

			if isinstance(v, str):
				v = v.strip()
				value = [v] if v else []
			elif isinstance(v, list):
				value = []
				for x in v:
					if isinstance(x, str):
						x = x.strip()
						if x:
							value.append(x)
					else:
						raise TypeError("JSON values must be strings")
			else:
				raise TypeError("JSON values must be strings")

			cleaned[key] = value

		return cleaned

	def is_valid_answer(self, answer):
		function = answer.get("function")
		genes = answer.get("genes")
		samples = answer.get("samples")

		if not function or not genes or not samples:
			return False
		
		if len(function) > 1:
			return False

		return True

	

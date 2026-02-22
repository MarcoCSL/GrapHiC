import torch
from transformers import AutoModelForCausalLM
from openai_harmony import (
	load_harmony_encoding,
	HarmonyEncodingName,
	ReasoningEffort
)
from src.utils import llm_answer
from src.GraphRAG import GraphRAG
from src.template import FINAL_ANSWER_TEMPLATE


class GrapHiC:	
	def __init__(self, llm_name="openai/gpt-oss-20b"):
		self.device = "auto" if torch.cuda.is_available() else "cpu"
		self.llm_name = llm_name
		self.encoder = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
		self.model = AutoModelForCausalLM.from_pretrained(
			self.llm_name, 
			device_map=self.device
		)
		self.GraphRAG = GraphRAG(self.model, self.encoder, ReasoningEffort.MEDIUM)
		self.answer = self.graphic_answer

	def graphic_answer(self, question):
		print("\nAnswering question: ", question)
		prompt, query = self.GraphRAG.get_data(question)
		print("- Final answer with LLM")
		ans = llm_answer(self.model, self.encoder, FINAL_ANSWER_TEMPLATE, prompt, ReasoningEffort.MEDIUM)

		return ans, query

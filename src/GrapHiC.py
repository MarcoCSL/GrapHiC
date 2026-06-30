import torch
from transformers import AutoModelForCausalLM
from transformers import AutoTokenizer
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
		self.llm_name = llm_name
	
		if "gpt-oss" in self.llm_name:
			self.tokenizer = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
		else:
			self.tokenizer = AutoTokenizer.from_pretrained(self.llm_name)
	
		self.model = AutoModelForCausalLM.from_pretrained(
			self.llm_name, 
			device_map="auto",
			dtype=torch.bfloat16,
		)
		self.graph_rag = GraphRAG(self.model, self.llm_name, self.tokenizer)

	def answer(self, question):
		print("\nAnswering question: ", question)
		prompt, query = self.graph_rag.get_data(question)
		print("- Final answer with LLM")
		ans = llm_answer(self.model, self.llm_name, self.tokenizer, FINAL_ANSWER_TEMPLATE, prompt, ReasoningEffort.MEDIUM)

		return ans, query

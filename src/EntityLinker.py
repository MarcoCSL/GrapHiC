from rapidfuzz import process, fuzz
from pathlib import Path
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

class EntityLinker:
	def __init__(self, csvs_folder=PROJECT_DIR / "src" / "data"):
		dfs = [pd.read_csv(p) for p in csvs_folder.glob("*.csv")]
		gene_df = pd.concat(dfs, ignore_index=True)
		self.symbol_to_number = dict(zip(gene_df["symbol"], gene_df["gene_number"]))
		self.gene_list = gene_df["symbol"].tolist()

	def link(self, gene):
		return self.symbol_to_number[gene]
	
	def best_match(self, words_list, list_to_match):
		result = []
		for word in words_list:
			fc = self.fuzzy_aux(word, list_to_match)
			result.append(fc)
		
		return result
	
	def fuzzy_aux(self, word, list_to_match):
		fuzzy_candidate = process.extractOne(
			word,
			list_to_match,
			scorer=fuzz.ratio
		)

		return fuzzy_candidate[0]

	def get_gene_list(self):
		return self.gene_list

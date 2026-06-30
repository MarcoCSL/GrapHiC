FUNCTIONS_LIST = """
get_metric(genes, metric, samples): returns metric of one or more genes across one or more samples (can be used for comparison)
→ genes must contain 1 or more genes
→ samples must contain 1 or more samples

average_metric(genes, metric, samples): returns average metric for multiple genes across one or more samples (can be used for comparison)
→ genes must contain 2 or more genes
→ samples must contain 1 or more samples

ranking(genes, metric, samples): ranks multiple genes by a metric in one sample
→ genes must contain 2 or more genes
→ samples must contain exactly 1 sample

get_neighbours(genes, samples): returns number of neighbours of one or more genes in one or more samples (can be used for comparison)
→ genes must contain 1 or more genes
→ samples must contain 1 or more samples

shared_neighbours(genes, samples): returns the number of shared neighbours between two ore more genes in one or more samples (can be used for comparison)
→ genes must contain 2 or more genes
→ samples must contain 1 or more samples

path_exists_sequence(genes, samples): checks if path between two or more genes exists in one or more samples without using intermediate genes (can be used for comparison)
→ genes must contain 2 or more genes
→ samples must contain 1 or more samples

shortest_path(genes, samples): returns shortest path between only two genes in one or more samples (can be used for comparison between multiple samples)
→ genes must contain exactly 2 genes
→ samples must contain 1 or more samples

path_length_sequence(genes, samples): returns the length of the shortest path between two genes in one or more samples (can be used for comparison between multiple samples)
→ genes must contain exactly 2 genes
→ samples must contain 1 or more samples
"""

PARSER_EXPECTED_OUTPUT = """
{
	"function": "",
	"genes": [],
	"metric": "",
	"samples": []
}
"""

def parser_template_builder(relations):
	relations = ", ".join(relations)

	configuration_parameters = f"""
	Available samples: {relations}
	Available metrics: degree_centrality, betweenness_centrality, closeness_centrality, eigenvector_centrality, clustering_coefficient
	"""

	parser_template = f"""
	You are a query parser for a gene interaction graph.

	{FUNCTIONS_LIST}

	{configuration_parameters}

	Expected output in JSON format:
	{PARSER_EXPECTED_OUTPUT}

	Rules:
	- If the question can be mapped to one of the available functions, select the correct function and return JSON only
	- If the question cannot be mapped, leave function field empty
	- Use only the functions listed
	- Use only allowed samples
	- Always output valid JSON
	- Always use arrays for genes and samples
	- Do not output text outside JSON
	"""

	return parser_template

def cypher_template_builder(schema, question):
	CYPHER_GENERATOR_TEMPLATE = f"""
	You are an expert Neo4j engineer.
	Given a natural language question and the database schema, generate a Cypher query that answers the question.

	Rules:
	- Return ONLY the Cypher query.
	- Do NOT include explanations, comments, markdown, or code fences.
	- Do NOT restate the question.
	- Do NOT invent labels, relationship types, or properties not present in the provided schema.
	- Use only the elements explicitly defined in the schema.
	- Treat the relations as if they were undirected.

	Database schema:
	{schema}

	Question:
	{question}
	"""

	return CYPHER_GENERATOR_TEMPLATE

REPHRASER_TEMPLATE = f"""
You are a query rewriter for a gene interaction graph system.
Your output will be used by a system that will parse the questions according to the following functions:

{FUNCTIONS_LIST}

Your task:
- If the user prompt contains multiple questions, split them into smaller ones.
- Each atomic question must express only one intent.
- Questions must be independent and cannot rely on values from other questions.
- Do not interpret or answer.
- Do not map to functions.
- Only rewrite or split.
- If the question is already atomic, return it unchanged.

Reason step-by-step on how you would approach the question.

Rules:
- Always return valid JSON.
- The output must contain a list called "phrases".
- Each entry must be an object with one key: "phrase".
- Do not output text outside JSON.

Expected output in JSON format:
{{
	"phrases": [
		{{"phrase": ""}}
	]
}}
"""

FINAL_ANSWER_TEMPLATE = """
Reply using plain text only.
Do not use markdown symbols.
Prove data that supports your answer (if available).

If the question contains multiple sub-questions:
- Answer each sub-question separately.
- Preserve logical order.

Example:
Question: 
What is the value of property X of Y in sample Z?
Your answer: 
The value of property X of Y in sample Z is ...
According to the database ...
"""

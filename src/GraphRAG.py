import re
import traceback
from neo4j.exceptions import Neo4jError
from src.Parser import Parser
from src.Rephraser import Rephraser
from src.DBInterviewer import DBInterviewer
from src.utils import llm_answer
from src.template import cypher_template_builder


class GraphRAG():
	def __init__(self, model, llm_name, tokenizer):
		self.model = model
		self.llm_name = llm_name
		self.tokenizer = tokenizer
		self.db_interviewer = DBInterviewer()
		self.rephraser = Rephraser(self.model, self.llm_name, self.tokenizer)
		self.parser = Parser(self.model, self.llm_name, self.tokenizer, self.db_interviewer)
		self.FORBIDDEN = re.compile(r'(?i)\b(CREATE|MERGE|DELETE|DETACH|REMOVE|SET|DROP|FOREACH|CALL|LOAD\s+CSV|CONSTRAINT|INDEX)\b')
		self.ALLOWED = re.compile(r'(?i)^\s*(MATCH|OPTIONAL MATCH)\b')
		self.schema = self.db_interviewer.get_schema() # With enormus dataset may require some time, use sampling if needed

	def get_data(self, og_question):
		try:
			rephrased_question = self.rephraser.rephrase(og_question)
			if len(rephrased_question) > 1:
				print("  Rephrased into:")
				[print("                  ", rq) for rq in rephrased_question]
		except:
			rephrased_question = [og_question]
		
		datas = []
		queries = []
		tot = len(rephrased_question)

		for i, question in enumerate(rephrased_question):
			print(f"- Analysing question {i + 1}/{tot}")
			# Try to parse and execute query
			try:
				json = self.parser.parse_intent(question)
				data, query = self.db_interviewer.handle_request(json)
			# If something fails (usually the parsing), use LLM to make up cypher query
			except Exception as e:
				print(type(e).__name__)
				print(e)
				traceback.print_exc()

				query = ""
				# Try to create and execute the query
				try:
					template = cypher_template_builder(self.schema, question)
					
					print("- Creating cypher query using LLM")
					query = llm_answer(self.model, self.llm_name, self.tokenizer, template, question)
					query = self.validate_query(query)
					data = self.db_interviewer.custom_query(query)
				# If something goes wrong say to the user that you could not get any info for the question
				except Neo4jError as e:
					print("Neo4j error")
					print("Type:", type(e).__name__)
					print("Code:", getattr(e, "code", None))
					print("Message:", e)
					data = ["Couldn't query the database! No information retrieved for question: (" + question + ")"]
				except (RuntimeError, ValueError, Exception) as e:
					print("Unexpected error:", type(e).__name__, e)
					data = [f"Unexpected failure for question: ({question})"]

			data = "\n".join(data)
			datas.append(data)
			queries.append(query)
		
		prompt = og_question + "\n\nRetrieved information from the Database:\n\n" + "\n".join(datas)
		print("- Information retrieved!")

		return prompt, "\n".join(queries)
	
	def validate_query(self, query):
		if self.FORBIDDEN.search(query):
			raise ValueError("Forbidden clause detected in Cypher query")
		if not self.ALLOWED.match(query):
			raise ValueError("Only read-only MATCH queries are allowed")
		
		return query
	

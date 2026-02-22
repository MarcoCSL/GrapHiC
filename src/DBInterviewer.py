from src.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER, NEO4J_DATABASE
from src.EntityLinker import EntityLinker
from neo4j import GraphDatabase
from neo4j_graphrag.schema import get_structured_schema
import json
import logging
logging.getLogger("neo4j").setLevel(logging.ERROR)


class DBInterviewer:
	def __init__(self):
		self.entity_linker = EntityLinker()
		self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
		self.schema, node_properties, relations = self.get_schema_from_db()

		node_properties = node_properties.get("Gene")
		unused_properties = ["id", "organism", "gene", "symbol", "chr", "start", "end", "strand", "number", "genome"]
		self.allowed_merics = list(set(node_properties) - set(unused_properties))
		
		self.relations = list(relations.keys())
		rel_view = self.Project(self.relations)
		self.graphview_map = {rel: gview for rel, gview in rel_view}
		
		self.function_list = [
			"get_metric",
			"average_metric",
			"ranking",
			"get_neighbours",
			"shared_neighbours",
			"path_exists_sequence",
			"shortest_path",
			"path_length_sequence"
		]

	# Create GDS projections
	def Project(self, relations):
		rel_view = []

		for rel in relations:
			gview = "gview_" + rel
			rel_view.append((rel, gview))

			# Check if the graph projection already exists
			check_query = f"RETURN gds.graph.exists('{gview}') AS exists"
			with self.driver.session() as session:
				result = session.run(check_query)
				exists = result.single()["exists"]

			if not exists:
				query = f"""
				CALL gds.graph.project(
					'{gview}',
					{{
						Gene: {{
						properties: ['number']
						}}
					}},
					{{
						{rel}: {{
							type: '{rel}',
							orientation: 'UNDIRECTED',
							aggregation: 'SINGLE'
						}}
					}}
				)
				"""
				with self.driver.session() as session:
					result = session.run(query)
		
		return rel_view

	def param_mapper(self, data):
		function = self.entity_linker.best_match(data["function"], self.function_list)
		genes = self.entity_linker.best_match(data["genes"], self.entity_linker.get_gene_list())
		samples = self.entity_linker.best_match(data["samples"], self.relations)
		
		try:
			if data["metric"]:
				raw_metrics = data["metric"]
				expanded_metrics = [
					f"{metric}_{sample}"
					for metric in raw_metrics
					for sample in samples
				]
				metrics = self.entity_linker.best_match(expanded_metrics, self.allowed_merics)
			else:
				metrics = []
		except:
			metrics = []

		# Function is a list containing a single element by design
		return function[0], genes, metrics, samples

	def handle_request(self, data):
		print("- Handling DB query")
		function, genes, metrics, samples = self.param_mapper(data)
		gene_numbers = self.get_genes_number(genes)
		context = []

		if function == "get_metric" or function == "ranking":
			result, summary = self.get_metric(genes, metrics)
			for dic in result:
				metric, relation = self.strip_relation_suffix(dic["metric"])
				tmp_res = "In the Sample: " + relation + ", the Gene " + dic["gene"] + " has " + metric + " = " + str(dic["metric_value"])
				context.append(tmp_res)
		
		elif function == "average_metric":
			result, summary = self.average_metric(genes, metrics)
			genes = self.genes_to_string(genes)
			for dic in result:
				metric, relation = self.strip_relation_suffix(dic["metric"])
				tmp_res = "In the Sample: " + relation +  ", the genes" + genes + " have " + metric + " mean value = " + str(dic["mean_value"]) 
				context.append(tmp_res)
		
		elif function == "get_neighbours":
			result, summary = self.get_neighbours(genes, samples)
			for dic in result:
				tmp_res = "In the Sample: " + dic["sample"] + ", the Gene " + dic["gene"] + " has " + str(dic["n_neighbours"]) + " neighbours"
				context.append(tmp_res)
		
		elif function == "shared_neighbours":
			result, summary = self.get_neighbours(genes, samples)
			all_genes = self.genes_to_string(genes)
			sample_sets = {}

			for dic in result:
				s = dic["sample"]
				neighbours_set = set(dic["neighbours"])
				neighbours_set.discard(dic["gene"])  # Remove self loop
				if s not in sample_sets:
					sample_sets[s] = []
				sample_sets[s].append(neighbours_set)

			intersections = {
				s: set.intersection(*sets) if sets else set()
				for s, sets in sample_sets.items()
			}
			counts = {s: len(intersection) for s, intersection in intersections.items()}
			
			for s in intersections:
				n_common = counts[s]
				common_genes = sorted(intersections[s])
				
				tmp_res = f"In the sample {s}, the genes [{all_genes}] have {n_common} neighbours in common: {common_genes}"
				context.append(tmp_res)

		elif function == "path_exists_sequence":
			result, summary = self.path_exists_sequence(gene_numbers, samples)
			for dic in result:
				try: # se si schianta non c'è path, se non si chianta ma trova un subset sbagliato mettiamo False
					genes_list = [str(row["gene"]) for row in dic["rows"]]
					success = set(genes_list) == set(genes)
				except:
					success = False
					
				if success:
					tmp_res = "In the Sample: " + dic["sample"] + ", the Genes [" + ", ".join(genes) + "] have a path that connects all of them without using intermediate genes"
				else:
					tmp_res = "In the Sample: " + dic["sample"] + ", the Genes [" + ", ".join(genes) + "] do not have a path that connects all of them without using intermediate genes"
				context.append(tmp_res)
		
		elif function == "shortest_path" or function == "path_length_sequence":
			if len(genes) != 2:
				raise ValueError("Number of genes too high, you can use only 2 if you want to compute the shortest path!")
			result, summary = self.shortest_paths(gene_numbers, samples)
			genes = self.genes_to_string(genes)
			
			for dic in result:
				is_path = (False if len(dic["rows"]) == 0 or not dic["rows"] else True)
				if not is_path:
					risultato_tmp = "In the Sample: " + dic["sample"] + ", there is no path between the Genes: [" + genes + "]"
				else:
					paths = []
					for row in dic["rows"]:
						edges = row["edges"]
						symbols = [edges[0]["from_symbol"]] # First node
						for edge in edges:
							symbols.append(edge["to_symbol"])
						
						path = " - ".join(symbols)
						paths.append(path)
					risultato_tmp = "In the Sample: " + dic["sample"] + ", the shortest path between the Genes [" + genes + "] is: " + path + " with a total cost of: " + str(dic["rows"][0]["totalCost"])
				context.append(risultato_tmp)

		# elif function == "":

		summary = self.summary_converter(summary)
		return context, summary
	
	def strip_relation_suffix(self, metric):
		metric, relation = metric.rsplit("_", 1)

		return metric, relation
	
	def genes_to_string(self, genes):
		return ", ".join(genes)

	def get_genes_number(self, genes):
		numbers = []
		for g in genes:
			numbers.append(self.entity_linker.link(g))

		return numbers
	
	def get_metric(self, genes, metrics):
		query = """
		UNWIND $genes AS g
		MATCH (n:Gene {symbol: g})
		UNWIND $metrics AS m
		RETURN g AS gene, m AS metric, n[m] AS metric_value
		"""

		with self.driver.session() as session:
			aux_result = session.run(
				query,
				genes=genes,
				metrics=metrics
			)
			result = list(aux_result)
			summary = aux_result.consume()

		return [dict(r) for r in result], summary

	def average_metric(self, genes, metrics):
		query = """
		UNWIND $genes AS g
		MATCH (n:Gene {symbol: g})
		UNWIND $metrics AS m
		RETURN m AS metric, avg(n[m]) AS mean_value
		"""

		with self.driver.session() as session:
			aux_result = session.run(
				query,
				genes=genes,
				metrics=metrics
			)
			result = list(aux_result)
			summary = aux_result.consume()

		return [dict(r) for r in result], summary
	
	# Returns neighbours and number of neighbours of each gene for each sample (relation)
	def get_neighbours(self, genes, samples):
		query = """
		UNWIND $genes AS g
		MATCH (n:Gene {symbol: g})
		UNWIND $samples AS s
		OPTIONAL MATCH (n)-[r]-(m:Gene)
		WHERE type(r) = s
		WITH g, s, collect(m.symbol) AS neighbours
		RETURN 
			g AS gene,
			s AS sample,
			size(neighbours) AS n_neighbours,
			neighbours
		ORDER BY sample, gene
		"""

		with self.driver.session() as session:
			aux_result = session.run(
				query,
				genes=genes,
				samples=samples
			)
			result = list(aux_result)
			summary = aux_result.consume()

		return [dict(r) for r in result], summary
	
	# Checks if multiple genes are connected for each sample
	def path_exists_sequence(self, genes_number, samples):
		result = []
		summaries = []

		with self.driver.session() as session:
			for s in samples:
				# 1) Drop tmp if exists
				drop_query = """
				CALL gds.graph.exists('tmp') YIELD exists
				WITH exists
				WHERE exists
				CALL gds.graph.drop('tmp', false)
				YIELD graphName
				RETURN graphName
				"""
				session.run(drop_query)

				# 2) Crea proiezione tmp con soli geni target
				project_query = f"""
				MATCH (source:Gene)-[r:{s}]-(target:Gene)
				WHERE source.number IN $genes
				AND target.number IN $genes

				WITH gds.graph.project(
					'tmp',
					source,
					target,
					{{
						sourceNodeProperties: source {{ .number }},
						targetNodeProperties: target {{ .number }},
						relationshipType: '{s}'
					}},
					{{
						undirectedRelationshipTypes: ['{s}']
					}}
				) AS g

				RETURN g.graphName, g.nodeCount, g.relationshipCount
				"""
				session.run(
					project_query,
					genes=genes_number
				)

				# 3) Minimum Weight Spanning Tree
				query = """
				MATCH (g:Gene)
				WHERE g.number IN $genes
				WITH g
				LIMIT 1

				CALL gds.spanningTree.stream(
					'tmp',
					{
						sourceNode: id(g)
					}
				)
				YIELD nodeId, parentId, weight

				WITH
					gds.util.asNode(nodeId) AS node,
					gds.util.asNode(parentId) AS parent,
					weight

				RETURN
					node.number AS gene,
					parent.number AS parent,
					weight
				ORDER BY gene
				"""

				try:
					aux_result = session.run(
						query,
						genes=genes_number
					)

					res = list(aux_result)
					summary = aux_result.consume()
					summaries.append(summary)
					result.append({
						"sample": s,
						"rows": [dict(r) for r in res]
					})

				except:
					session.run("CALL gds.graph.drop('tmp', false)")
					summary = query + "\n\t\tUsing as parameters:\n\t\t[gene_numbers = " + ", ".join(str(n) for n in genes_number) + " samples (relations) = " + ", ".join(samples) + "]"
					summaries.append(query)
					result.append({
						"sample": s,
						"error": 0
					})
				
				session.run("CALL gds.graph.drop('tmp', false)")

		return result, summaries

	# Returns K-shortest paths between a pair of genes in all the specified samples (relations)
	# returns also: path cost
	def shortest_paths(self, genes_number, samples, k=1):
		g1, g2 = genes_number
		result = []
		summaries = []

		query = """
		MATCH (source:Gene {number: $g1})
		MATCH (target:Gene {number: $g2})

		CALL gds.shortestPath.yens.stream($gview, {
			sourceNode: source,
			targetNode: target,
			k: $k
		})
		YIELD index, path, totalCost

		WITH index, totalCost, nodes(path) AS ns
		UNWIND range(0, size(ns)-2) AS i
		WITH index, totalCost, ns[i] AS fromNode, ns[i+1] AS toNode

		MATCH (fromNode)-[r]-(toNode)
		WHERE type(r) = $rel

		WITH index, totalCost,
			collect({
				from_number: fromNode.number,
				from_symbol: fromNode.symbol,
				to_number: toNode.number,
				to_symbol: toNode.symbol,
				relation: type(r)
			}) AS edges

		RETURN
			index AS path_index,
			totalCost,
			edges
		ORDER BY path_index
		"""

		with self.driver.session() as session:
			for s in samples:
				gview = self.graphview_map[s]
				try:
					aux_result = session.run(
						query,
						g1=g1,
						g2=g2,
						gview=gview,
						rel=s,
						k=k
					)

					rows = list(aux_result)
					summary = aux_result.consume()
					summaries.append(summary)
		
					result.append({
						"sample": s,
						"source": g1,
						"target": g2,
						"rows": [dict(r) for r in rows]
					})

				except Exception as e:
					result.append({
						"sample": s,
						"error": str(e)
					})

		return result, summaries

	def get_schema_from_db(self):
		structured_schema = get_structured_schema(
			self.driver,
			database=NEO4J_DATABASE,
			sample=-1, # -1 uses all nodes in the DB to guess the schema
			timeout=None,
			sanitize=False,
			is_enhanced=False
		)

		node_props = {}
		rel_props = {}

		for label, props in structured_schema["node_props"].items():
			node_props[label] = [p["property"] for p in props]

		for rel_type, props in structured_schema["rel_props"].items():
			rel_props[rel_type] = [p["property"] for p in props]

		node_lines = []
		rel_prop_lines = []
		rel_lines = []

		for label, props in node_props.items():
			node_lines.append(label + " {" + ", ".join(props) + "}")

		for rel_type, props in rel_props.items():
			rel_prop_lines.append(rel_type + " {" + ", ".join(props) + "}")

		for rel in structured_schema["relationships"]:
			rel_lines.append("(:" + rel["start"] + ")-[:" + rel["type"] + "]-(:" + rel["end"] + ")")

		schema = (
			"Node properties:\n"
			+ "\n".join(node_lines)
			+ "\n\nRelationship properties:\n"
			+ "\n".join(rel_prop_lines)
			+ "\n\nRelationships:\n"
			+ "\n".join(rel_lines)
		)

		return schema, node_props, rel_props
	
	def custom_query(self, query):
		print("- Handling DB query")

		with self.driver.session() as session:
			tx = session.begin_transaction(timeout=5)
			try:
				result = tx.run(query)
				out = [json.dumps(r.data(), ensure_ascii=False) for r in result]
				tx.commit()
				return out
			except:
				tx.rollback()
				raise
			finally:
				tx.close()

	def get_relations(self):
		return self.relations
	
	def get_schema(self):
		return self.schema

	def summary_converter_aux(self, summary):
		if isinstance(summary, str):
			result = summary
		else:
			summary = summary[0] if isinstance(summary, list) else summary
			query = summary.query
			parameters = ", ".join(f"{k}: {v}" for k, v in summary.parameters.items())
			result = query + "\n\tWith parameters: [" + parameters + "]"

		return result
	
	def summary_converter(self, summary):
		if isinstance(summary, list):
			result = [self.summary_converter_aux(s) for s in summary]
		else:
			result = [self.summary_converter_aux(summary)]

		return "\n".join(result)

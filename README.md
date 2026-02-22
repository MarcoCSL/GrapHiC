**INSTRUCTIONS**
<br><br>

Execute:
```bash
conda create -n GrapHiC python=3.11.13
conda activate GrapHiC
pip install -r requirements.txt
```

Then:
1. Install neo4j (utilized version: **2026.01.3**)
2. Download neo4j gds and apoc libraries and put them into */var/lib/neo4j/plugins* folder (utilized versions: **2026.01.3**, **neo4j-graph-data-science-2.25.0**)
3. Put genome_mm10.csv file in *src/data* and in */var/lib/neo4j/import* folders
4. Put contact matrix files (ES.csv, NPC.csv) in */var/lib/neo4j/import* folder
5. Modify */etc/neo4j/neo4j.conf*:
  
   Uncomment
   ```bash
     server.directories.import=/var/lib/neo4j/import
     dbms.security.auth_enabled=false
     server.default_listen_address=0.0.0.0
     server.default_advertised_address=localhost
     server.bolt.enabled=true
     server.bolt.listen_address=:7687
     server.http.enabled=true
     server.http.listen_address=:7474
   ```
   Add
   ```bash
     dbms.security.procedures.unrestricted=apoc.*
     dbms.security.procedures.allowlist=apoc.*,gds.*
   ```
6. Export:
   ```bash
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_DATABASE=neo4j
   NEO4J_PASSWORD=yourpassword
   ```
7. Start Neo4j database:
   ```bash
   sudo neo4j start
   ```
8. Execute this queries:
    ```cypher
    // Indexes creation
    CREATE CONSTRAINT gene_symbol_unique IF NOT EXISTS
    FOR (g:Gene) REQUIRE g.symbol IS UNIQUE;
    CREATE CONSTRAINT gene_number_unique IF NOT EXISTS
    FOR (g:Gene) REQUIRE g.number IS UNIQUE;
    ```

    ```cypher
    // Genome upload
    CALL apoc.periodic.iterate(
      "LOAD CSV WITH HEADERS FROM 'file:///genome_mm10.csv' AS row FIELDTERMINATOR ',' RETURN row",
      "MERGE (g:Gene {id: row.gene_id})
       SET g.organism = row.organism,
           g.genome = row.genome,
           g.number = toInteger(row.gene_number),
           g.symbol = row.symbol,
           g.chr    = row.chr,
           g.start  = toInteger(row.start),
           g.end    = toInteger(row.end),
           g.strand = row.strand",
      {batchSize: 3000, parallel: true}
    );
    ```
    
    ```cypher
    // Contacts upload
    WITH [
    'NPC',
    'ES'
    ] AS files
    UNWIND files AS file
    CALL apoc.periodic.iterate(
    "
    LOAD CSV WITH HEADERS FROM 'file:///" + file + ".csv' AS row FIELDTERMINATOR ','
    RETURN row
    ",
    "
    MATCH (g1:Gene {symbol: row.gene1})
    MATCH (g2:Gene {symbol: row.gene2})
    CALL apoc.create.relationship(
      g1,
      row.sample_id,
      {
        fdr: toFloat(row.fdr),
        detection_scale: toFloat(row.detection_scale),
        loop_distance: toInteger(row.loop_distance)
      },
      g2
    ) YIELD rel
    RETURN 0
    ",
    {batchSize: 10000, parallel: true}
    )
    YIELD batches, total
    RETURN file, batches, total;
    ```
    
    ```cypher
    // ES graphview creation
    CALL gds.graph.project(
      'graphview_ES',
      {
        Gene: {
          properties: ['number']
        }
      },
      {
        ES: {
          type: 'ES',
          orientation: 'UNDIRECTED',
          aggregation: 'SINGLE'
        }
      }
    );
    ```
    
    ```cypher
    // Metrics computation on ES
    WITH 'ES' AS tag
    CALL gds.betweenness.write(
      'graphview_ES',
      { writeProperty: 'betweenness-centrality-' + tag }
    )
    YIELD nodePropertiesWritten AS b
    CALL gds.closeness.write(
      'graphview_ES',
      { 
        writeProperty: 'closeness-centrality-' + tag,
        useWassermanFaust: true
      }
    )
    YIELD nodePropertiesWritten AS c
    CALL gds.eigenvector.write(
      'graphview_ES',
      { 
        writeProperty: 'eigenvector-centrality-' + tag,
        maxIterations: 500
      }
    )
    YIELD nodePropertiesWritten AS e
    CALL gds.localClusteringCoefficient.write(
      'graphview_ES',
      { writeProperty: 'clustering-coefficient-' + tag }
    )
    YIELD nodePropertiesWritten AS l
    CALL gds.degree.write(
      'graphview_ES',
      { writeProperty: 'degree-centrality-' + tag }
    )
    YIELD nodePropertiesWritten AS d
    RETURN b, c, e, l, d;
    ```

    ```cypher
    // NPC graphview creation
    CALL gds.graph.project(
      'graphview_NPC',
      {
        Gene: {
          properties: ['number']
        }
      },
      {
        NPC: {
          type: 'NPC',
          orientation: 'UNDIRECTED',
          aggregation: 'SINGLE'
        }
      }
    );
    ```
    
    ```cypher
    // Metrics computation on NPC
    WITH 'NPC' AS tag
    CALL gds.betweenness.write(
      'graphview_NPC',
      { writeProperty: 'betweenness-centrality-' + tag }
    )
    YIELD nodePropertiesWritten AS b
    CALL gds.closeness.write(
      'graphview_NPC',
      { 
        writeProperty: 'closeness-centrality-' + tag,
        useWassermanFaust: true
      }
    )
    YIELD nodePropertiesWritten AS c
    CALL gds.eigenvector.write(
      'graphview_NPC',
      { 
        writeProperty: 'eigenvector-centrality-' + tag,
        maxIterations: 500
      }
    )
    YIELD nodePropertiesWritten AS e
    CALL gds.localClusteringCoefficient.write(
      'graphview_NPC',
      { writeProperty: 'clustering-coefficient-' + tag }
    )
    YIELD nodePropertiesWritten AS l
    CALL gds.degree.write(
      'graphview_NPC',
      { writeProperty: 'degree-centrality-' + tag }
    )
    YIELD nodePropertiesWritten AS d
    RETURN b, c, e, l, d;
    ```
    
    ```cypher
    // drop graphviews
    CALL gds.graph.drop('graphview_ES');
    CALL gds.graph.drop('graphview_NPC');
    ```

<br><br>
Examples of execution:

```bash
# Answers all questions in question.txt file
python3 test.py
```

```bash
# Allows user to ask questions interactively
python3 test.py -i
```

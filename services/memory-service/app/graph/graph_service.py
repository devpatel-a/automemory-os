from app.graph.graph_builder import build_graph
from app.graph.relationship_detector import detect_relationships
from app.graph.repository import GraphRepository
from app.graph.sql_repository import USER_ENTITY, SqlGraphRepository
from app.knowledge.fact_extractor import extract_fact
from app.understanding.entity_normalizer import normalize_entity_name


class GraphService:
    """
    Knowledge graph service.

    - persist_memory(): writes entities, memory links and typed relationships
      to PostgreSQL (the source of truth) inside the caller's transaction.
      Requires a session: GraphService(db).
    - process_memory(): updates the process-local in-memory graph, kept as a
      deterministic compatibility view for existing callers and tests.
    """

    def __init__(self, db=None):
        self.repository = GraphRepository()
        self.sql = SqlGraphRepository(db) if db is not None else None

    def persist_memory(self, parsed_memory, memory_id: int) -> None:
        if self.sql is None:
            raise RuntimeError("persist_memory requires GraphService(db)")

        fact = extract_fact(parsed_memory)
        types = {normalize_entity_name(e.text): e.label for e in parsed_memory.entities}
        subject_key = (
            normalize_entity_name(fact.entity)
            if fact and fact.entity and fact.entity.lower() != USER_ENTITY
            else USER_ENTITY
        )
        value_key = normalize_entity_name(fact.value) if fact and fact.value else ""

        ids = {}

        def entity_id(key: str) -> int | None:
            if key not in ids:
                entity_type = "USER" if key == USER_ENTITY else types.get(key, "CONCEPT")
                ids[key] = self.sql.upsert_entity(key, entity_type)
            return ids[key]

        # Memory -> entity links (the subject is linked even when it is the user)
        subject_id = entity_id(subject_key)
        if subject_id is not None:
            self.sql.link_memory(memory_id, subject_id, "subject")
        for key in types:
            if key and key != subject_key:
                eid = entity_id(key)
                if eid is not None:
                    self.sql.link_memory(memory_id, eid, "value" if key == value_key else "mention")

        # Typed relationships
        for edge in detect_relationships(parsed_memory):
            source_id, target_id = entity_id(edge.source), entity_id(edge.target)
            if source_id is not None and target_id is not None:
                self.sql.add_relationship(source_id, target_id, edge.relationship, memory_id)

    def process_memory(
        self,
        parsed_memory,
        memory_id: int | None = None,
    ):

        graph = self.repository.load()

        new_graph = build_graph(
            parsed_memory,
            memory_id,
        )

        existing = {
            node.id.lower(): node
            for node in graph.nodes
        }

        for node in new_graph.nodes:

            current = existing.get(
                node.id.lower()
            )

            if current is None:

                graph.nodes.append(node)

                existing[node.id.lower()] = node

            else:

                for mid in node.memory_ids:

                    if mid not in current.memory_ids:

                        current.memory_ids.append(mid)

        existing_edges = {
            (
                edge.source.lower(),
                edge.target.lower(),
                edge.relationship.lower(),
            )
            for edge in graph.edges
        }

        for edge in new_graph.edges:

            key = (
                edge.source.lower(),
                edge.target.lower(),
                edge.relationship.lower(),
            )

            if key not in existing_edges:

                graph.edges.append(edge)

                existing_edges.add(key)

        self.repository.save(graph)

        return graph

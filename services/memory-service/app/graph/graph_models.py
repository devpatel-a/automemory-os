from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: str

    # IDs of memories that mention this node.
    memory_ids: list[int] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str


class KnowledgeGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    def find_node(
        self,
        node_id: str,
    ) -> GraphNode | None:

        node_id = node_id.lower()

        for node in self.nodes:

            if node.id.lower() == node_id:
                return node

        return None

    def neighbors(
        self,
        node_id: str,
    ) -> list[str]:

        node_id = node_id.lower()

        results = []

        for edge in self.edges:

            if edge.source.lower() == node_id:
                results.append(edge.target)

            elif edge.target.lower() == node_id:
                results.append(edge.source)

        return results

    def expand(
        self,
        entities: list[str],
    ) -> list[str]:

        expanded = {
            entity.lower()
            for entity in entities
        }

        queue = list(expanded)

        while queue:

            current = queue.pop(0)

            for neighbor in self.neighbors(current):

                neighbor = neighbor.lower()

                if neighbor not in expanded:

                    expanded.add(neighbor)

                    queue.append(neighbor)

        return sorted(expanded)
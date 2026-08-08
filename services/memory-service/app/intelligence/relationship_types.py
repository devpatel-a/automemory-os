from enum import Enum


class RelationshipType(str, Enum):

    RELATED = "related"

    SUPPORTS = "supports"

    CONTRADICTS = "contradicts"

    DUPLICATE_OF = "duplicate_of"

    PART_OF = "part_of"

    CAUSES = "causes"

    PREFERS = "prefers"

    LOCATED_AT = "located_at"

    WORKS_WITH = "works_with"

    BELONGS_TO = "belongs_to"
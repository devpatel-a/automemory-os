import spacy
from app.knowledge.fact_models import KnowledgeFact
from app.understanding.models import ParsedMemory
from app.knowledge.temporal_cues import (
    FUTURE_CUES,
    INTENTION_VERB_LEMMAS,
    NEGATION_TRANSITION_CUES,
    PAST_CUES,
    contains_cue,
    has_transition_evidence,
)

nlp = spacy.load("en_core_web_sm")

USER_PRONOUNS = {"i", "me", "my", "myself"}
RELATION_NOUNS = {
    "brother": "brother",
    "sister": "sister",
    "mother": "mother",
    "father": "father",
    "friend": "friend",
    "colleague": "colleague",
    "wife": "wife",
    "husband": "husband",
    "son": "son",
    "daughter": "daughter",
    "boss": "boss",
    "manager": "manager",
    "partner": "partner",
}
ABSTRACT_CONCEPT_NOUNS = {
    "language", "concept", "framework", "library", "code", "script",
    "method", "syntax", "service", "app", "software", "tool",
    "technique", "process", "strategy", "algorithm"
}

VERB_ATTRIBUTE_MAP = {
    "live": ("residence", "LOCATION"),
    "reside": ("residence", "LOCATION"),
    "stay": ("residence", "LOCATION"),
    "move": ("residence", "LOCATION"),
    "work": ("employer", "EMPLOYMENT"),
    "employed": ("employer", "EMPLOYMENT"),
    "transfer": ("employer", "EMPLOYMENT"),
    "prefer": ("preference", "PREFERENCE"),
    "like": ("preference", "PREFERENCE"),
    "love": ("preference", "PREFERENCE"),
    "enjoy": ("preference", "PREFERENCE"),
    "learn": ("learning_topic", "LEARNING"),
    "study": ("learning_topic", "LEARNING"),
    "master": ("learning_topic", "LEARNING"),
    "own": ("device", "DEVICE"),
    "play": ("activity", "ACTIVITY"),
    "practice": ("activity", "ACTIVITY"),
}

NOUN_ATTRIBUTE_MAP = {
    "location": ("residence", "LOCATION"),
    "city": ("residence", "LOCATION"),
    "residence": ("residence", "LOCATION"),
    "employer": ("employer", "EMPLOYMENT"),
    "company": ("employer", "EMPLOYMENT"),
    "workplace": ("employer", "EMPLOYMENT"),
    "preference": ("preference", "PREFERENCE"),
    "drink": ("favorite_drink", "PREFERENCE"),
    "food": ("preference", "PREFERENCE"),
    "language": ("preference", "PREFERENCE"),
    "topic": ("learning_topic", "LEARNING"),
    "name": ("name", "PROFILE"),
    "age": ("age", "PROFILE"),
}


EMPLOYMENT_PREPOSITIONS = {"at", "for"}


def _work_non_employment_preposition(verb_token) -> str | None:
    """
    For 'work': the first governing preposition when none of them marks
    employment ("work on X", "work with X"), else None ("work at/for X",
    or no preposition at all).
    """
    preps = [child.lower_ for child in verb_token.children if child.dep_ == "prep"]
    if not preps or any(p in EMPLOYMENT_PREPOSITIONS for p in preps):
        return None
    return preps[0]


def extract_fact(memory: ParsedMemory) -> KnowledgeFact | None:
    """
    Generic linguistic fact extractor using spaCy dependency parsing, POS tags,
    noun chunks, and centralized canonical attribute normalization.
    Does NOT depend on database IDs or memory persistence structures during NLP extraction.
    """
    if not memory or not memory.content or not memory.content.strip():
        return None

    raw_text = memory.content.strip()
    doc = nlp(raw_text)

    # 1. Subject & Entity Resolution + Explicit Entity Relationship Extraction
    entity = "user"
    relationship_to_user = None
    subj_token = None
    verb_token = None

    for token in doc:
        if token.dep_ in ("nsubj", "nsubjpass"):
            subj_token = token
            break

    for token in doc:
        if token.pos_ in ("VERB", "AUX") and token.dep_ not in ("aux", "auxpass"):
            verb_token = token
            break

    # Intention verbs ("plan", "intend", ...) describe a planned state carried by
    # their open clausal complement: "I am planning to move to Bangalore".
    is_intention = False
    if verb_token is not None and verb_token.lemma_.lower() in INTENTION_VERB_LEMMAS:
        complement = next(
            (c for c in verb_token.children if c.dep_ == "xcomp" and c.pos_ in ("VERB", "AUX")),
            None,
        )
        if complement is not None:
            verb_token = complement
            is_intention = True
    elif (
        verb_token is not None
        and verb_token.lemma_.lower() == "use"
        and verb_token.tag_ == "VBD"
        and verb_token.i + 1 < len(doc)
        and doc[verb_token.i + 1].lower_ == "to"
    ):
        # Habitual-past aspect "used to <verb>": the fact is about <verb>
        # ("I used to live in Mumbai" is residence, not tool usage).
        complement = next(
            (c for c in verb_token.children if c.dep_ == "xcomp" and c.pos_ in ("VERB", "AUX")),
            None,
        )
        if complement is not None:
            verb_token = complement

    possessive_my = any(t.lower_ in USER_PRONOUNS and t.dep_ == "poss" for t in doc)

    if subj_token:
        subtree_lemmas = [t.lemma_.lower() for t in subj_token.subtree]
        for r_noun, r_rel in RELATION_NOUNS.items():
            if r_noun in subtree_lemmas and possessive_my:
                relationship_to_user = r_rel
                break

        propn_tokens = [t.text for t in subj_token.subtree if t.pos_ == "PROPN" and t.lower_ not in USER_PRONOUNS]
        if propn_tokens:
            entity = " ".join(propn_tokens)
        elif possessive_my:
            if subj_token.lemma_.lower() in RELATION_NOUNS:
                entity = subj_token.text
            else:
                entity = "user"
        elif subj_token.lower_ not in USER_PRONOUNS:
            entity = subj_token.text

    # 2. Attribute & Fact Type Extraction via Centralized Linguistic Normalization
    attribute = None
    fact_type = "OTHER"
    verb_lemma = verb_token.lemma_.lower() if verb_token else ""

    if verb_token and verb_token.lemma_ in ("be", "is", "am", "are"):
        head_noun = None
        for token in doc:
            if token.pos_ == "NOUN" and token.dep_ in ("nsubj", "attr"):
                head_noun = token.lemma_.lower()
                break
        if head_noun in NOUN_ATTRIBUTE_MAP:
            attribute, fact_type = NOUN_ATTRIBUTE_MAP[head_noun]
        elif head_noun:
            attribute = head_noun
            fact_type = "PROFILE"
    elif verb_lemma == "use":
        dobj_token = None
        for token in doc:
            if token.dep_ == "dobj":
                dobj_token = token
                break

        has_determiner = False
        is_abstract = False
        is_bare_propn = False

        if dobj_token:
            has_determiner = any(t.dep_ in ("det", "poss") for t in dobj_token.subtree)
            head_lemma = dobj_token.lemma_.lower()
            is_abstract = head_lemma in ABSTRACT_CONCEPT_NOUNS
            is_bare_propn = (dobj_token.pos_ == "PROPN" and not has_determiner)

        has_tool_adjunct = any(t.lower_ in ("for", "to") for t in doc)

        if dobj_token and not is_abstract and not is_bare_propn and (has_determiner or not has_tool_adjunct):
            attribute, fact_type = "device", "DEVICE"
        else:
            attribute, fact_type = "tool", "OTHER"
    elif verb_lemma == "work" and _work_non_employment_preposition(verb_token):
        # "work on my laptop" / "work with William" describe a focus or a
        # collaborator, not an employer.
        attribute, fact_type = f"work_{_work_non_employment_preposition(verb_token)}", "OTHER"
    elif verb_lemma in VERB_ATTRIBUTE_MAP:
        attribute, fact_type = VERB_ATTRIBUTE_MAP[verb_lemma]
    elif verb_token:
        attribute = verb_lemma
        fact_type = "OTHER"

    # 3. Multi-token Value Extraction
    val_tokens = []
    direct_object_value = None
    for token in doc:
        if token.dep_ in ("pobj", "dobj", "attr"):
            chunk = [t for t in token.subtree if t.dep_ in ("compound", "amod", "flat", "pobj", "dobj", "attr") or t == token]
            chunk.sort(key=lambda t: t.i)
            val_text = " ".join(t.text for t in chunk).strip(".,!?\"'")
            if val_text and val_text.lower() not in USER_PRONOUNS and val_text.lower() != entity.lower():
                val_tokens.append(val_text)
                if token.dep_ == "dobj" and direct_object_value is None:
                    direct_object_value = val_text

    if not val_tokens:
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.strip(".,!?\"'")
            if chunk_text.lower() not in USER_PRONOUNS and chunk_text.lower() != (subj_token.text.lower() if subj_token else ""):
                val_tokens.append(chunk_text)

    if direct_object_value:
        # "I use my MacBook Air for development" -> MacBook Air, not development
        value = direct_object_value.strip()
    else:
        value = val_tokens[-1].strip() if val_tokens else ""

    if not value or value.lower() in ("this", "that", "it", "something", "anything"):
        if attribute:
            return KnowledgeFact(
                entity=entity,
                attribute=attribute,
                value=value or "unknown",
                fact_type=fact_type,
                temporal_info="current",
                temporal_state="CURRENT",
                confidence=0.35,
            )
        return None

    # 4. Negation & Temporal State Classification
    is_negated = any(t.dep_ == "neg" or t.lower_ in ("not", "no", "never", "anymore") for t in doc)
    
    temporal_info = "current"
    temporal_state = "CURRENT"
    text_lower = raw_text.lower()

    has_transition = has_transition_evidence(text_lower)

    if contains_cue(text_lower, PAST_CUES) or (verb_token and verb_token.tag_ in ("VBD", "VBN")):
        if has_transition:
            temporal_info = "current"
            temporal_state = "CURRENT"
        else:
            temporal_info = "past"
            temporal_state = "HISTORICAL"
    elif is_intention or contains_cue(text_lower, FUTURE_CUES):
        temporal_info = "future"
        temporal_state = "FUTURE"

    if is_negated and contains_cue(text_lower, NEGATION_TRANSITION_CUES):
        temporal_state = "HISTORICAL"

    # 5. Deterministic Confidence Calculation
    confidence = 0.60
    if attribute and value:
        confidence += 0.25
    if len(value.split()) > 1 or value[0].isupper():
        confidence += 0.10
    confidence = min(confidence, 0.95)

    return KnowledgeFact(
        entity=entity,
        attribute=attribute or "general",
        value=value,
        fact_type=fact_type,
        temporal_info=temporal_info,
        temporal_state=temporal_state,
        relationship_to_user=relationship_to_user,
        is_negated=is_negated,
        confidence=confidence,
    )
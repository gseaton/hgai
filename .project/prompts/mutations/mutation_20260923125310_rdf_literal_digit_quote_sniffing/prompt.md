# Prompt

## Turn 1

Please refactor the RDF import for statements (subject predicate object) Object that starts with a double or single quote should be stored as an text Attribute value in the Subject hypernode with the attribute field being the Predicate (full expanded prefix), and if the Object starts with a digit character, then the Object should be stored as a numeric attribute value in the Subject hypernode as a number literal  (if cast of the Object number fails, store -1 as the numeric attribute value) in the Subject hypernode with the atttribute field name the Predicate (fully expanded prefix).  For example, if prefix ex: is 'http://example.com', a statement 'ex:Eve ex:sex "female"` should add an attribute to hypernode 'http://example.com/Eve' with the attirbute field name of 'http://example.org/sex' and a text attribute value of "female", and a statement 'ex:Eve ex:rating 12.2' should add an attribute to the hypernode 'http://example.com/Eve' with attribute field name of 'http://example.com/rating' and attribute field value of the number literal 12.2.

---

## Turn 2

Please refactor the RDF import for statements (subject predicate object) Object that starts with a double or single quote should be stored as an text Attribute value in the Subject hypernode with the attribute field being the Predicate (full expanded prefix), and if the Object starts with a digit character, then the Object should be stored as a numeric attribute value in the Subject hypernode as a number literal  (if cast of the Object number fails, store -1 as the numeric attribute value) in the Subject hypernode with the atttribute field name the Predicate (fully expanded prefix).  For example, if prefix ex: is 'http://example.com', a statement 'ex:Eve ex:sex "female"` should add an attribute to hypernode 'http://example.com/Eve' with the attirbute field name of 'http://example.org/sex' and a text attribute value of "female", and a statement 'ex:Eve ex:rating 12.2' should add an attribute to the hypernode 'http://example.com/Eve' with attribute field name of 'http://example.com/rating' and attribute field value of the number literal 12.2.  Please note that hypernode RDF references do not start with a number nor quotes and should be considered hypernode/hyperedge references and NOT converted to attribute values.

---

## Turn 3 (clarifying answer, via AskUserQuestion)

Question asked: "The current code deliberately keeps attribute keys as compact CURIEs ('ex:sex'), not full IRIs, because SHQL's `attributes: {key: value}` pattern filter builds a literal MongoDB dot-path query (`attributes.<key>`) from the key — and a key containing dots (which almost every real IRI has, e.g. 'example.com') makes that filter address the wrong nested path and silently stop matching. You're asking for full-IRI keys. How should I handle this conflict?"

Answer selected: "Keep CURIE-compacted keys (decline this part)" — keep attribute keys as sanitized CURIEs like today ('ex:sex'), and implement only the text-vs-numeric value logic (quote/digit sniffing, -1 fallback) described above, not the full-IRI key change.

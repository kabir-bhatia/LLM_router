import numpy as np
import pytest

from router.classify import (EmbeddingClassifier, HybridClassifier, OOS, hybrid_predict, parse_llm_label, pick_threshold,
                             rule_classify)
from router.difficulty import features


@pytest.mark.parametrize("prompt,label", [
    ("Summarise the following text in exactly two sentences: Some long text.", "summarisation"),
    ("Three runners - A, B and C - finished a race with no ties. Who finished first?", "logic"),
    ("Classify the sentiment of this review: 'Great phone, awful battery.'", "sentiment"),
    ("Extract the named entities (people, organisations) from: Priya met Acme in Paris.", "ner"),
    ("Write a Python function that reverses a string.", "code_gen"),
    ("This function has a bug, fix it:\n```python\ndef f(x):\n    return x - 1\n```", "code_debug"),
    ("Build me a complete website for my bakery with ordering and accounts.", OOS),
    ("Translate this paragraph into French: hello there my friend.", OOS),
    ("Hey, how's your day going?", OOS),
])
def test_strong_rules(prompt, label):
    lab, strong = rule_classify(prompt)
    assert lab == label and strong


def test_weak_rules_are_not_strong():
    lab, strong = rule_classify("What causes the seasons on Earth?")
    assert lab == "factual" and not strong
    assert rule_classify("zzz qqq") == (None, False)


def test_embedding_classifier_threshold_and_hybrid():
    rng = np.random.default_rng(0)
    centers = rng.normal(size=(3, 8))
    X = np.vstack([c + 0.05 * rng.normal(size=(20, 8)) for c in centers])
    y = np.repeat(["math", "ner", "logic"], 20)
    clf = EmbeddingClassifier().fit(X, y)
    lab, mp = clf.predict(X)
    assert (lab == y).mean() > 0.95
    tau = pick_threshold(mp, 0.05)
    clf.threshold = max(tau, 0.99)
    far = rng.normal(size=(1, 8)) * 5
    assert clf.predict(far)[0][0] in ("math", "ner", "logic", OOS)
    clf.threshold = 1.01   # nothing can reach it -> everything out of scope
    assert (clf.predict(X)[0] == OOS).all()
    clf.threshold = 0.0
    out, path = hybrid_predict(["Summarise this in one sentence: x.", "something odd"], X[:2], clf)
    assert out[0] == "summarisation" and path == ["rule", "embedding"]


def test_hybrid_classifier_runtime():
    coef = np.array([[5.0, 0.0], [0.0, 5.0]])
    h = HybridClassifier(coef, np.zeros(2), ["math", "ner"], 0.7)
    assert h.predict("anything", np.array([1.0, 0.0]))["label"] == "math"
    assert h.predict("anything", np.array([0.0, 1.0]))["label"] == "ner"
    assert h.predict("anything", np.array([0.1, 0.1]))["label"] == OOS  # near 0.5/0.5 < threshold
    assert h.predict("Summarise this in two sentences", np.array([1.0, 0.0]))["path"] == "rule"


def test_parse_llm_label():
    assert parse_llm_label("math") == "math"
    assert parse_llm_label("out_of_scope") == OOS
    assert parse_llm_label("Label: code debug") == "code_debug"
    assert parse_llm_label("") == OOS


def test_difficulty_features_shape_and_signal():
    a = features("What is 2 + 2?")
    b = features("A company has 7,000 subscribers. Over three consecutive years its count changes by +25%, -50% and +20%. How many at the end?")
    assert a.shape == b.shape and b[3] > a[3]

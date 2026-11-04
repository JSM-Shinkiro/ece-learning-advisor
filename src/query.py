"""Bounded domain aliases for student wording, never academic evidence.

Aliases are explicit development policy, not inferred intent or model output.
Only terms present in the active collection may be added to a search query.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .retrieval import tokenize

QUERY_POLICY_VERSION = "p07-domain-aliases-v1"
MAX_ADDED_TERMS = 12


@dataclass(frozen=True)
class QueryAlias:
    alias_id: str
    required_any: tuple[frozenset[str], ...]
    terms: tuple[str, ...]


def alias(alias_id, groups, terms):
    return QueryAlias(alias_id, tuple(frozenset(group.split()) for group in groups), tuple(terms))


VISUAL_TERMS = ("computer vision", "deep learning", "neural networks")
PROCESSOR_TERMS = ("processor organization", "instruction sets", "memory caches", "computer architecture")
ALIASES = (
    alias("visual_recognition", (
        "image images picture pictures photo photos photograph photographs",
        "recognition recognize recognise recognizing recognising classify classifying classification detect detecting detection identify identifying",
    ), VISUAL_TERMS),
    alias("visual_learning", (
        "image images picture pictures photo photos photograph photographs",
        "computer computers machine machines neural",
        "train training learn learning patterns pattern",
    ), VISUAL_TERMS),
    alias("board_events", (
        "board boards microcontroller microcontrollers arduino mcu",
        "button buttons switch switches polling",
        "react reacts reacting respond responds responding pressed press events event polling interrupt interrupts",
    ), ("microcontrollers", "interrupts", "hardware interfaces", "embedded systems")),
    alias("processor_execution", (
        "cpu processor processors microprocessor microprocessors",
        "instruction instructions opcode opcodes execute executes executing",
    ), PROCESSOR_TERMS),
    alias("chip_execution", (
        "chip chips", "memory machine computer cpu processor execute executes executing opcode opcodes",
        "instruction instructions opcode opcodes execute executes executing",
    ), PROCESSOR_TERMS),
    alias("processor_memory", ("cpu processor processors", "cache caches memory ram"), PROCESSOR_TERMS),
    alias("microcontroller_io", ("gpio uart adc",),
          ("microcontrollers", "hardware interfaces", "serial communication", "analog conversion")),
    alias("coding_foundations", (
        "code coding", "learn learning begin beginner basics scratch new start starting",
    ), ("programming foundations", "C programming", "algorithms")),
    alias("tensor_practice", (
        "tensor tensors minibatch minibatches", "train training learn learning practice weights optimization parameters",
    ), ("deep learning", "neural network", "model parameters", "optimization")),
)


@dataclass(frozen=True)
class QueryInterpretation:
    matched_aliases: tuple[str, ...] = ()
    added_terms: tuple[str, ...] = ()

    def expand(self, text):
        return " ".join((text, *self.added_terms)).strip()

    def trace(self):
        return {"version": QUERY_POLICY_VERSION, "matched_aliases": list(self.matched_aliases),
                "added_terms": list(self.added_terms)}


def catalog_vocabulary(catalog):
    return set(tokenize(" ".join(r.title + " " + r.summary + " " + " ".join(r.topics) for r in catalog.records)))


def interpret_query(text, catalog):
    """Match whole tokens in student text, without chaining alias expansions.

    Matching uses original wording only; labels and evidence never change.
    Retaining only existing catalog terms avoids inventing subject coverage.
    """
    original = set(re.findall(r"[a-z0-9]+", text.casefold()))
    vocabulary = catalog_vocabulary(catalog)
    matched, added = [], []
    for rule in ALIASES:
        if not all(original & group for group in rule.required_any):
            continue
        supported = [term for term in rule.terms if set(tokenize(term)) <= vocabulary]
        if not supported:
            continue
        matched.append(rule.alias_id)
        for term in supported:
            if term not in added and not set(tokenize(term)) <= original and len(added) < MAX_ADDED_TERMS:
                added.append(term)
    return QueryInterpretation(tuple(matched), tuple(added))

"""Experimental ConvoKit bridge for thread-aware analysis."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ._optional import require


def build_conversation_corpus(records: Iterable[Mapping[str, Any]]) -> Any:
    """Build a ConvoKit Corpus from neutral message dictionaries.

    Expected fields are ``id``, ``text`` and ``speaker`` (or ``speaker_id``).
    ``conversation_id`` and ``reply_to`` are optional. No analysis is run.
    """
    convokit = require("convokit")
    speakers: dict[str, Any] = {}
    utterances: list[Any] = []

    for index, record in enumerate(records):
        speaker_id = str(record.get("speaker") or record.get("speaker_id") or "unknown")
        speaker = speakers.setdefault(speaker_id, convokit.Speaker(id=speaker_id))
        utterance_id = str(record.get("id") or f"utterance-{index}")
        conversation_id = record.get("conversation_id")
        reply_to = record.get("reply_to")
        utterances.append(
            convokit.Utterance(
                id=utterance_id,
                speaker=speaker,
                conversation_id=None if conversation_id is None else str(conversation_id),
                reply_to=None if reply_to is None else str(reply_to),
                text=str(record.get("text") or ""),
            )
        )

    return convokit.Corpus(utterances=utterances)

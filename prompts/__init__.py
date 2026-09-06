# -*- coding: utf-8 -*-
"""Prompt modules for LaclauGPT 2.0.

Every prompt is built from parts:
    topic_background  (what was collected — per run)
    source_metadata   (which platform/country, metadata availability)
    context memory    (glossary + previous stage output)
    stage instructions (the actual task)
Nothing about the topic is hardcoded in analysis prompts anymore.
"""
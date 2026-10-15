"""Prefer actual PDF outlines; otherwise expose explicitly heuristic title levels."""
import re


def heading_level(title):
    match = re.match(r"^(\d+(?:\.\d+){0,2})\s+", title)
    return len(match.group(1).split(".")) if match else 1


def build_tree(headings):
    roots, stack = [], []
    for heading in headings:
        node = {**heading, "children": []}
        level = heading.get("level", 1)
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            roots.append(node)
        stack.append(node)
    return roots

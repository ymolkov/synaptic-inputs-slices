#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


NEWLABEL_RE = re.compile(r"^\\newlabel\{([^}]+)\}\{\{([^}]+)\}")


def load_aux_labels(aux_path: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    with aux_path.open() as handle:
        for line in handle:
            match = NEWLABEL_RE.match(line)
            if match:
                labels[match.group(1)] = match.group(2)
    return labels


def stringify_inlines(inlines) -> str:
    parts: list[str] = []
    for inline in inlines:
        if inline.get("t") == "Str":
            parts.append(inline.get("c", ""))
        elif inline.get("t") == "Space":
            parts.append(" ")
        elif inline.get("t") == "SoftBreak":
            parts.append("\n")
    return "".join(parts)


def prefix_inlines(prefix: str) -> list[dict]:
    pieces = prefix.split()
    out: list[dict] = []
    for i, piece in enumerate(pieces):
        if i:
            out.append({"t": "Space"})
        out.append({"t": "Str", "c": piece})
    out.append({"t": "Space"})
    return out


def maybe_prefix_caption_blocks(blocks, prefix: str) -> None:
    if not blocks:
        return
    first = blocks[0]
    if first.get("t") not in ("Plain", "Para"):
        return
    if stringify_inlines(first.get("c", [])).startswith(prefix):
        return
    first["c"] = prefix_inlines(prefix) + first.get("c", [])


def rewrite_captions(node, labels: dict[str, str]) -> None:
    if isinstance(node, dict):
        node_type = node.get("t")

        if node_type == "Figure":
            label = node["c"][0][0]
            number = labels.get(label)
            if number:
                caption_blocks = node["c"][1][1]
                maybe_prefix_caption_blocks(caption_blocks, f"Figure {number}.")

        if node_type == "Div":
            label = node["c"][0][0]
            number = labels.get(label)
            if number and (label.startswith("tab:") or label.startswith("tbl:")):
                for block in node["c"][1]:
                    if isinstance(block, dict) and block.get("t") == "Table":
                        caption_blocks = block["c"][1][1]
                        maybe_prefix_caption_blocks(caption_blocks, f"Table {number}.")

        for value in node.values():
            rewrite_captions(value, labels)
    elif isinstance(node, list):
        for item in node:
            rewrite_captions(item, labels)


def rewrite_links(node, labels: dict[str, str]) -> None:
    if isinstance(node, dict):
        if node.get("t") == "Link":
            attr, content, target = node["c"]
            attrs = {k: v for k, v in attr[2]}
            if attrs.get("reference-type") == "ref":
                label = attrs.get("reference", "")
                if label.startswith("eq:"):
                    number = labels.get(label)
                    text = stringify_inlines(content)
                    if number and text == f"[{label}]":
                        node["c"][1] = [{"t": "Str", "c": number}]
        for value in node.values():
            rewrite_links(value, labels)
    elif isinstance(node, list):
        for item in node:
            rewrite_links(item, labels)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Pandoc reference text from a LaTeX .aux file.")
    parser.add_argument("--aux", required=True, help="Path to the LaTeX .aux file.")
    parser.add_argument("--input", required=True, help="Input Pandoc JSON path.")
    parser.add_argument("--output", required=True, help="Output Pandoc JSON path.")
    args = parser.parse_args()

    labels = load_aux_labels(Path(args.aux))
    with Path(args.input).open() as handle:
        document = json.load(handle)

    rewrite_links(document, labels)
    rewrite_captions(document, labels)

    with Path(args.output).open("w") as handle:
        json.dump(document, handle)


if __name__ == "__main__":
    main()

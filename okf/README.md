# Bicho PR Reviewer — OKF Knowledge Bundle

This directory is an **[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)**
(OKF v0.1) bundle: a self-describing, hierarchical set of Markdown concepts with YAML frontmatter,
cross-linked as a knowledge graph. It captures the knowledge behind Bicho PR Reviewer — what it is,
how it is built, the decisions that shaped it, and how to operate it — in a portable, agent- and
human-readable form.

Start at [index.md](index.md). Each concept is a plain Markdown file: `cat` it to read it, follow the
links to traverse it. The canonical, code-adjacent docs still live at the repository root
([README](../README.md), [ARCHITECTURE](../ARCHITECTURE.md), [docs/adr](../docs/adr/)); this bundle
is the OKF projection of that knowledge, and each concept cites its source via the `resource` field.

To publish it into a catalog, copy `okf/` as a bundle (e.g. into
`GoogleCloudPlatform/knowledge-catalog/okf/bundles/bicho-pr-reviewer/`) via a fork and PR — a bundle
is valid as a subdirectory of any repository.

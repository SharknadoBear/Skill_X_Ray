# Skill X-Ray

Skill X-Ray casts an agent skill into validated JSON and a standalone interactive HTML workflow graph. The graph helps inspect documented states, gates, tools, examples, iterations, and explicit subskill calls. In graph version 0.2, an **Example** button explains one illustrative input at each working state, gate, and inter-skill call. The source skill remains authoritative.

Start with [SKILL.md](SKILL.md) for the workflow and its boundaries. The repository also contains the schema and notation in `schemas/` and `references/`, the Python inventory, validation, and rendering scripts in `scripts/`, the standalone viewer assets in `assets/` and `templates/`, and example graphs in `examples/`.

## Check the repository

```powershell
python -m unittest discover -s tests -v
```

This repository is the version-controlled maintenance copy of the installed `skill-xray` skill. Project objective and session memos are kept in the sibling `Memo` folder of the local working directory.

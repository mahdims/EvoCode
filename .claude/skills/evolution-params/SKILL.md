---
name: evolve/evolution-params
description: Gathers evolution loop parameters for the EvoCode process.
---

# Evolution Loop Parameters

When this subskill is invoked, ask the user for the parameters for the evolution script.

## Parameter Options
Offer the following options:
- `Use default`
- `Path to parameter file`
- `Parameter JSON string`

## Processing Rules
- If a user selects `Use default`, we do not need to provide a JSON file to our script.
- If a parameter JSON string is provided, create a temporary JSON file in `/tmp/$(openssl rand -base64 12).json`
- If a path to a parameter file is provided, validate that the file exists

## Output
Return the path to the parameter file (either default, user-provided, or temporary) to the calling skill.

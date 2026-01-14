# New Project - Orchestrator Direct Task

> **Direct execution - no delegation needed.**

## Usage

```
/new-project <path> [options]
```

## Arguments

- `path` - Path to create the new project (required)
- `--no-git` - Don't initialize git repository
- `--pm <tool>` - Set PM tool (asana|trello|github|linear|none)
- `--repo <type>` - Set repo type (github|gitlab)

## Examples

```
/new-project ~/projects/my-new-app
/new-project ../../projects/test-auction-site
/new-project ./my-app --pm trello --repo gitlab
```

## Execution

Run the create-project script with the provided arguments:

```bash
.claude/scripts/create-project.sh $ARGUMENTS
```

## After Execution

Report the result to the user and remind them of next steps:
1. `cd` to the new project
2. Edit `config.yaml` with project settings
3. Edit `.env` with API keys
4. Authenticate git provider (`gh auth login` or `glab auth login`)
5. Start with `/discover`

## Project Path

$ARGUMENTS

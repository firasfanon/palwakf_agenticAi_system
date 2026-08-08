# Operational Activation Policy V1

## Scope
This policy applies only to `palwakf_local_agents`. It does not authorize a change in PalWakf platform, Supabase, Flutter source, SQL, Git history, deployment, or secrets.

## Default deny
Every capability is denied unless explicitly enabled in the registry and task contract.

## V1 runnable agents
Only `coordinator` and `sovereignty_reviewer` may create read-only reports. All other agents remain admission-only.

## V1 tool boundary
Tool gateway permits only local read operations within approved roots. It cannot execute shell commands, SQL, Git write, network calls, deployment, or secret reads.

## Human control
Human approval is mandatory before a Draft task becomes runnable; before a memory record becomes Approved; and before any Skill, policy, or runtime expansion.

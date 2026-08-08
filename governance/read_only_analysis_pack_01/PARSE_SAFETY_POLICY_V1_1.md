# Pack 01 Parse-Safety Policy V1.1

- All package PowerShell scripts must parse under the local Windows PowerShell parser before installation.
- Error-string interpolation must not contain unsafe `$variable:` syntax.
- Use `${variable}:` or the format operator when a colon immediately follows an interpolated variable.
- A package syntax gate is mandatory before target preflight and WhatIf.
- Any parser failure means no installer invocation, no runtime activation, and no model execution.

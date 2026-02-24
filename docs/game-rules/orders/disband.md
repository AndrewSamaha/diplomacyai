# Disband Orders

This document explains how **disband orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

Disbands are issued during adjustment phases (unless a retreat disband is required).

1. **Disband a unit (adjustments)**

```
<UNIT> <FROM> D
```

Example:

```
A PAR D
```

2. **Forced disband (retreats)**

```
<UNIT> <FROM> D
```

Example:

```
F NTH D
```

## Examples

```
A MUN D
F STP/SC D
F ION D
```

## Interpretation Rules

1. **Adjustment disbands happen when you have more units than centers.**
   - Required disbands = `(current units) - (controlled centers)` if positive.

2. **Disband orders are only legal in adjustment phases.**
   - Outside adjustments, a disband order is ignored or invalid.

3. **You can choose which units to disband.**
   - Any of your existing units can be disbanded.

4. **Coasts must be specified for fleets when required.**
   - Example: `F STP/SC D` is valid.
   - `F STP D` is ambiguous if the fleet is on a specific coast.

5. **Retreat disbands are forced when no valid retreat exists.**
   - In retreat phases, a dislodged unit with no legal retreat must disband.

## Common Errors

- **Not in adjustments**: disband orders are ignored or invalid outside adjustment phases.
- **Missing coast**: `F STP D` is invalid if a specific coast is required.
- **Too few disbands**: you must submit enough disbands to match required removals.

## Quick Reference

- Disband: `A/F <FROM> D`

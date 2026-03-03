# Hold Orders

This document explains how **hold orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

```
<UNIT> <FROM> H
```

- `<UNIT>` is `A` (army) or `F` (fleet).
- `<FROM>` is the unit’s current location.
- `H` indicates a hold order.

Example:

```
A PAR H
```

## Examples

```
A MUN H
F NTH H
F STP/SC H
A SER H
```

## Interpretation Rules

1. **Hold means no movement.**
   - The unit stays in place for the phase.

2. **Hold is always legal if the unit is in a legal location.**
   - A hold does not require adjacency checks.

3. **Coasts must be specified for fleets when required.**
   - Example: `F STP/SC H` is valid.
   - `F STP H` is ambiguous if the fleet is on a specific coast.

4. **Hold can be supported.**
   - Other units can support a hold order to increase defense strength.

## Common Errors

- **Wrong unit type**: `F PAR H` is invalid because PAR is inland.
- **Missing coast**: `F STP H` is invalid if the fleet is on a specific coast.

## Quick Reference

- Hold: `A/F <FROM> H`

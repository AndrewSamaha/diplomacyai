# Support Orders

This document explains how **support orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

Support comes in two forms:

1. **Support Hold**

```
<UNIT> <FROM> S <UNIT> <TARGET>
```

Example:

```
A BUR S A PAR
```

2. **Support Move**

```
<UNIT> <FROM> S <UNIT> <TARGET> - <DEST>
```

Example:

```
A BUR S A PAR - MUN
```

## Examples

```
F NTH S A LON
A RUH S A KIE - MUN
F ION S A APU - TUN
F BOT S F SWE - BAL
```

## Interpretation Rules

1. **The supporter must be adjacent to the supported destination.**
   - For support hold: supporter must be adjacent to the supported unit’s location.
   - For support move: supporter must be adjacent to the supported unit’s destination.

2. **Adjacency is unit‑type specific.**
   - An army can only support across land adjacency.
   - A fleet can only support across water/coastal adjacency.

3. **Supported unit type must be explicit.**
   - Support orders must include the supported unit type (`A` or `F`).

4. **Coasts matter for fleets.**
   - If a fleet supports a move to a multi‑coast province, the coast must be specified.
   - Example: `F MAO S F SPA/NC - POR` is valid; `F MAO S F SPA - POR` is ambiguous.

5. **Support is cut by attack.**
   - A unit’s support is cut if it is attacked from any province **other than** the province the support is being given against.
   - If the attack comes from the supported destination, the support is not cut.

6. **Support can be illegal if the supported move is illegal.**
   - If the supported unit cannot legally move to the destination, the support is invalid.

## Common Errors

- **Not adjacent to destination**: `A PAR S A MAR - MUN` is invalid if PAR is not adjacent to MUN.
- **Wrong unit type**: `F PAR S A BUR - PIC` is invalid because a fleet cannot be in PAR.
- **Missing coast**: `F MAO S F SPA - POR` is invalid if SPA has multiple coasts and a fleet is involved.

## Quick Reference

- Support hold: `A/F <FROM> S A/F <TARGET>`
- Support move: `A/F <FROM> S A/F <TARGET> - <DEST>`

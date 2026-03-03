# Retreat Orders

This document explains how **retreat orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

Retreats are issued only for dislodged units during a retreat phase.

1. **Retreat to a new location**

```
<UNIT> <FROM> R <TO>
```

Example:

```
A MUN R BOH
```

2. **Disband (no retreat)**

```
<UNIT> <FROM> D
```

Example:

```
A MUN D
```

## Examples

```
A PAR R GAS
F NTH R NWG
F STP/SC R BOT
A SER D
```

## Interpretation Rules

1. **Only dislodged units can retreat.**
   - Retreat orders are only allowed in retreat phases.

2. **Retreat destinations must be legal and empty.**
   - The destination must be adjacent and unoccupied.
   - A unit cannot retreat to the space the attacker came from.

3. **Retreats cannot be supported or convoyed.**
   - No support or convoy rules apply during retreats.

4. **Coasts must be specified for fleets when required.**
   - Example: `F STP/SC R BOT` is valid.
   - `F STP R BOT` is ambiguous if the fleet is on a specific coast.

5. **Disband is always legal.**
   - If no legal retreats exist, the unit is forced to disband.

## Common Errors

- **Not dislodged**: `A PAR R GAS` is invalid if PAR was not dislodged.
- **Retreat to attacker’s origin**: invalid if the attacker came from the destination.
- **Occupied destination**: retreats cannot go to a space with any unit.
- **Missing coast**: `F STP R BOT` is invalid if the fleet is on a specific coast.

## Quick Reference

- Retreat: `A/F <FROM> R <TO>`
- Disband: `A/F <FROM> D`

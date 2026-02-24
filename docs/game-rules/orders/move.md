# Move Orders

This document explains how **move orders** work in Diplomacy, how to interpret their syntax, and common edge cases around coasts and unit types.

## Core Syntax

```
<UNIT> <FROM> - <TO>
```

- `<UNIT>` is `A` (army) or `F` (fleet).
- `<FROM>` is the unit’s current location.
- `<TO>` is the destination.
- The dash `-` indicates a move order.

Example:

```
A PAR - BUR
```

## Examples

```
A APU - VEN
F NTH - ENG
F STP/SC - FIN
A BUL - SER
```

## Interpretation Rules

1. **Armies move over land.**
   - Armies can move between adjacent land provinces and from land to coastal provinces.
   - Armies cannot move into sea zones.

2. **Fleets move over water and along coasts.**
   - Fleets can move between adjacent sea zones.
   - Fleets can move between adjacent sea zones and coastal provinces.
   - Fleets cannot move into inland land provinces.

3. **Coasts must be specified when required.**
   - Provinces with multiple coasts require the coast to be specified for fleets.
   - Example: `F STP/SC - FIN` is valid, while `F STP - FIN` is ambiguous.
   - Armies do not use coast suffixes.

4. **Moves require adjacency.**
   - A move is legal only if the destination is adjacent to the source for the given unit type.
   - Adjacency can differ for armies vs fleets.

5. **Convoys are separate from normal moves.**
   - An army that moves by convoy uses the `VIA` keyword.
   - Example: `A LON - BEL VIA`
   - This is not a standard land move and requires convoying fleets.

## Common Errors

- **Wrong unit type**: `F PAR - BUR` is invalid because PAR is inland.
- **Missing coast**: `F STP - FIN` is invalid; must specify `STP/SC`.
- **Not adjacent**: `A PAR - MUN` is invalid if PAR and MUN are not adjacent on the map.

## Quick Reference

- Army move: `A <LAND/COAST> - <LAND/COAST>`
- Fleet move: `F <WATER/COAST> - <WATER/COAST>`
- Convoyed army move: `A <COAST> - <COAST> VIA`

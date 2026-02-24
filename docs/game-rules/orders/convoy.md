# Convoy Orders

This document explains how **convoy orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

Convoying uses two order types:

1. **Army move via convoy**

```
A <FROM> - <TO> VIA
```

Example:

```
A LON - BEL VIA
```

2. **Fleet convoy order**

```
F <SEA> C A <FROM> - <TO>
```

Example:

```
F ENG C A LON - BEL
```

## Examples

```
A APU - TUN VIA
F ION C A APU - TUN
F TYR C A NAP - TUN
```

## Interpretation Rules

1. **Only armies are convoyed.**
   - Fleets cannot be convoyed.

2. **Convoyed moves must start and end on coasts.**
   - The army must start in a coastal province.
   - The destination must be a coastal province.

3. **Convoying fleets must be in sea zones.**
   - Fleets in coastal land provinces cannot convoy.

4. **A convoy requires a valid sea path.**
   - A continuous chain of convoying fleets must connect the source and destination.

5. **Convoy orders must match the army’s move.**
   - The fleet’s convoy order must specify the exact same `A <FROM> - <TO>` as the army’s `VIA` order.

6. **Convoys can be disrupted.**
   - If any convoying fleet is dislodged, the convoy may fail.

7. **Convoyed moves still resolve like normal moves.**
   - The army can bounce, succeed, or be dislodged depending on support and conflict.

## Common Errors

- **Army not on coast**: `A PAR - LON VIA` is invalid (PAR is inland).
- **Fleet not in sea**: `F NAP C A ROM - TUN` is invalid (NAP is a coastal land province).
- **Missing VIA**: `A LON - BEL` is a normal move, not a convoy.
- **Mismatched orders**: Fleet convoy order doesn’t match the army’s move.

## Quick Reference

- Army convoy move: `A <COAST> - <COAST> VIA`
- Fleet convoy order: `F <SEA> C A <COAST> - <COAST>`

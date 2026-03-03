# Build Orders

This document explains how **build orders** work in Diplomacy, how to interpret their syntax, and common edge cases.

## Core Syntax

Builds are issued only during adjustment phases.

1. **Build an army or fleet**

```
<UNIT> <LOC> B
```

Example:

```
A PAR B
```

2. **Waive a build**

```
WAIVE
```

Example:

```
WAIVE
```

## Examples

```
A PAR B
F BRE B
F STP/SC B
WAIVE
```

## Interpretation Rules

1. **Builds happen in adjustment phases.**
   - Build orders are only legal in adjustment phases (typically Winter).

2. **Build locations must be owned home centers and empty.**
   - You can only build in your home supply centers that you currently control.
   - The location must be unoccupied.

3. **Fleets must be built on coasts when required.**
   - Multi‑coast provinces require a coast for fleet builds.
   - Example: `F STP/SC B` is valid.

4. **Build count is limited by available builds.**
   - The number of builds equals `(controlled centers) - (current units)`.
   - If this is zero or negative, you cannot build.

5. **Waive is always legal if you have unused builds.**
   - Use `WAIVE` to skip a build you could otherwise take.

## Common Errors

- **Not in adjustments**: build orders are ignored or invalid outside adjustment phases.
- **Not a home center**: cannot build in captured non‑home centers.
- **Occupied location**: cannot build where a unit already exists.
- **Missing coast**: `F STP B` is invalid if a specific coast is required.

## Quick Reference

- Build: `A/F <HOME CENTER> B`
- Waive: `WAIVE`

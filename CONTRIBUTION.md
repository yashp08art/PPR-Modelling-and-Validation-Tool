# Contribution

This repository is a **fork** of the original, hosted on a teammate's account:
<https://github.com/yashp08art/PPR-Modelling-and-Validation-Tool>

Forking preserves the original commit history and attribution. The code was
pushed from one account in a single upload, so the commit history does not show
who wrote which module.

## Project

*Python for Production Systems Engineering, Otto von Guericke University
Magdeburg. Winter Semester 2025/26, submitted 25 April 2026.*

Group of two.

## Navroop Singh's scope

**The engineering and reliability views** over the shared Product–Process–Resource
graph.

- **Basic Engineering view** — projects cost, mass, assembly time and Overall
  Equipment Effectiveness into the node labels, and aggregates them into
  system-level KPIs.
- **Reliability view** — projects MTBF, MTTR, failure probability and maintenance
  interval, and overlays failure-dependency edges as dashed arrows on top of the
  PPR structure (not as PPR edges, which would corrupt the conformance rules).
  Ranks nodes by MTBF/MTTR and flags failure probability above 4%. The same
  overlay drives the view-specific failure-propagation check, so the view and the
  algorithm cannot disagree.

## Honest limitations

- Reliability data lives in a module-level table, not in the model file — trivial
  to demo, wrong for provenance.
- The failure-dependency list is duplicated across two modules rather than held
  as one shared constant.
- The tool imports three formats and exports none.
- The graph layer was deliberately kept free of Streamlit so it could be
  unit-tested — and then no tests were written.

Full write-up: <https://singhnavroop1401-lab.github.io/projects/01-ppr-tool.html>
Live demo: <https://ppr-modelling-and-validation-tool-hz9epskbcjybcqievvs3cj.streamlit.app/>

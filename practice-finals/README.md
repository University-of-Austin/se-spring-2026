# SE Spring 2026 — Practice Finals

Two extra sample finals (B and C) built to match the structure of the course's official
"Final Exam — Sample" (`final practice.pdf` / `final solutions.pdf`):

- 7 questions each, in the same 5 categories with the same 2 / 2 / 1 / 1 / 1 split
  (Trace-through ×2, Spot the bug ×2, Specification ×1, Code review ×1, Short design ×1).
- Same intentionally-hard, "skills the agent can't do for you" framing.
- Each exam has a questions-only PDF and a separate solutions PDF (green answer boxes),
  exactly like the original pair.

## The PDFs

| File | What it is |
|------|------------|
| `Sample-Final-B.pdf` | Exam B — questions only (print this, do it cold) |
| `Sample-Final-B-Solutions.pdf` | Exam B with answers |
| `Sample-Final-C.pdf` | Exam C — questions only |
| `Sample-Final-C-Solutions.pdf` | Exam C with answers |

## Topic coverage

The official sample skipped three in-scope lectures. Between B and C, these two cover **all ten**
lectures 5.1–10.1 — including the three the original left out (7.1 React state/effects,
7.2 cloud deployment, 10.1 agents).

- **Exam B:** 7.1 React state/effects, 5.1 JS/TS, 5.2 fetch/races, 9.2 security, 6.1 React, 8.2 CI/CD, 7.2 deployment
- **Exam C:** 10.1 agents, 9.1 concurrency, 6.1 React, 9.2 security, 5.2 fetch/races, 8.1 Docker, 10.1 agents

## Regenerating the PDFs (if you edit the questions)

The PDFs are built from the `.typ` (Typst) source files. `sol=0` makes the questions-only
version; `sol=1` makes the solutions version. From this folder:

```
typst compile --input sol=0 final-b.typ "Sample-Final-B.pdf"
typst compile --input sol=1 final-b.typ "Sample-Final-B-Solutions.pdf"
typst compile --input sol=0 final-c.typ "Sample-Final-C.pdf"
typst compile --input sol=1 final-c.typ "Sample-Final-C-Solutions.pdf"
```

`template.typ` holds the shared styling (the header table, code blocks, green solution boxes).

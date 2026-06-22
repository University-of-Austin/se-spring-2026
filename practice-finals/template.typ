// Shared styling for the UATX Software Engineering sample finals.
// Compile twice from each content file:
//   typst compile --input sol=0 final-b.typ "Sample-Final-B.pdf"
//   typst compile --input sol=1 final-b.typ "Sample-Final-B-Solutions.pdf"

#let show-solutions = sys.inputs.at("sol", default: "0") == "1"

// palette tuned to match the original "final practice.pdf" look
#let muted     = rgb("#6b6b6b")
#let codebg    = rgb("#f3f3f4")
#let solbg     = rgb("#eaf5ec")
#let solborder = rgb("#cfe6d4")
#let sollabel  = rgb("#2e7d4f")
#let tableline = rgb("#d9d9d9")

#let bodyfont = ("Helvetica Neue", "Arial")
#let monofont = ("Menlo", "DejaVu Sans Mono", "Courier New")

// ---- question header: "Question N" left, topic/category tag right, then a rule ----
#let qhead(n, tag) = {
  grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
    text(weight: "bold", size: 13pt)[Question #n],
    text(fill: muted, size: 9.5pt)[#tag],
  )
  v(1pt)
  line(length: 100%, stroke: 0.8pt + rgb("#333333"))
  v(3pt)
}

// ---- one question. cat = short category (shown on the exam); tag = full topic tag (shown on solutions) ----
#let q(n, cat, tag, body) = {
  if not show-solutions { pagebreak(weak: true) } else { v(15pt) }
  qhead(n, if show-solutions { tag } else { cat })
  body
}

// ---- green SOLUTION callout; renders only when sol=1 ----
#let solution(body) = if show-solutions {
  v(8pt)
  block(
    width: 100%,
    fill: solbg,
    stroke: 0.6pt + solborder,
    radius: 4pt,
    inset: 11pt,
  )[
    #text(fill: sollabel, weight: "bold", size: 8.5pt, tracking: 0.6pt)[SOLUTION]
    #v(3pt)
    #body
  ]
}

// ---- the exam-front matter (header table + framing); only on the exam, not the solutions ----
#let intro() = if not show-solutions {
  v(4pt)
  table(
    columns: (110pt, 1fr),
    stroke: 0.5pt + tableline,
    inset: 8pt,
    align: (left + horizon, left + horizon),
    [*Format*],     [Pencil and paper. No computer, phone, notes, or coding agent.],
    [*Time*],       [150 minutes.],
    [*Length*],     [Seven questions, one to two per category.],
    [*Coverage*],   [Lectures 5.1 through 10.1 (JS/TS and the browser, React, deployment, Docker, CI/CD, concurrency, security, agents), plus assignments 3 and 4.],
    [*Categories*], [Trace-through, spot the bug, specification, code review, short design.],
    [*Grading*],    [Curved. The exam is intentionally hard; expect to leave some parts unfinished.],
  )
  v(10pt)
  text(weight: "bold", size: 10.5pt, tracking: 0.5pt)[HOW THIS EXAM THINKS ABOUT AGENTS]
  v(2pt)
  par[The whole semester has leaned into coding agents as the way real engineers work, so an exam that asks you to write working code from scratch on paper would punish you for taking the course seriously. Instead, every question is built around a skill the agent can't do for you: reading code carefully, finding bugs by inspection, writing the spec you'd hand to the agent, judging which of two implementations is better, and making design calls under uncertainty.]
  v(8pt)
  text(weight: "bold", size: 10.5pt, tracking: 0.5pt)[HOW TO USE THIS SAMPLE]
  v(2pt)
  par[This is a representative exam, not the actual one — the real final will have seven questions in the same five categories at roughly the same difficulty. Solutions are in a separate document; try the questions cold first, then check.]
}

// ---- document wrapper ----
#let conf(letter, body) = {
  set page(
    paper: "us-letter",
    margin: (x: 1in, top: 0.9in, bottom: 0.95in),
    footer: context { align(center, text(size: 8pt, fill: muted)[#counter(page).display()]) },
  )
  set text(font: bodyfont, size: 10.5pt, fill: rgb("#1a1a1a"))
  set par(leading: 0.65em, spacing: 0.95em, justify: false)
  set enum(numbering: "1.", spacing: 1.0em, body-indent: 7pt)

  show raw.where(block: true): it => block(
    width: 100%,
    fill: codebg,
    inset: 9pt,
    radius: 3pt,
    text(font: monofont, size: 8.6pt, it),
  )
  show raw.where(block: false): it => box(
    fill: codebg,
    inset: (x: 2pt),
    outset: (y: 2.5pt),
    radius: 2pt,
    text(font: monofont, size: 9pt, it),
  )

  let titletext = "Final Exam — Sample " + letter + (if show-solutions { " — Solutions" } else { "" })
  grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
    text(size: 22pt, weight: "bold")[#titletext],
    if show-solutions { [] } else { text(size: 11pt)[Name: #box(width: 1.8in, stroke: (bottom: 0.6pt))[#v(2pt)]] },
  )
  v(2pt)
  line(length: 100%, stroke: 1.2pt)
  v(2pt)
  text(size: 13pt, fill: muted)[Software Engineering — UATX — Spring 2026]
  intro()
  body
}

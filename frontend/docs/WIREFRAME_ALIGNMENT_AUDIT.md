# Full wireframe alignment audit

Reviewed against all nine original-resolution wireframes and the accompanying leader notes on 2026-07-19.

## Non-negotiable product safeguards

- A calculation is blocked while any source conflict or required confirmation remains. It must not reveal an income total, threshold comparison, score, approval, denial, or ranking.
- A readiness result is `NEEDS_REVIEW` whenever anything required is unresolved. `READY_TO_REVIEW` is reserved for zero unresolved required items.
- A low-confidence extraction is not a prefill: the person must type a value before it can be confirmed.
- Every AI rules answer and derived rule needs a visible citation, rule version, or effective date.
- Exported caseworker packets exclude AI notes, rankings, eligibility decisions, and unconfirmed information. The safety gate must make that visible.

## Screen-by-screen requirements

| Wireframe | Required experience | Current gap to close |
| --- | --- | --- |
| 1. Start | Explain document organization, rule explanation, and packet building alongside privacy and consent. | Keep the consent gate and make the three capabilities clear before a session begins. |
| 2. Progress | Three-stage progress, document/rule/readiness summary, agent activity, and actionable next steps. | Expand the sparse overview with concrete state, activity, and context-aware actions. |
| 3. Upload | PDF-only intake, fixed document types, upload status, and an inventory. | Replace the simple picker/tile presentation with accepted-type guidance and an inventory. |
| 4. Evidence review | Extracted fields beside the PDF, confidence state, source location, and manual entry for uncertain values. | Preserve source boxes and add usable field-to-evidence context plus forced typed confirmation for low confidence. |
| 5. Reconciliation | Confirmed profile with provenance and a conflict resolution workspace. | Replace the profile placeholder and make conflict resolution evidence-led. |
| 6. Rules | Conversational rule help, plain-language support, field prompts, and citation chips. | Keep remote answers/citations and add persistent question context and helpful prompts. |
| 7. Calculations | Transparent formula, source, inclusion/exclusion rule, threshold lookup, and evidence chain. | Never render a result while blocked; add a provenance-oriented layout once it is safe to calculate. |
| 8. Readiness | Confirmed, needs-review, and missing groups; an ordered next-steps plan; summary counts. | Correct the status semantics and make every unresolved item actionable and visible. |
| 9. Packet | Safety gate, section controls, personal vs caseworker template, summary, and final disclaimer. | Connect the backend safety check to the UI and clearly separate personal-only from caseworker-safe content. |

## Implementation order

1. Safety-critical state: blocked calculations, readiness status, manual low-confidence confirmation, and safety-gated export.
2. Missing workflow: profile/reconciliation and source provenance.
3. Layout and navigation refinement: overview, upload inventory, rules prompts, and packet/editor affordances.

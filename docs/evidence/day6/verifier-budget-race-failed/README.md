# Historical failed verifier

Source 333af26. All 164 live security cases passed, but overall verifier failed: first budget allowed probe received429 because prior asynchronous spend was not settled before setting its tiny cap. Raw results are unchanged. Superseded by the source-frozen replay after101094a.

The original envelope retains its original artifact paths and hashes. For historical inspection, resolve `baseline-single-choice/` to `baseline-before-budget-fix/` and `final/` to `final-before-budget-fix/`. Current folders with the original names contain the later source101094a replay. No raw report hashes were rewritten when archiving.

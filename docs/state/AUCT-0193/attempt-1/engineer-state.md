# Engineer State: AUCT-0193

**Ticket:** AUCT-0193 - Implement Next Steps Synthesizer agent prompt
**Attempt:** 1
**Timestamp:** 2026-01-19T18:30:00Z
**Status:** VALIDATION_PASSED
**Branch:** feature/AUCT-0193-implementation

## Validation Result

| Check | Result |
|-------|--------|
| Typecheck | skip |
| Lint | skip |
| Test | skip |
| Build | skip |
| **Overall** | **pass** |

## Work Completed

- Enhanced Next Steps Synthesizer Agent prompt with comprehensive "How to Analyze" section
- Added Step 1: Read All Documents - instructions to read all 7 analysis documents
- Added Step 2: Cross-Reference Analysis - table showing how to cross-reference findings
- Added Step 3: Priority Classification Criteria - concrete P1/P2/P3 indicators
- Added Step 4: Quick Wins Identification - framework for low-effort improvements
- Added Step 5: SDLC Gap Analysis - table mapping SDLC requirements to gap indicators

## Files Modified

- `.claude/commands/analyze-codebase.md`

## Tests Written

None (prompt engineering - no code to test)

## Known Issues

None

## Next Steps

- Ready for PR creation
- Manual validation on diverse codebases recommended (AUCT-0196)

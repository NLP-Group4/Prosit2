# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Thread Title Display on Reload
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the ReferenceError when accessing undefined `threads` variable
  - **Scoped PBT Approach**: Scope the property to concrete failing cases: activeThread and activeProject are both set to valid IDs
  - Test that the topbar displays the thread title when activeThread and activeProject are set (from Fault Condition in design)
  - The test assertions should verify: no ReferenceError is thrown AND the correct thread title is displayed
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with "ReferenceError: threads is not defined" (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause (e.g., "Mounting ChatPage with activeThread='thread-123' and activeProject='project-1' throws ReferenceError at line 853")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - New Thread Display
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (when activeThread is null)
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - When activeThread is null, topbar displays "New thread"
    - When thread has no title property, topbar displays "New thread"
    - When project or thread is not found, topbar displays "New thread"
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for undefined threads variable in topbar

  - [x] 3.1 Implement the fix in ChatPage.jsx
    - Locate line 853 where the topbar displays the thread title
    - Replace `threads.find(t => t.id === activeThread)` with correct state traversal
    - Use `projects.find(p => p.id === activeProject)?.threads.find(t => t.id === activeThread)` to access the thread
    - Add null safety checks for activeProject and activeThread
    - Preserve the existing "New thread" fallback behavior
    - _Bug_Condition: isBugCondition(input) where input.activeThread !== null AND input.projects.length > 0 AND topbar attempts to render thread title_
    - _Expected_Behavior: Topbar displays thread title without ReferenceError when activeThread and activeProject are set_
    - _Preservation: When activeThread is null OR project/thread not found, display "New thread" (Requirements 3.1, 3.2, 3.3, 3.4)_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Thread Title Display on Reload
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - no ReferenceError and correct title displayed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - New Thread Display
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions in "New thread" display behavior)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Timeout and No Progress Feedback
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Test concrete failing cases - (1) 35-second database initialization timing out at 30 seconds, (2) no progress events emitted during deployment
  - Test implementation details from Fault Condition in design:
    - Deploy backend with PostgreSQL configured to delay initialization by 35 seconds
    - Assert deployment fails with timeout error at ~30 seconds (confirms insufficient timeout)
    - Deploy backend and monitor IPC events
    - Assert zero 'deployment-progress' events are emitted during build/startup/health check phases (confirms no progress reporting)
  - The test assertions should match the Expected Behavior Properties from design:
    - After fix: deployment should succeed within 120-second window
    - After fix: progress events should include 'building', 'starting', 'health_checking', 'verifying' phases
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause:
    - Exact timeout duration observed
    - Number of health check attempts before timeout
    - Absence of progress events in console/IPC logs
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Fast Deployment and Error Handling
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Deploy backend that becomes healthy in 5 seconds - record exact timing
    - Trigger port conflict error (start two projects on same port) - record error message
    - Test Docker not installed scenario - record guidance messages
    - Deploy backend successfully and run verification - record test execution flow
    - Stop project after deployment - record cleanup behavior
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements:
    - Fast deployments (< 30s) complete without unnecessary delays
    - Port conflict errors produce specific error messages
    - Docker detection produces specific guidance messages
    - Verification test execution produces expected results
    - Project cleanup stops containers correctly
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Implement Docker health check timeout and progress reporting fix

  - [x] 3.1 Add progress callback support to DockerManager class
    - Add `progressCallback` property to constructor (initialize to null)
    - Add `setProgressCallback(callback)` method to allow registration
    - Add `_reportProgress(phase, message, details)` internal helper method
    - Helper should safely invoke callback only if it exists
    - _Bug_Condition: isBugCondition(input) where input.progressCallbackExists == false_
    - _Expected_Behavior: Progress callback invoked at all deployment phases_
    - _Preservation: Existing deployments without callback should work unchanged_
    - _Requirements: 2.2, 2.3_

  - [x] 3.2 Increase health check timeout and adjust interval in waitForHealth
    - Change `maxAttempts` parameter default from 30 to 60
    - Change `intervalMs` parameter default from 1000 to 2000
    - Total timeout: 60 attempts × 2 seconds = 120 seconds
    - _Bug_Condition: isBugCondition(input) where input.databaseInitTime > 30 AND input.healthCheckTimeout == 30_
    - _Expected_Behavior: Health checks wait up to 120 seconds with 2-second intervals_
    - _Preservation: Fast deployments (< 30s) complete without delays_
    - _Requirements: 2.1, 3.1_

  - [x] 3.3 Add progress reporting to waitForHealth function
    - Calculate elapsed time from start
    - Invoke `_reportProgress` with phase 'health_checking' before each attempt
    - Include attempt number, maxAttempts, elapsed time, and URL in details
    - Format: `{ phase: 'health_checking', message: 'Health check attempt X/Y', attempt, maxAttempts, elapsed, url }`
    - _Bug_Condition: isBugCondition(input) where input.deploymentPhase == 'health_checking' AND input.progressCallbackExists == false_
    - _Expected_Behavior: Progress updates sent during health check polling_
    - _Preservation: Health check logic and error handling unchanged_
    - _Requirements: 2.3, 2.4_

  - [x] 3.4 Add progress reporting to deployProject function
    - Invoke `_reportProgress('building', 'Building Docker images...', { projectId })` before spawning docker compose
    - Forward Docker Compose stdout/stderr as progress updates during build phase
    - Invoke `_reportProgress('starting', 'Containers started, waiting for health checks...', { projectId })` after containers start
    - Invoke `_reportProgress('healthy', 'All services are healthy', { projectId })` after health checks succeed
    - Invoke `_reportProgress('error', errorMessage, { projectId })` on failures
    - _Bug_Condition: isBugCondition(input) where input.deploymentPhase IN ['building', 'starting'] AND input.progressCallbackExists == false_
    - _Expected_Behavior: Progress updates sent during build and startup phases_
    - _Preservation: Docker Compose execution and error handling unchanged_
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Extended Timeout and Progress Reporting
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify 35-second database initialization now succeeds
    - Verify progress events are emitted during all deployment phases
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 2.4_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Fast Deployment and Error Handling
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm fast deployments still complete quickly
    - Confirm error messages unchanged
    - Confirm Docker detection unchanged
    - Confirm verification flow unchanged
    - Confirm cleanup behavior unchanged

- [x] 4. Implement IPC progress forwarding in main.cjs

  - [x] 4.1 Set up progress callback on DockerManager
    - Before calling `deployProject`, register progress callback using `dockerManager.setProgressCallback`
    - Callback should forward progress events to renderer via `event.sender.send('deployment-progress', progressData)`
    - Add console logging for debugging: `console.log('[IPC] Docker progress:', progressData)`
    - _Bug_Condition: isBugCondition(input) where renderer receives no progress updates_
    - _Expected_Behavior: All docker-manager progress events forwarded to renderer_
    - _Preservation: Existing IPC handlers and error handling unchanged_
    - _Requirements: 2.4_

  - [x] 4.2 Send deployment phase progress events
    - Send 'deploying' phase event before calling `deployProject`
    - Include attempt number and maxAttempts in event data
    - Send 'verifying' phase event before calling `verifyRunner.runFullSuite`
    - Send 'complete' phase event after successful verification
    - Send 'error' phase event on any failures
    - Format: `{ phase, message, details }`
    - _Bug_Condition: isBugCondition(input) where UI receives no status updates_
    - _Expected_Behavior: Renderer receives phase transitions throughout workflow_
    - _Preservation: Existing workflow logic and error handling unchanged_
    - _Requirements: 2.4_

  - [x] 4.3 Add error progress events
    - Wrap `deployProject` call in try-catch
    - On error, send 'error' phase event with error message
    - Include attempt number in error event
    - Ensure error is still thrown after sending event
    - _Bug_Condition: isBugCondition(input) where errors occur without progress notification_
    - _Expected_Behavior: Errors reported via progress events before throwing_
    - _Preservation: Error handling and rejection behavior unchanged_
    - _Requirements: 2.4, 3.3_

- [x] 5. Implement progress reporting in verify-runner.cjs

  - [x] 5.1 Add progress callback parameter to runFullSuite
    - Modify signature: `runFullSuite(spec, onProgress = null)`
    - Add internal helper: `reportProgress(test, current, total, passed = null)`
    - Helper should safely invoke callback only if it exists
    - _Bug_Condition: isBugCondition(input) where test execution has no progress updates_
    - _Expected_Behavior: Test progress reported to caller_
    - _Preservation: Test execution logic and results unchanged_
    - _Requirements: 2.4_

  - [x] 5.2 Report individual test progress
    - Calculate total test count before execution
    - Before each test, invoke `reportProgress` with phase 'verifying'
    - Include test name, current index, and total count
    - After each test, invoke `reportProgress` with phase 'test_complete'
    - Include test name and pass/fail result
    - Format: `{ phase: 'verifying'|'test_complete', test, current, total, passed }`
    - _Bug_Condition: isBugCondition(input) where individual tests run silently_
    - _Expected_Behavior: Each test execution reported with progress_
    - _Preservation: Test results and timing unchanged_
    - _Requirements: 2.4_

  - [x] 5.3 Pass progress callback from main.cjs to verifyRunner
    - In `generate-and-verify` handler, pass progress callback to `runFullSuite`
    - Callback should forward test progress to renderer via `event.sender.send('deployment-progress', testProgress)`
    - Verify progress events flow from verify-runner through main.cjs to renderer
    - _Bug_Condition: isBugCondition(input) where test progress doesn't reach UI_
    - _Expected_Behavior: Test progress forwarded through IPC to renderer_
    - _Preservation: Test execution and results reporting unchanged_
    - _Requirements: 2.4_

- [ ] 6. Checkpoint - Ensure all tests pass
  - Run bug condition exploration test - verify it now PASSES
  - Run preservation property tests - verify they still PASS
  - Run unit tests for progress callback mechanism
  - Run integration tests for full deployment flow with progress reporting
  - Test fast deployment scenario (< 30s) - verify no delays introduced
  - Test slow deployment scenario (35s) - verify success with progress updates
  - Test error scenario (port conflict) - verify error reporting unchanged
  - Manually test UI - verify progress updates display correctly
  - Ask user if any questions or issues arise

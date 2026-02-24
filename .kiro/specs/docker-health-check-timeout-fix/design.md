# Docker Health Check Timeout Fix - Bugfix Design

## Overview

This bugfix addresses the premature timeout and lack of progress feedback during Docker container deployment in the Electron desktop app. The current implementation uses a 30-second timeout with 1-second intervals, which is insufficient for database initialization (20-30 seconds). Additionally, users receive no feedback during the build, startup, and health check phases, causing the UI to appear frozen.

The fix introduces a progress callback mechanism throughout the Docker deployment lifecycle, increases the health check timeout to 120 seconds, adjusts the health check interval to 2 seconds, and forwards progress events to the renderer process via IPC. This ensures users receive real-time feedback and containers have adequate time to initialize.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when Docker containers require more than 30 seconds to become healthy OR when users receive no progress updates during deployment
- **Property (P)**: The desired behavior - containers should have 120 seconds to become healthy AND users should receive progress updates throughout the deployment lifecycle
- **Preservation**: Existing Docker deployment behavior, verification testing, and error handling that must remain unchanged by the fix
- **deployProject**: The function in `docker-manager.cjs` that spawns Docker Compose and waits for health checks
- **waitForHealth**: The function in `docker-manager.cjs` that polls the health endpoint with timeout and interval configuration
- **generate-and-verify**: The IPC handler in `main.cjs` that orchestrates the generation, deployment, and verification workflow
- **Progress Callback**: A callback function passed to docker-manager that receives progress updates (phase, message, details) during deployment
- **Health Check Phase**: The period after containers start when the system polls the /health endpoint to verify service readiness

## Bug Details

### Fault Condition

The bug manifests when Docker containers are deployed and either (1) the database initialization takes longer than 30 seconds, causing a premature timeout, or (2) users receive no feedback during the build/startup/health check phases, causing the UI to appear frozen.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type DockerDeploymentContext
  OUTPUT: boolean
  
  RETURN (input.databaseInitTime > 30 AND input.healthCheckTimeout == 30)
         OR (input.deploymentPhase IN ['building', 'starting', 'health_checking'] 
             AND input.progressCallbackExists == false)
END FUNCTION
```

### Examples

- **Example 1**: User generates a backend with PostgreSQL. Database initialization takes 35 seconds. System times out at 30 seconds with "Service never became healthy" error, even though the service would have been ready in 5 more seconds.

- **Example 2**: User generates a backend. Docker images are being built (taking 45 seconds). UI shows "Verification suite passed" with no updates. User thinks the app is frozen and considers force-quitting.

- **Example 3**: User generates a backend. Containers start successfully but database takes 28 seconds to initialize. Health checks poll every 1 second (28 attempts). System succeeds but uses inefficient polling.

- **Edge Case**: User generates a backend. Docker Compose fails immediately (port conflict). System should report error quickly without waiting for full timeout period.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Docker detection and installation guidance must continue to work exactly as before
- Successful deployments that complete within 30 seconds must continue to work without delays
- Error handling for genuine Docker failures (port conflicts, missing files, daemon not running) must continue to report appropriate error messages
- Verification test execution after successful health checks must continue to work exactly as before
- The iterative test-and-fix loop with cloud API must continue to function correctly
- Project cleanup with `stopProject` must continue to work as before

**Scope:**
All Docker deployment scenarios that currently succeed within 30 seconds should be completely unaffected by this fix. This includes:
- Fast container startups (< 10 seconds)
- Immediate health check success
- Docker detection and guidance flows
- Error scenarios that fail before health checking begins

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Insufficient Health Check Timeout**: The `waitForHealth` function uses `maxAttempts = 30` with a 1-second interval, resulting in a 30-second total timeout. Database initialization alone can take 20-30 seconds, leaving insufficient buffer for container startup and health endpoint readiness.

2. **No Progress Reporting Mechanism**: The `deployProject` function has no callback or event mechanism to report progress. The function is entirely silent between "Deploying project" and "Containers started", which can span 30-60 seconds during image builds.

3. **Inefficient Health Check Interval**: Polling every 1 second is excessive for services that need 20-30 seconds to initialize. A 2-second interval would reduce unnecessary network requests while still providing timely detection.

4. **No IPC Progress Events**: The `generate-and-verify` handler in `main.cjs` doesn't forward any progress updates to the renderer process. The UI has no way to display deployment status.

5. **No Test Execution Progress**: The `verifyRunner.runFullSuite` function doesn't report individual test progress, causing another silent period after health checks succeed.

## Correctness Properties

Property 1: Fault Condition - Extended Timeout and Progress Reporting

_For any_ Docker deployment where containers require more than 30 seconds to become healthy (up to 120 seconds) OR where users need feedback during the deployment lifecycle, the fixed deployProject function SHALL wait up to 120 seconds for health checks with 2-second intervals AND SHALL invoke progress callbacks with phase updates (building, starting, health_checking, verifying) and detailed status messages.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Fast Deployment and Error Handling

_For any_ Docker deployment that succeeds within 30 seconds OR that fails due to genuine errors (port conflicts, missing files, daemon issues), the fixed code SHALL produce exactly the same behavior as the original code, preserving fast completion times for quick startups and appropriate error messages for genuine failures.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `frontend/desktop/electron/services/docker-manager.cjs`

**Function**: `deployProject` and `waitForHealth`

**Specific Changes**:

1. **Add Progress Callback Support to DockerManager**:
   - Add `progressCallback` property to the DockerManager class constructor
   - Add `setProgressCallback(callback)` method to allow main.cjs to register a callback
   - Modify `deployProject` to accept optional `onProgress` parameter
   - Invoke progress callback at key phases: 'building', 'starting', 'health_checking'

2. **Increase Health Check Timeout**:
   - Change `waitForHealth` default `maxAttempts` from 30 to 60
   - Change interval from 1000ms to 2000ms
   - Total timeout: 60 attempts × 2 seconds = 120 seconds

3. **Add Progress Reporting in waitForHealth**:
   - Report current attempt number and elapsed time during health checking
   - Invoke progress callback with format: `{ phase: 'health_checking', attempt: j, maxAttempts, elapsed: j*2, url }`

4. **Report Docker Compose Build Progress**:
   - Invoke progress callback when Docker Compose starts: `{ phase: 'building', message: 'Building Docker images...' }`
   - Invoke progress callback when containers start: `{ phase: 'starting', message: 'Starting containers...' }`

5. **Add Progress Reporting to Verification**:
   - Modify `verifyRunner.runFullSuite` to accept optional `onProgress` callback
   - Report individual test execution: `{ phase: 'verifying', test: testName, current: i, total: totalTests }`

**File**: `frontend/desktop/electron/main.cjs`

**Function**: `generate-and-verify` IPC handler

**Specific Changes**:

1. **Set Up Progress Callback on DockerManager**:
   - Before calling `deployProject`, register a progress callback using `dockerManager.setProgressCallback`
   - The callback should forward progress events to the renderer via `event.sender.send('deployment-progress', progressData)`

2. **Forward Progress Events via IPC**:
   - Add new IPC event channel: `'deployment-progress'`
   - Send progress updates with structure: `{ phase, message, details }`
   - Phases: 'building', 'starting', 'health_checking', 'verifying', 'complete', 'error'

3. **Handle Progress in Verification Loop**:
   - Pass progress callback to `verifyRunner.runFullSuite`
   - Forward test execution progress to renderer

**File**: `frontend/desktop/electron/services/verify-runner.cjs`

**Function**: `runFullSuite`

**Specific Changes**:

1. **Add Progress Callback Parameter**:
   - Modify `runFullSuite(spec, onProgress = null)` signature
   - Invoke `onProgress` before each test with: `{ phase: 'verifying', test: testName, current: i, total: totalTests }`

2. **Report Test Completion**:
   - After each test completes, invoke `onProgress` with result: `{ phase: 'test_complete', test: testName, passed: result.passed }`

### Implementation Details

#### docker-manager.cjs Changes

```javascript
class DockerManager {
    constructor() {
        this.activeProjects = new Map();
        this.dockerAvailable = null;
        this.progressCallback = null; // NEW: Store progress callback
    }

    /**
     * Sets the progress callback for deployment updates.
     * @param {Function} callback - Function(phase, message, details)
     */
    setProgressCallback(callback) {
        this.progressCallback = callback;
    }

    /**
     * Internal helper to invoke progress callback safely.
     */
    _reportProgress(phase, message, details = {}) {
        if (this.progressCallback) {
            this.progressCallback({ phase, message, ...details });
        }
    }

    async deployProject(projectId, projectPath) {
        // ... existing Docker detection code ...

        return new Promise((resolve, reject) => {
            console.log(`[DockerManager] Deploying project ${projectId} from ${projectPath}`);
            
            // ... existing compose file validation and patching ...

            // NEW: Report building phase
            this._reportProgress('building', 'Building Docker images...', { projectId });

            const dockerProcess = spawn('docker', ['compose', 'up', '--build', '-d'], {
                cwd: projectPath,
                stdio: ['ignore', 'pipe', 'pipe']
            });

            this.activeProjects.set(projectId, { path: projectPath, process: dockerProcess });

            dockerProcess.stdout.on('data', (data) => {
                console.log(`[DOCKER ${projectId}]: ${data}`);
                // NEW: Forward build output as progress
                this._reportProgress('building', data.toString().trim(), { projectId });
            });

            dockerProcess.stderr.on('data', (data) => {
                console.log(`[DOCKER ${projectId}]: ${data}`);
                this._reportProgress('building', data.toString().trim(), { projectId });
            });

            dockerProcess.on('close', async (code) => {
                if (code !== 0) {
                    this._reportProgress('error', `Docker Compose failed with exit code ${code}`, { projectId, code });
                    return reject(new Error(`Docker Compose failed with exit code ${code}`));
                }

                // NEW: Report starting phase
                this._reportProgress('starting', 'Containers started, waiting for health checks...', { projectId });
                
                console.log(`[DockerManager] Containers started for ${projectId}. Waiting for health...`);
                try {
                    await this.waitForHealth(8001);
                    this._reportProgress('healthy', 'All services are healthy', { projectId });
                    resolve(true);
                } catch (e) {
                    this._reportProgress('error', e.message, { projectId });
                    reject(e);
                }
            });
        });
    }

    /**
     * Polls the backend health endpoint with extended timeout and progress reporting.
     * @param {number} port - Port to check
     * @param {number} maxAttempts - Maximum number of attempts (default: 60)
     * @param {number} intervalMs - Interval between attempts in milliseconds (default: 2000)
     */
    async waitForHealth(port, maxAttempts = 60, intervalMs = 2000) {
        const url = `http://localhost:${port}/health`;
        const startTime = Date.now();
        
        for (let j = 0; j < maxAttempts; j++) {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            
            // NEW: Report health check progress
            this._reportProgress('health_checking', `Health check attempt ${j + 1}/${maxAttempts}`, {
                attempt: j + 1,
                maxAttempts,
                elapsed,
                url
            });
            
            try {
                const res = await fetch(url);
                if (res.ok) {
                    console.log(`[DockerManager] Health check succeeded after ${j + 1} attempts (${elapsed}s)`);
                    return true;
                }
            } catch (e) {
                // Connection refused means container isn't ready
            }
            await new Promise(r => setTimeout(r, intervalMs));
        }
        
        const totalTime = Math.floor((Date.now() - startTime) / 1000);
        throw new Error(`Service at ${url} never became healthy after ${maxAttempts} attempts (${totalTime}s).`);
    }

    // ... rest of the class remains unchanged ...
}
```

#### main.cjs Changes

```javascript
ipcMain.handle('generate-and-verify', async (event, args) => {
    const { prompt, model, token, apiUrl } = args;
    console.log('[IPC] Received generate-and-verify request for', model);

    // NEW: Set up progress callback to forward to renderer
    dockerManager.setProgressCallback((progressData) => {
        console.log('[IPC] Docker progress:', progressData);
        event.sender.send('deployment-progress', progressData);
    });

    try {
        // ... existing generation and download code ...

        while (!currentPassedTests && attempts <= MAX_ATTEMPTS) {
            console.log(`[IPC] Starting Docker local evaluation layer in ${currentProjectDir} (Attempt ${attempts})...`);
            
            // NEW: Send initial progress event
            event.sender.send('deployment-progress', {
                phase: 'deploying',
                message: `Deploying project (Attempt ${attempts}/${MAX_ATTEMPTS})...`,
                attempt: attempts,
                maxAttempts: MAX_ATTEMPTS
            });
            
            try {
                await dockerManager.deployProject(project_id, currentProjectDir);
            } catch (err) {
                console.error(`[IPC] Docker deploy failed on attempt ${attempts}:`, err.message);
                event.sender.send('deployment-progress', {
                    phase: 'error',
                    message: err.message,
                    attempt: attempts
                });
                throw err;
            }

            // NEW: Send verification phase event
            event.sender.send('deployment-progress', {
                phase: 'verifying',
                message: 'Running endpoint verification tests...'
            });

            console.log('[IPC] Running endpoint verification simulations...');
            
            // NEW: Pass progress callback to verifyRunner
            const testReport = await verifyRunner.runFullSuite(spec, (testProgress) => {
                event.sender.send('deployment-progress', testProgress);
            });
            
            console.log(`[IPC] Test suite passed: ${testReport.passed}`);
            currentPassedTests = testReport.passed;

            // ... rest of the loop remains unchanged ...
        }

        // NEW: Send completion event
        event.sender.send('deployment-progress', {
            phase: 'complete',
            message: 'Deployment and verification complete',
            success: currentPassedTests
        });

        return {
            success: true,
            project_id,
            project_name,
            download_url: currentDownloadUrl
        };

    } catch (error) {
        console.error('[IPC] Error in generation lifecycle:', error.response?.data || error.message);
        
        // NEW: Send error event
        event.sender.send('deployment-progress', {
            phase: 'error',
            message: error.response?.data?.detail || error.message
        });
        
        return {
            success: false,
            error: error.response?.data?.detail || error.message
        };
    }
});
```

#### verify-runner.cjs Changes

```javascript
class VerifyRunner {
    constructor(baseUrl = 'http://localhost:8001') {
        this.baseUrl = baseUrl;
    }

    // ... existing testEndpoint method remains unchanged ...

    /**
     * Runs the full verification suite with optional progress reporting.
     * @param {Object} spec - The project specification
     * @param {Function} onProgress - Optional callback for progress updates
     */
    async runFullSuite(spec, onProgress = null) {
        const start = Date.now();
        const results = [];

        // Helper to report progress
        const reportProgress = (test, current, total, passed = null) => {
            if (onProgress) {
                onProgress({
                    phase: passed === null ? 'verifying' : 'test_complete',
                    test,
                    current,
                    total,
                    passed
                });
            }
        };

        // Calculate total tests
        let totalTests = 1; // health check
        if (spec.auth?.enabled) totalTests += 2; // register + login
        if (spec.entities) {
            for (const entity of spec.entities) {
                if (spec.auth?.enabled && entity.name.toLowerCase() === 'user') continue;
                totalTests += 2; // POST + GET per entity
            }
        }

        let currentTest = 0;

        // 1. Health checks
        currentTest++;
        reportProgress('GET /health', currentTest, totalTests);
        const healthResult = await this.testEndpoint('GET', '/health', 200);
        results.push(healthResult);
        reportProgress('GET /health', currentTest, totalTests, healthResult.passed);

        // 2. Auth tests (if applicable in the spec)
        if (spec.auth && spec.auth.enabled) {
            const userPayload = { email: 'test@example.com', password: 'password123' };
            
            currentTest++;
            reportProgress('POST /auth/register', currentTest, totalTests);
            const registerResult = await this.testEndpoint('POST', '/auth/register', 201, userPayload);
            results.push(registerResult);
            reportProgress('POST /auth/register', currentTest, totalTests, registerResult.passed);
            
            currentTest++;
            reportProgress('POST /auth/login', currentTest, totalTests);
            const loginResult = await this.testEndpoint('POST', '/auth/login', 200, userPayload);
            results.push(loginResult);
            reportProgress('POST /auth/login', currentTest, totalTests, loginResult.passed);
        }

        // 3. Entity CRUD simulation
        if (spec.entities) {
            for (const entity of spec.entities) {
                if (spec.auth?.enabled && entity.name.toLowerCase() === 'user') continue;

                const routeName = `${entity.name.toLowerCase()}s`;
                const payload = {};
                for (const field of entity.fields || []) {
                    if (field.name !== 'id') payload[field.name] = "test-string";
                }

                currentTest++;
                const postTest = `POST /api/${routeName}`;
                reportProgress(postTest, currentTest, totalTests);
                const postResult = await this.testEndpoint('POST', `/api/${routeName}`, 201, payload);
                results.push(postResult);
                reportProgress(postTest, currentTest, totalTests, postResult.passed);

                currentTest++;
                const getTest = `GET /api/${routeName}`;
                reportProgress(getTest, currentTest, totalTests);
                const getResult = await this.testEndpoint('GET', `/api/${routeName}`, 200);
                results.push(getResult);
                reportProgress(getTest, currentTest, totalTests, getResult.passed);
            }
        }

        const passed = results.every(r => r.passed);
        return {
            passed,
            elapsed_ms: Date.now() - start,
            results
        };
    }
}

module.exports = new VerifyRunner();
```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (timeout and no progress), then verify the fix works correctly (extended timeout and progress reporting) and preserves existing behavior (fast deployments and error handling).

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Create test scenarios that simulate slow database initialization and observe the unfixed code timing out at 30 seconds. Monitor console logs to confirm no progress updates are emitted. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Slow Database Initialization Test**: Deploy a backend with PostgreSQL configured to delay initialization by 35 seconds (will fail on unfixed code with timeout error)
2. **No Progress Updates Test**: Deploy a backend and monitor IPC events - confirm no 'deployment-progress' events are emitted during build/startup/health check phases (will fail on unfixed code)
3. **Inefficient Polling Test**: Deploy a backend and count health check attempts - confirm 30 attempts with 1-second intervals (will show inefficiency on unfixed code)
4. **UI Freeze Perception Test**: Deploy a backend and observe UI - confirm no status updates between "Verification suite passed" and final result (will demonstrate poor UX on unfixed code)

**Expected Counterexamples**:
- Deployments timing out at exactly 30 seconds when database needs 35 seconds
- Zero progress events emitted to renderer process during deployment
- Health checks polling every 1 second (30 times total)
- UI appearing frozen with no feedback for 30-60 seconds

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (slow initialization or need for progress feedback), the fixed function produces the expected behavior (120-second timeout and progress reporting).

**Pseudocode:**
```
FOR ALL deployment WHERE isBugCondition(deployment) DO
  result := deployProject_fixed(deployment)
  ASSERT result.timeout == 120
  ASSERT result.interval == 2
  ASSERT result.progressEvents.length > 0
  ASSERT 'building' IN result.progressEvents.phases
  ASSERT 'starting' IN result.progressEvents.phases
  ASSERT 'health_checking' IN result.progressEvents.phases
END FOR
```

**Test Cases**:
1. **Extended Timeout Test**: Deploy backend with 35-second database initialization - verify deployment succeeds within 120-second window
2. **Progress Events Test**: Deploy backend and capture all IPC events - verify 'building', 'starting', 'health_checking', 'verifying' phases are reported
3. **Health Check Interval Test**: Deploy backend and measure time between health check attempts - verify 2-second intervals
4. **Attempt Reporting Test**: Deploy backend and verify health check progress includes attempt numbers (1/60, 2/60, etc.)

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (fast deployments, error scenarios), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL deployment WHERE NOT isBugCondition(deployment) DO
  ASSERT deployProject_original(deployment).behavior == deployProject_fixed(deployment).behavior
  ASSERT deployProject_original(deployment).timing ≈ deployProject_fixed(deployment).timing
  ASSERT deployProject_original(deployment).errors == deployProject_fixed(deployment).errors
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the deployment input domain
- It catches edge cases that manual unit tests might miss (various error conditions, timing variations)
- It provides strong guarantees that behavior is unchanged for all non-buggy deployments

**Test Plan**: Observe behavior on UNFIXED code first for fast deployments and error scenarios, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Fast Deployment Preservation**: Deploy backend that becomes healthy in 5 seconds - observe timing on unfixed code, verify fixed code completes in similar time (no unnecessary delays)
2. **Error Handling Preservation**: Trigger port conflict error - observe error message on unfixed code, verify fixed code produces identical error message
3. **Docker Detection Preservation**: Test Docker not installed scenario - verify guidance messages remain unchanged
4. **Verification Flow Preservation**: Deploy backend successfully - verify test execution and results reporting work exactly as before
5. **Cleanup Preservation**: Stop project after deployment - verify `stopProject` behavior unchanged

### Unit Tests

- Test `waitForHealth` with various timeout scenarios (success at attempt 1, 30, 60, timeout at 61)
- Test progress callback invocation at each phase (building, starting, health_checking)
- Test health check interval timing (verify 2-second delays between attempts)
- Test progress callback with null/undefined (should not crash)
- Test IPC event forwarding in main.cjs (verify 'deployment-progress' events sent)
- Test verify-runner progress reporting (verify test progress callbacks invoked)

### Property-Based Tests

- Generate random deployment scenarios (varying initialization times 0-120s) and verify appropriate timeout behavior
- Generate random progress callback implementations and verify they receive all expected phases
- Generate random test suites (varying entity counts) and verify progress reporting scales correctly
- Test that all fast deployments (< 30s) complete without unnecessary delays across many scenarios

### Integration Tests

- Test full generation flow with slow database (35s init) - verify success with progress updates
- Test full generation flow with fast database (5s init) - verify success without delays
- Test full generation flow with Docker error - verify appropriate error reporting
- Test UI integration - verify progress events update UI components correctly
- Test multi-attempt fix loop - verify progress reporting works across multiple deployment attempts

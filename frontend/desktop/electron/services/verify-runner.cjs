/*
 * verify-runner.js
 * 
 * Replaces the server-side deploy_verify.py agent.
 * Sends HTTP requests to the locally deployed Docker container 
 * to smoke test auth and CRUD requirements directly.
 */

class VerifyRunner {
    constructor(baseUrl = 'http://localhost:8001') {
        this.baseUrl = baseUrl;
    }

    async testEndpoint(method, endpoint, expectedStatus = 200, payload = null) {
        const start = Date.now();
        console.log(`[Verify] Testing ${method} ${endpoint}...`);
        try {
            const res = await fetch(`${this.baseUrl}${endpoint}`, {
                method,
                headers: payload ? { 'Content-Type': 'application/json' } : {},
                body: payload ? JSON.stringify(payload) : undefined
            });

            const elapsed = Date.now() - start;
            if (res.status !== expectedStatus) {
                return {
                    test_name: `${method} ${endpoint}`,
                    endpoint,
                    method,
                    passed: false,
                    status_code: res.status,
                    error_message: `Expected ${expectedStatus} but got ${res.status}`,
                    elapsed
                };
            }

            return {
                test_name: `${method} ${endpoint}`,
                endpoint,
                method,
                passed: true,
                status_code: res.status,
                elapsed
            };
        } catch (e) {
            return {
                test_name: `${method} ${endpoint}`,
                endpoint,
                method,
                passed: false,
                status_code: null,
                error_message: `Connection failed: ${e.message}`,
                elapsed: Date.now() - start
            };
        }
    }

    async testEndpointForm(method, endpoint, expectedStatus = 200, formData = null) {
        const start = Date.now();
        console.log(`[Verify] Testing ${method} ${endpoint} (form)...`);
        try {
            const body = formData ? new URLSearchParams(formData).toString() : undefined;
            const res = await fetch(`${this.baseUrl}${endpoint}`, {
                method,
                headers: body ? { 'Content-Type': 'application/x-www-form-urlencoded' } : {},
                body
            });

            const elapsed = Date.now() - start;
            if (res.status !== expectedStatus) {
                return {
                    test_name: `${method} ${endpoint}`,
                    endpoint,
                    method,
                    passed: false,
                    status_code: res.status,
                    error_message: `Expected ${expectedStatus} but got ${res.status}`,
                    elapsed
                };
            }

            return {
                test_name: `${method} ${endpoint}`,
                endpoint,
                method,
                passed: true,
                status_code: res.status,
                elapsed
            };
        } catch (e) {
            return {
                test_name: `${method} ${endpoint}`,
                endpoint,
                method,
                passed: false,
                status_code: null,
                error_message: `Connection failed: ${e.message}`,
                elapsed: Date.now() - start
            };
        }
    }

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
            const loginResult = await this.testEndpointForm('POST', '/auth/login', 200, { username: userPayload.email, password: userPayload.password });
            results.push(loginResult);
            reportProgress('POST /auth/login', currentTest, totalTests, loginResult.passed);
        }

        // 3. Entity CRUD simulation
        if (spec.entities) {
            for (const entity of spec.entities) {
                // Ignore User entity if auth is specialized
                if (spec.auth?.enabled && entity.name.toLowerCase() === 'user') continue;

                const tableName = entity.table_name || `${entity.name.toLowerCase()}s`;
                // Generate simple payload mapped from fields
                const payload = {};
                for (const field of entity.fields || []) {
                    if (field.name !== 'id') payload[field.name] = "test-string"; // overly simplistic mock
                }

                currentTest++;
                const postTest = `POST /${tableName}/`;
                reportProgress(postTest, currentTest, totalTests);
                const postResult = await this.testEndpoint('POST', `/${tableName}/`, 201, payload);
                results.push(postResult);
                reportProgress(postTest, currentTest, totalTests, postResult.passed);

                currentTest++;
                const getTest = `GET /${tableName}/`;
                reportProgress(getTest, currentTest, totalTests);
                const getResult = await this.testEndpoint('GET', `/${tableName}/`, 200);
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

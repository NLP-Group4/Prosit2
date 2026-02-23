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

    async runFullSuite(spec) {
        const start = Date.now();
        const results = [];

        // 1. Health checks
        results.push(await this.testEndpoint('GET', '/health', 200));

        // 2. Auth tests (if applicable in the spec)
        if (spec.auth && spec.auth.enabled) {
            const userPayload = { email: 'test@example.com', password: 'password123' };
            results.push(await this.testEndpoint('POST', '/auth/register', 201, userPayload));
            results.push(await this.testEndpoint('POST', '/auth/login', 200, userPayload));
        }

        // 3. Entity CRUD simulation
        if (spec.entities) {
            for (const entity of spec.entities) {
                // Ignore User entity if auth is specialized
                if (spec.auth?.enabled && entity.name.toLowerCase() === 'user') continue;

                const routeName = `${entity.name.toLowerCase()}s`;
                // Generate simple payload mapped from fields
                const payload = {};
                for (const field of entity.fields || []) {
                    if (field.name !== 'id') payload[field.name] = "test-string"; // overly simplistic mock
                }

                results.push(await this.testEndpoint('POST', `/api/${routeName}`, 201, payload));
                results.push(await this.testEndpoint('GET', `/api/${routeName}`, 200));
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

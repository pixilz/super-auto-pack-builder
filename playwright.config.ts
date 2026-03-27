import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
    testDir: "tests/e2e/",
    testMatch: '**/*.spec.ts',
    use: {
        baseURL: "http://localhost:3000"
    },
    timeout: 10000,
    retries: 3,
    maxFailures: 1,
    projects: [{
        name: 'chromium',
        use: {
            ...devices['Desktop Chrome']
        }
    }]
})
#!/usr/bin/env node
/**
 * Quick E2E browser test - login and verify UI
 * Run: node test-browser-e2e.mjs
 * Requires: npx playwright install chromium (first run)
 */
import { chromium } from 'playwright';

const BASE = 'http://localhost:5173';
const EMAIL = 'testuser@mail.com';
const PASSWORD = 'haxqy6-byqcyn-waCcun';

async function main() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    console.log('1. Navigate to app...');
    await page.goto(BASE, { waitUntil: 'networkidle' });

    console.log('2. Check for login modal...');
    const loginModal = page.locator('.login-modal, .login-overlay');
    const hasLogin = await loginModal.count() > 0;
    console.log('   Login modal visible:', hasLogin);

    if (hasLogin) {
      console.log('3. Filling credentials...');
      await page.fill('input[type="email"], input[placeholder*="example"]', EMAIL);
      await page.fill('input[type="password"]', PASSWORD);
      await page.click('button[type="submit"]');
      await page.waitForTimeout(2000);
    }

    console.log('4. Check for chat interface...');
    const chatPage = page.locator('.chat-page, .cp-main');
    const hasChat = await chatPage.count() > 0;
    console.log('   Chat page visible:', hasChat);

    console.log('5. Check for projects section...');
    const projectsSection = page.locator('.cp-section-threads, [class*="project"]');
    const hasProjects = await projectsSection.count() > 0;
    console.log('   Projects section visible:', hasProjects);

    console.log('6. Check for input/textarea...');
    const input = page.locator('textarea, input[placeholder*="Interius"]');
    const hasInput = await input.count() > 0;
    console.log('   Input visible:', hasInput);

    console.log('7. Wait for projects to load from API...');
    await page.waitForTimeout(2000);
    const projectItems = page.locator('.cp-project-group, .cp-project-header, .cp-thread-item');
    const projectCount = await projectItems.count();
    console.log('   Project/thread items found:', projectCount);

    if (projectCount > 0) {
      console.log('8. Click first project to expand...');
      const firstProject = page.locator('.cp-project-header').first();
      await firstProject.click();
      await page.waitForTimeout(1000);
      const threads = page.locator('.cp-thread-child, .cp-thread-indent .cp-thread-item');
      const threadCount = await threads.count();
      console.log('   Threads visible after expand:', threadCount);

      if (threadCount > 0) {
        console.log('9. Click first thread...');
        await threads.first().click();
        await page.waitForTimeout(1500);
        const hasContent = await page.locator('.cp-agent-body, .cp-final-output, .cp-msg').count() > 0;
        console.log('   Thread content loaded:', hasContent);
      }
    }

    const allOk = hasChat && hasProjects && hasInput;
    console.log('\n--- Result:', allOk ? 'PASS' : 'FAIL ---');
    if (!allOk) {
      await page.screenshot({ path: 'test-e2e-screenshot.png' });
      console.log('Screenshot saved to test-e2e-screenshot.png');
    }
    process.exit(allOk ? 0 : 1);
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  } finally {
    await browser?.close();
  }
}

main();

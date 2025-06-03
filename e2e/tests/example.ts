import { chromium, Browser, Page } from 'playwright';
import { generateSite } from '../lib/generator';
import { UserFactory } from '../lib/models';

/**
 * Example of using the page object framework
 */
async function main() {
  console.log('Starting example...');

  // Generate a new site
  console.log('Generating site...');
  generateSite({
    siteName: 'Example',
    baseUrl: 'https://example.com',
    outputDir: './lib',
  });
  console.log('Site generated successfully!');

  // Import the generated site
  const { ExampleSite } = require('../lib/sites/example-site');

  // Create a browser instance
  console.log('Launching browser...');
  const browser: Browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page: Page = await context.newPage();

  try {
    // Create a new instance of the site
    console.log('Creating site instance...');
    const exampleSite = new ExampleSite(page);

    // Navigate to the site
    console.log('Navigating to site...');
    await exampleSite.goto();
    
    // Wait for the landing page to load
    await exampleSite.landing_page.waitForContainer();
    
    // Get the page title
    const title = await exampleSite.landing_page.title();
    console.log(`Page title: ${title}`);

    // Use a page flow
    console.log('Executing page flow...');
    await exampleSite.landing_page.executePageFlow('fillSearchForm', 'playwright');

    // Use a site flow
    console.log('Executing site flow...');
    const userFactory = new UserFactory();
    const user = userFactory.createValid();
    console.log(`Generated user: ${user.username} (${user.email})`);
    
    const userId = await exampleSite.executeSiteFlow('registerUser', user.username, 'password123');
    console.log(`Registered user ID: ${userId}`);

    // Access a page through the pages map
    const landingPage = exampleSite.getPage('landing_page');
    console.log('Accessed landing page through pages map');

    // Demonstrate model validation
    const invalidUser = userFactory.createInvalid();
    console.log(`Invalid user: ${invalidUser.username} (${invalidUser.email})`);
    console.log(`Is valid: ${invalidUser.validate()}`);

    // Create multiple users with the factory
    const users = userFactory.createMany(3);
    console.log('Generated users:');
    users.forEach(user => {
      console.log(`- ${user.username} (${user.email})`);
    });

  } catch (error) {
    console.error('Error in example:', error);
  } finally {
    // Close the browser
    console.log('Closing browser...');
    await browser.close();
  }

  console.log('Example completed!');
}

// Run the example if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}
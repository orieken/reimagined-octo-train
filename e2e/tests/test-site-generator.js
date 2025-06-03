// Test script to verify the site generator works correctly
console.log('Testing site generator...');
console.log('Command to run: npm run site:generate --name TestSite');
console.log('This should generate a new site called TestSite in the lib directory.');
console.log('After running, check for the following files:');
console.log('- lib/sites/testsite-site.ts');
console.log('- lib/pages/testsite/landing-page.ts');
console.log('- Updated exports in lib/sites/index.ts and lib/pages/index.ts');
console.log('\nTo run this test:');
console.log('1. Run: npm run site:generate --name TestSite');
console.log('2. Verify the files were created correctly');
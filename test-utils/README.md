# Cucumber Report Enhancer

A TypeScript utility that enhances Cucumber test reports by adding metadata and standardizing the output format.

## Features

- Adds project metadata to Cucumber reports
- Generates comprehensive test summary statistics
- Extracts failure screenshots from Cucumber embeddings
- Supports multiple output formats (JSON, Pretty Text, Minimal)
- Automatically finds the latest report in a directory
- Configurable via command line arguments, environment variables, or config file

## Installation

```bash
npm install --save-dev cucumber-report-enhancer
```

Or clone this repository:

```bash
git clone https://github.com/yourusername/cucumber-report-enhancer.git
cd cucumber-report-enhancer
npm install
```

## Usage

### Finding the Latest Report

The script can automatically find the most recent Cucumber report in a directory:

```bash
# Find the latest report in ./reports directory
node dist/cucumber-enhancer.js --latest ./reports enhanced-report.json

# Or use the NPM script
npm run enhance
```

### Output Formats

The enhancer supports multiple output formats:

```bash
# JSON format (default)
node dist/cucumber-enhancer.js --latest ./reports enhanced-report.json

# Pretty text format
node dist/cucumber-enhancer.js --latest ./reports enhanced-report.txt --format pretty
npm run enhance:pretty

# Minimal JSON format
node dist/cucumber-enhancer.js --latest ./reports enhanced-minimal.json --format minimal
npm run enhance:minimal
```

### Extracting Failure Screenshots

The enhancer can extract failure screenshots from Cucumber embeddings:

```bash
# Extract screenshots to ./test-failures directory
node dist/cucumber-enhancer.js --latest ./reports enhanced-report.json --screenshots ./test-failures
npm run enhance:screenshots
```

### Basic Usage with Specific File

```bash
# Build the TypeScript
npm run build

# Run with direct arguments
node dist/cucumber-enhancer.js cucumber_report.json enhanced-report.json

# Or use NPM script
npm run postcucumber
```

### Using a Config File

Create a `cucumber-enhancer-config.json` file with all available options:

```json
{
  "metadata": {
    "project": "retail-platform",
    "branch": "main",
    "commit": "a389f82",
    "runner": "cucumber-junit",
    "environment": "integration"
  },
  "reportsDir": "./reports",
  "outputFile": "enhanced-cucumber-report.json",
  "includeSummary": true,
  "includeTagsSummary": true,
  "outputFormat": "json",
  "errorScreenshotDir": "./test-failures"
}
```

Then run:

```bash
node dist/cucumber-enhancer.js --config cucumber-enhancer-config.json
# Or use the NPM script
npm run enhance:config
```

### Environment Variables

You can also use environment variables to override metadata:

```bash
PROJECT_NAME=my-project BRANCH_NAME=feature/new-tests COMMIT_HASH=abc123 TEST_ENV=staging npm run postcucumber
```

## Integration with Cucumber.js

Add a postcucumber script to your package.json:

```json
{
  "scripts": {
    "test": "cucumber-js",
    "postcucumber": "ts-node cucumber-enhancer.ts --latest ./reports enhanced-report.json"
  }
}
```

This will automatically run the enhancer after your Cucumber tests complete, finding the latest report in the ./reports directory.

## Summary Statistics

The enhancer generates comprehensive test summary statistics, including:

- Total number of scenarios
- Passed, failed, and skipped counts
- Success rate (percentage of passed tests)
- Total test duration
- Flaky test count
- Tag frequency summary

## Output Example

### JSON Format (default)

```json
{
  "metadata": {
    "project": "retail-platform",
    "branch": "main",
    "commit": "a389f82",
    "timestamp": "2025-04-14T10:15:30.000Z",
    "runner": "cucumber-junit",
    "environment": "integration"
  },
  "summary": {
    "total": 25,
    "passed": 20,
    "failed": 3,
    "skipped": 2,
    "flaky": 5,
    "duration": 12500000000,
    "success_rate": 80,
    "tags_summary": {
      "@smoke": 10,
      "@regression": 8,
      "@flaky": 5
    }
  },
  "report": [
    // Original cucumber report with added IDs
  ]
}
```

### Pretty Format

The pretty format provides a human-readable text output with symbols indicating test status:

```
================================================================================
CUCUMBER TEST REPORT - retail-platform
================================================================================
Branch: main
Commit: a389f82
Time: 2025-04-14T10:15:30.000Z
Environment: integration
================================================================================

SUMMARY:
Total Scenarios: 25
Passed: 20 (80.00%)
Failed: 3
Skipped: 2
Flaky: 5
Total Duration: 12.5s

TAGS SUMMARY:
  @smoke: 10
  @regression: 8
  @flaky: 5

FEATURES:
Feature: Customer Support - Contact Form (customer_support.feature)
  ❌ Scenario: Submitting a contact form with valid details
    ✅ Given I am on the "Contact Us" page (189ms)
    ✅ When I enter my name "Alice Smith" (1.18s)
    ✅ And I enter my email "alice.smith@example.com" (2.95s)
    ❌ And I enter a subject "Order Inquiry" (1.61s)
      Error: Element not found: #product-list ...
    ⏩ And I enter a message "I have a question about my recent order." (0ms)
    ⏩ And I click the "Submit" button (0ms)
    ⏩ Then I should see a confirmation message (0ms)
```

## License

MIT

## Output Format

The enhanced report will have the following structure:

```json
{
  "metadata": {
    "project": "retail-platform",
    "branch": "main",
    "commit": "a389f82",
    "timestamp": "2025-04-11T10:15:30.000Z",
    "runner": "cucumber-junit",
    "environment": "integration"
  },
  "report": [
    {
      "id": "feature-uuid",
      "name": "Feature Name",
      "uri": "feature_file.feature",
      "line": 1,
      "keyword": "Feature",
      "elements": [
        {
          "id": "scenario-uuid",
          "name": "Scenario Name",
          "line": 3,
          "description": "",
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [],
          "steps": []
        }
      ]
    }
  ]
}
```

## License

MIT

* example config scripts
```json
{
  "name": "cucumber-test-reporter",
  "version": "1.0.0",
  "description": "Enhance Cucumber test reports with metadata",
  "main": "dist/cucumber-enhancer.js",
  "scripts": {
    "test": "cucumber-js",
    "postcucumber": "ts-node cucumber-enhancer.ts --latest ./reports enhanced-report.json",
    "enhance": "ts-node cucumber-enhancer.ts --latest ./reports enhanced-report.json",
    "enhance:config": "ts-node cucumber-enhancer.ts --config cucumber-report-builder-config.json",
    "build": "tsc",
    "start": "node dist/cucumber-enhancer.js"
  },
  "dependencies": {
    "fs-extra": "^10.1.0"
  },
  "devDependencies": {
    "@types/fs-extra": "^9.0.13",
    "@types/node": "^16.11.12",
    "ts-node": "^10.4.0",
    "typescript": "^4.5.3"
  }
}
```
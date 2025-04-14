import * as fs from 'fs';
import * as path from 'path';
import { CucumberReportEnhancer } from './cucumber-enhancer';

/**
 * Test script to verify the summary generation functionality
 */
function testSummaryGeneration(inputFile: string = './reports/cucumber_report-sample.json'): void {
  console.log(`Testing summary generation using sample data`);

  // Create a test directory
  const testDir = './test-summary';
  if (!fs.existsSync(testDir)) {
    fs.mkdirSync(testDir, { recursive: true });
  }

  // Create a sample cucumber report
  const sampleData = createSampleCucumberReport();
  const sampleFile = path.join(testDir, 'cucumber_report-sample.json');
  fs.writeFileSync(sampleFile, JSON.stringify(sampleData, null, 2), 'utf8');
  console.log(`Created sample report at ${sampleFile}`);

  // Test all output formats
  const formats: Array<'json' | 'pretty' | 'minimal'> = ['json', 'pretty', 'minimal'];

  for (const format of formats) {
    const outputFile = path.join(testDir, `enhanced-${format}.${format === 'pretty' ? 'txt' : 'json'}`);

    // Create enhancer with summary enabled
    const enhancer = new CucumberReportEnhancer(
      sampleFile,
      outputFile,
      {
        project: 'test-project',
        branch: 'test-branch',
        commit: 'abc123',
        timestamp: new Date().toISOString(),
        runner: 'test-runner',
        environment: 'test-env'
      },
      {
        includeSummary: true,
        includeTagsSummary: true,
        outputFormat: format
      }
    );

    // Process the report
    enhancer.process();

    console.log(`Generated ${format} report: ${outputFile}`);

    // For JSON format reports, verify the summary structure
    if (format !== 'pretty') {
      try {
        const outputData = JSON.parse(fs.readFileSync(outputFile, 'utf8'));
        if (outputData.summary) {
          console.log(`✅ Summary generated successfully in ${format} format`);
          console.log(`Summary: ${JSON.stringify(outputData.summary, null, 2)}`);
        } else {
          console.error(`❌ Summary not found in ${format} report`);
        }
      } catch (error) {
        console.error(`❌ Error reading output file: ${error}`);
      }
    }
  }

  console.log(`\nTest completed. Reports saved in ${testDir} directory`);
}

/**
 * Create a sample cucumber report for testing
 */
function createSampleCucumberReport(): any[] {
  return [
    {
      "id": "customer-support",
      "name": "Customer Support Features",
      "uri": "features/customer_support.feature",
      "line": 1,
      "keyword": "Feature",
      "elements": [
        {
          "id": "customer-support;submitting-contact-form",
          "name": "Submitting a contact form with valid details",
          "line": 3,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@smoke",
              "line": 2
            },
            {
              "name": "@critical",
              "line": 2
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I am on the contact page",
              "line": 4,
              "result": {
                "status": "passed",
                "duration": 150000000
              }
            },
            {
              "keyword": "When",
              "name": "I fill in the form",
              "line": 5,
              "result": {
                "status": "passed",
                "duration": 250000000
              }
            },
            {
              "keyword": "And",
              "name": "I click submit",
              "line": 6,
              "result": {
                "status": "passed",
                "duration": 100000000
              }
            },
            {
              "keyword": "Then",
              "name": "I should see a confirmation message",
              "line": 7,
              "result": {
                "status": "passed",
                "duration": 50000000
              }
            }
          ]
        },
        {
          "id": "customer-support;submitting-without-email",
          "name": "Submitting form without email",
          "line": 9,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@regression",
              "line": 8
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I am on the contact page",
              "line": 10,
              "result": {
                "status": "passed",
                "duration": 120000000
              }
            },
            {
              "keyword": "When",
              "name": "I submit without email",
              "line": 11,
              "result": {
                "status": "passed",
                "duration": 80000000
              }
            },
            {
              "keyword": "Then",
              "name": "I should see an error message",
              "line": 12,
              "result": {
                "status": "failed",
                "duration": 30000000,
                "error_message": "Expected error message not found"
              }
            }
          ]
        },
        {
          "id": "customer-support;submitting-malformed-email",
          "name": "Submitting form with malformed email",
          "line": 14,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@flaky",
              "line": 13
            },
            {
              "name": "@regression",
              "line": 13
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I am on the contact page",
              "line": 15,
              "result": {
                "status": "passed",
                "duration": 110000000
              }
            },
            {
              "keyword": "When",
              "name": "I enter malformed email",
              "line": 16,
              "result": {
                "status": "passed",
                "duration": 90000000
              }
            },
            {
              "keyword": "Then",
              "name": "I should see a validation error",
              "line": 17,
              "result": {
                "status": "skipped",
                "duration": 0
              }
            }
          ]
        }
      ]
    },
    {
      "id": "product-catalog",
      "name": "Product Catalog Features",
      "uri": "features/product_catalog.feature",
      "line": 1,
      "keyword": "Feature",
      "elements": [
        {
          "id": "product-catalog;browsing-products",
          "name": "Browsing product catalog",
          "line": 3,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@smoke",
              "line": 2
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I am on the products page",
              "line": 4,
              "result": {
                "status": "passed",
                "duration": 200000000
              }
            },
            {
              "keyword": "When",
              "name": "I browse products",
              "line": 5,
              "result": {
                "status": "passed",
                "duration": 300000000
              }
            },
            {
              "keyword": "Then",
              "name": "I should see product listings",
              "line": 6,
              "result": {
                "status": "passed",
                "duration": 150000000
              }
            }
          ]
        },
        {
          "id": "product-catalog;filtering-by-category",
          "name": "Filtering products by category",
          "line": 8,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@flaky",
              "line": 7
            },
            {
              "name": "@smoke",
              "line": 7
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I am on the products page",
              "line": 9,
              "result": {
                "status": "passed",
                "duration": 180000000
              }
            },
            {
              "keyword": "When",
              "name": "I filter by category",
              "line": 10,
              "result": {
                "status": "failed",
                "duration": 150000000,
                "error_message": "Filter dropdown not found",
                "embeddings": [
                  {
                    "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQI12P4//8/AAX+Av7czFnnAAAAAElFTkSuQmCC",
                    "mime_type": "image/png"
                  }
                ]
              }
            },
            {
              "keyword": "Then",
              "name": "I should see filtered results",
              "line": 11,
              "result": {
                "status": "skipped",
                "duration": 0
              }
            }
          ]
        }
      ]
    }
  ];
}

// Run the test if this script is executed directly
if (require.main === module) {
  testSummaryGeneration();
}

export { testSummaryGeneration };
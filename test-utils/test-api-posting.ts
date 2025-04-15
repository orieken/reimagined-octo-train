import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';
import { CucumberReportEnhancer } from './cucumber-enhancer';

/**
 * Test script to verify the API posting functionality
 * This starts a simple HTTP server to receive the posted report
 */
async function testApiPosting(port: number = 4000): Promise<void> {
  console.log(`Testing API posting functionality`);

  // Create a test directory
  const testDir = './test-api';
  if (!fs.existsSync(testDir)) {
    fs.mkdirSync(testDir, { recursive: true });
  }

  // Create a sample cucumber report
  const sampleData = createSampleCucumberReport();
  const sampleFile = path.join(testDir, 'cucumber_report-sample.json');
  fs.writeFileSync(sampleFile, JSON.stringify(sampleData, null, 2), 'utf8');
  console.log(`Created sample report at ${sampleFile}`);

  // Start a dummy HTTP server to receive the API post
  const server = await startTestServer(port);

  try {
    // Path to the enhanced report
    const outputFile = path.join(testDir, 'enhanced-report.json');

    // API endpoint URL (our test server)
    const apiEndpoint = `http://localhost:${port}/api/v1/processor/cucumber`;

    // Create enhancer with API config
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
        apiConfig: {
          endpoint: apiEndpoint,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token',
            'X-Test-Header': 'test-value'
          }
        }
      }
    );

    // Process the report and post to API
    await enhancer.process();

    console.log(`Test completed successfully!`);
  } catch (error) {
    console.error(`Test failed with error:`, error);
  } finally {
    // Shut down the test server
    server.close();
    console.log(`Test server shutdown`);
  }
}

/**
 * Start a test HTTP server to receive the posted report
 */
function startTestServer(port: number): Promise<http.Server> {
  return new Promise((resolve) => {
    // Create a simple HTTP server
    const server = http.createServer((req, res) => {
      console.log(`\nReceived ${req.method} request to ${req.url}`);
      console.log('Request Headers:');
      console.log(req.headers);

      // Only process POST requests to our API endpoint
      if (req.method === 'POST' && req.url === '/api/v1/processor/cucumber') {
        const chunks: Buffer[] = [];

        req.on('data', (chunk) => {
          chunks.push(chunk);
        });

        req.on('end', () => {
          const requestBody = Buffer.concat(chunks).toString();
          console.log(`\nReceived report data (showing first 500 chars):`);
          console.log(requestBody.substring(0, 500) + '...');

          // Save the received data to a file
          const receivedFile = path.join('./test-api', 'received-report.json');
          fs.writeFileSync(receivedFile, requestBody, 'utf8');
          console.log(`Saved received report to ${receivedFile}`);

          // Send a success response
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            status: 'success',
            message: 'Report received successfully'
          }));
        });
      } else {
        // Send a 404 for other endpoints
        res.writeHead(404);
        res.end('Not Found');
      }
    });

    // Start the server
    server.listen(port, () => {
      console.log(`Test server started on port ${port}`);
      resolve(server);
    });
  });
}

/**
 * Create a sample cucumber report for testing
 */
function createSampleCucumberReport(): any[] {
  return [
    {
      "id": "api-test-feature",
      "name": "API Test Feature",
      "uri": "features/api_test.feature",
      "line": 1,
      "keyword": "Feature",
      "elements": [
        {
          "id": "api-test-feature;test-scenario",
          "name": "Test Scenario",
          "line": 3,
          "keyword": "Scenario",
          "type": "scenario",
          "tags": [
            {
              "name": "@api",
              "line": 2
            }
          ],
          "steps": [
            {
              "keyword": "Given",
              "name": "I have a test step",
              "line": 4,
              "result": {
                "status": "passed",
                "duration": 150000000
              }
            },
            {
              "keyword": "When",
              "name": "I post to an API",
              "line": 5,
              "result": {
                "status": "passed",
                "duration": 250000000
              }
            },
            {
              "keyword": "Then",
              "name": "It should succeed",
              "line": 6,
              "result": {
                "status": "passed",
                "duration": 100000000
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
  testApiPosting();
}

export { testApiPosting };
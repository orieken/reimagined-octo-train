import * as fs from 'fs';
import * as path from 'path';

interface CucumberReport {
  [key: string]: any;
}

interface EnhancedReport {
  metadata: {
    project: string;
    branch: string;
    commit: string;
    timestamp: string;
    runner: string;
    environment: string;
  };
  summary?: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    flaky: number;
    duration: number;
    success_rate: number;
    tags_summary?: Record<string, number>;
  };
  report: any[];
}

interface Config {
  metadata: EnhancedReport['metadata'];
  inputFile?: string;
  reportsDir?: string;
  outputFile: string;
  includeSummary?: boolean;
  includeTagsSummary?: boolean;
  outputFormat?: 'json' | 'pretty' | 'minimal';
  errorScreenshotDir?: string;
}

/**
 * Enhances a Cucumber report with additional metadata
 */
class CucumberReportEnhancer {
  private inputFile: string;
  private outputFile: string;
  private metadata: EnhancedReport['metadata'];
  private includeSummary: boolean;
  private includeTagsSummary: boolean;
  private outputFormat: 'json' | 'pretty' | 'minimal';
  private errorScreenshotDir?: string;

  constructor(
    inputFile: string,
    outputFile: string,
    metadata: EnhancedReport['metadata'],
    options: {
      includeSummary?: boolean;
      includeTagsSummary?: boolean;
      outputFormat?: 'json' | 'pretty' | 'minimal';
      errorScreenshotDir?: string;
    } = {}
  ) {
    this.inputFile = inputFile;
    this.outputFile = outputFile;
    this.metadata = {
      ...metadata,
      timestamp: metadata.timestamp || new Date().toISOString() // Ensure timestamp is set
    };
    this.includeSummary = options.includeSummary ?? true;
    this.includeTagsSummary = options.includeTagsSummary ?? true;
    this.outputFormat = options.outputFormat ?? 'json';
    this.errorScreenshotDir = options.errorScreenshotDir;
  }

  /**
   * Process the Cucumber report and add metadata
   */
  public process(): void {
    try {
      // Read the input file
      const rawData = fs.readFileSync(this.inputFile, 'utf8');
      const cucumberReport: CucumberReport[] = JSON.parse(rawData);

      // Process the report features and elements
      const processedReport = cucumberReport.map(feature => ({
        id: feature.id || this.generateUUID(),
        name: feature.name,
        uri: feature.uri,
        line: feature.line,
        keyword: feature.keyword,
        elements: feature.elements?.map((element: any) => ({
          id: element.id || this.generateUUID(),
          name: element.name,
          line: element.line,
          description: element.description || "",
          keyword: element.keyword,
          type: element.type,
          tags: element.tags || [],
          steps: element.steps || []
        }))
      }));

      // Create the enhanced report structure
      const enhancedReport: EnhancedReport = {
        metadata: this.metadata,
        report: processedReport
      };

      // Add summary if needed
      if (this.includeSummary) {
        enhancedReport.summary = this.generateSummary(processedReport);
      }

      // Extract failure screenshots if directory is specified
      if (this.errorScreenshotDir) {
        this.extractFailureScreenshots(processedReport);
      }

      // Ensure output directory exists
      const dir = path.dirname(this.outputFile);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      // Write the enhanced report to the output file
      let outputContent: string;
      if (this.outputFormat === 'json') {
        outputContent = JSON.stringify(enhancedReport, null, 2);
      } else if (this.outputFormat === 'pretty') {
        outputContent = this.generatePrettyOutput(enhancedReport);
      } else { // minimal
        outputContent = this.generateMinimalOutput(enhancedReport);
      }

      fs.writeFileSync(
        this.outputFile,
        outputContent,
        'utf8'
      );

      // Print success message with summary
      this.printSummary(enhancedReport);
      console.log(`Enhanced report saved to ${this.outputFile}`);
    } catch (error) {
      console.error('Error processing Cucumber report:');
      if (error instanceof Error) {
        console.error(`${error.name}: ${error.message}`);
        if (error.stack) {
          console.error(error.stack.split('\n').slice(1).join('\n'));
        }
      } else {
        console.error(error);
      }
      process.exit(1);
    }
  }

  /**
   * Generate summary statistics from the report
   */
  private generateSummary(report: any[]): EnhancedReport['summary'] {
    const summary = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      flaky: 0,
      duration: 0,
      success_rate: 0,
      tags_summary: {} as Record<string, number>
    };

    // Process each feature
    for (const feature of report) {
      if (!feature.elements) continue;

      // Process each scenario
      for (const scenario of feature.elements) {
        summary.total++;

        // Collect tags if needed
        if (this.includeTagsSummary && scenario.tags) {
          for (const tag of scenario.tags) {
            const tagName = tag.name;
            summary.tags_summary[tagName] = (summary.tags_summary[tagName] || 0) + 1;
          }
        }

        // Check if this is a flaky test
        const isFlaky = scenario.tags?.some((tag: any) => tag.name === '@flaky' || tag.name === '@flaky');
        if (isFlaky) {
          summary.flaky++;
        }

        // Check steps status
        if (!scenario.steps || scenario.steps.length === 0) continue;

        let scenarioPassed = true;
        let scenarioSkipped = false;
        let scenarioDuration = 0;

        for (const step of scenario.steps) {
          if (!step.result) continue;

          // Add duration
          if (step.result.duration) {
            scenarioDuration += step.result.duration;
          }

          // Check status
          if (step.result.status === 'failed') {
            scenarioPassed = false;
          } else if (step.result.status === 'skipped') {
            scenarioSkipped = true;
          }
        }

        // Update summary counts
        if (!scenarioPassed) {
          summary.failed++;
        } else if (scenarioSkipped) {
          summary.skipped++;
        } else {
          summary.passed++;
        }

        // Add to total duration
        summary.duration += scenarioDuration;
      }
    }

    // Calculate success rate (percentage of passed tests)
    if (summary.total > 0) {
      summary.success_rate = (summary.passed / summary.total) * 100;
    }

    return summary;
  }

  /**
   * Extract failure screenshots from embeddings
   */
  private extractFailureScreenshots(report: any[]): void {
    if (!this.errorScreenshotDir) return;

    // Create screenshots directory if it doesn't exist
    if (!fs.existsSync(this.errorScreenshotDir)) {
      fs.mkdirSync(this.errorScreenshotDir, { recursive: true });
    }

    let screenshotCount = 0;

    // Process each feature
    for (const feature of report) {
      if (!feature.elements) continue;

      // Process each scenario
      for (const scenario of feature.elements) {
        // Check if the scenario failed
        const isFailed = scenario.steps?.some((step: any) =>
          step.result?.status === 'failed'
        );

        if (!isFailed) continue;

        // Extract scenario info for filename
        const featureName = feature.name?.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'unknown';
        const scenarioName = scenario.name?.replace(/[^a-z0-9]/gi, '_').toLowerCase() || 'unknown';

        // Look for embeddings in steps
        for (const step of scenario.steps || []) {
          // Skip if no embeddings
          if (!step.embeddings || !Array.isArray(step.embeddings)) continue;

          // Process embeddings
          for (let i = 0; i < step.embeddings.length; i++) {
            const embedding = step.embeddings[i];

            // Skip if not an image
            if (!embedding.mime_type?.includes('image/')) continue;

            // Generate filename
            const timestamp = new Date().getTime();
            const filename = `${featureName}_${scenarioName}_${timestamp}_${i}.png`;
            const filePath = path.join(this.errorScreenshotDir, filename);

            try {
              // Write screenshot data to file
              const imageBuffer = Buffer.from(embedding.data, 'base64');
              fs.writeFileSync(filePath, imageBuffer);
              screenshotCount++;
            } catch (error) {
              console.warn(`Failed to extract screenshot to ${filePath}:`, error);
            }
          }
        }
      }
    }

    if (screenshotCount > 0) {
      console.log(`Extracted ${screenshotCount} failure screenshots to ${this.errorScreenshotDir}`);
    }
  }

  /**
   * Generate a pretty-formatted text report
   */
  private generatePrettyOutput(report: EnhancedReport): string {
    const lines: string[] = [];

    // Add header
    lines.push('='.repeat(80));
    lines.push(`CUCUMBER TEST REPORT - ${report.metadata.project}`);
    lines.push('='.repeat(80));
    lines.push(`Branch: ${report.metadata.branch}`);
    lines.push(`Commit: ${report.metadata.commit}`);
    lines.push(`Time: ${report.metadata.timestamp}`);
    lines.push(`Environment: ${report.metadata.environment}`);
    lines.push('='.repeat(80));

    // Add summary if available
    if (report.summary) {
      const summary = report.summary;
      lines.push('\nSUMMARY:');
      lines.push(`Total Scenarios: ${summary.total}`);
      lines.push(`Passed: ${summary.passed} (${summary.success_rate.toFixed(2)}%)`);
      lines.push(`Failed: ${summary.failed}`);
      lines.push(`Skipped: ${summary.skipped}`);
      lines.push(`Flaky: ${summary.flaky}`);
      lines.push(`Total Duration: ${this.formatDuration(summary.duration)}`);

      // Add tags summary if available
      if (summary.tags_summary && Object.keys(summary.tags_summary).length > 0) {
        lines.push('\nTAGS SUMMARY:');
        for (const [tag, count] of Object.entries(summary.tags_summary)) {
          lines.push(`  ${tag}: ${count}`);
        }
      }
    }

    // Add features
    lines.push('\nFEATURES:');
    for (const feature of report.report) {
      lines.push(`\n${feature.keyword}: ${feature.name} (${feature.uri})`);

      if (!feature.elements || feature.elements.length === 0) {
        lines.push('  No scenarios');
        continue;
      }

      // Add scenarios
      for (const scenario of feature.elements) {
        const status = this.getScenarioStatus(scenario);
        const statusSymbol = this.getStatusSymbol(status);

        lines.push(`  ${statusSymbol} ${scenario.keyword}: ${scenario.name}`);

        // Add steps
        if (scenario.steps && scenario.steps.length > 0) {
          for (const step of scenario.steps) {
            const stepStatus = step.result?.status || 'unknown';
            const stepSymbol = this.getStatusSymbol(stepStatus);
            const duration = step.result?.duration
              ? ` (${this.formatDuration(step.result.duration)})`
              : '';

            lines.push(`    ${stepSymbol} ${step.keyword}${step.name}${duration}`);

            // Add error message if step failed
            if (stepStatus === 'failed' && step.result?.error_message) {
              const errorLines = step.result.error_message.split('\n');
              const errorSummary = errorLines[0] + (errorLines.length > 1 ? ' ...' : '');
              lines.push(`      Error: ${errorSummary}`);
            }
          }
        }
      }
    }

    return lines.join('\n');
  }

  /**
   * Generate a minimal output format
   */
  private generateMinimalOutput(report: EnhancedReport): string {
    // For minimal output, we'll just include a condensed JSON with summary and basic info
    const minimal = {
      metadata: report.metadata,
      summary: report.summary,
      features: report.report.map(feature => ({
        name: feature.name,
        scenarios_count: feature.elements?.length || 0,
        failures: feature.elements?.filter(element =>
          this.getScenarioStatus(element) === 'failed'
        ).map(element => ({
          name: element.name,
          error: this.getScenarioError(element)
        })) || []
      }))
    };

    return JSON.stringify(minimal, null, 2);
  }

  /**
   * Get the overall status of a scenario
   */
  private getScenarioStatus(scenario: any): string {
    if (!scenario.steps || scenario.steps.length === 0) {
      return 'unknown';
    }

    const hasFailure = scenario.steps.some((step: any) =>
      step.result?.status === 'failed'
    );

    if (hasFailure) {
      return 'failed';
    }

    const hasSkipped = scenario.steps.some((step: any) =>
      step.result?.status === 'skipped'
    );

    if (hasSkipped) {
      return 'skipped';
    }

    const allPassed = scenario.steps.every((step: any) =>
      step.result?.status === 'passed'
    );

    return allPassed ? 'passed' : 'unknown';
  }

  /**
   * Get a symbol representing the status
   */
  private getStatusSymbol(status: string): string {
    switch (status) {
      case 'passed': return '✅';
      case 'failed': return '❌';
      case 'skipped': return '⏩';
      case 'pending': return '⏳';
      default: return '❓';
    }
  }

  /**
   * Get the error message from a scenario
   */
  private getScenarioError(scenario: any): string {
    if (!scenario.steps) return '';

    for (const step of scenario.steps) {
      if (step.result?.status === 'failed' && step.result.error_message) {
        const errorLines = step.result.error_message.split('\n');
        return errorLines[0];
      }
    }

    return '';
  }

  /**
   * Format a duration in nanoseconds to a human-readable string
   */
  private formatDuration(nanoseconds: number): string {
    const milliseconds = nanoseconds / 1000000;

    if (milliseconds < 1000) {
      return `${Math.round(milliseconds)}ms`;
    }

    const seconds = milliseconds / 1000;

    if (seconds < 60) {
      return `${seconds.toFixed(2)}s`;
    }

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;

    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  }

  /**
   * Print a summary of the report to the console
   */
  private printSummary(report: EnhancedReport): void {
    if (!report.summary) return;

    const summary = report.summary;
    const totalScenarios = summary.total;
    const passRate = summary.success_rate.toFixed(2);

    console.log('\n=== Test Results Summary ===');
    console.log(`Total Scenarios: ${totalScenarios}`);

    // Use colored output for pass/fail
    console.log(`Passed: ${summary.passed} (${passRate}%)`);
    console.log(`Failed: ${summary.failed}`);

    if (summary.skipped > 0) {
      console.log(`Skipped: ${summary.skipped}`);
    }

    if (summary.flaky > 0) {
      console.log(`Flaky: ${summary.flaky}`);
    }

    console.log(`Duration: ${this.formatDuration(summary.duration)}`);
    console.log('===========================\n');
  }

  /**
   * Generate a UUID for elements that don't have an ID
   */
  private generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  /**
   * Find the most recent Cucumber report in a directory
   * @param directory Directory to search in
   * @param pattern Optional regex pattern to match filenames
   * @returns Path to the most recent report file
   */
  public static findLatestReport(directory: string, pattern: RegExp = /cucumber_report.*\.json$/): string {
    try {
      if (!fs.existsSync(directory)) {
        throw new Error(`Directory does not exist: ${directory}`);
      }

      const files = fs.readdirSync(directory)
        .filter(file => pattern.test(file))
        .map(file => ({
          name: file,
          path: path.join(directory, file),
          mtime: fs.statSync(path.join(directory, file)).mtime
        }))
        .sort((a, b) => b.mtime.getTime() - a.mtime.getTime());

      if (files.length === 0) {
        throw new Error(`No matching report files found in ${directory}`);
      }

      console.log(`Found latest report: ${files[0].name} (Modified: ${files[0].mtime.toISOString()})`);
      return files[0].path;
    } catch (error) {
      console.error('Error finding latest report:', error);
      process.exit(1);
    }
  }

  /**
   * Create enhancer from a config file
   */
  public static fromConfigFile(configPath: string): CucumberReportEnhancer {
    try {
      const configData = fs.readFileSync(configPath, 'utf8');
      const config: Config = JSON.parse(configData);

      // If reportsDir is specified and inputFile is not, find the latest report
      let inputFile = config.inputFile;
      if (!inputFile && config.reportsDir) {
        inputFile = CucumberReportEnhancer.findLatestReport(config.reportsDir);
      } else if (!inputFile) {
        throw new Error("Either inputFile or reportsDir must be specified in the config");
      }

      return new CucumberReportEnhancer(
        inputFile,
        config.outputFile,
        config.metadata,
        {
          includeSummary: config.includeSummary,
          includeTagsSummary: config.includeTagsSummary,
          outputFormat: config.outputFormat,
          errorScreenshotDir: config.errorScreenshotDir
        }
      );
    } catch (error) {
      console.error(`Error reading config file ${configPath}:`, error);
      if (error instanceof Error) {
        console.error(`${error.name}: ${error.message}`);
      }
      process.exit(1);
    }
  }
}

/**
 * Command line script to enhance Cucumber reports
 */
function main(): void {
  // Get command line arguments
  const args = process.argv.slice(2);

  // Initialize options with defaults
  const options: {
    includeSummary?: boolean;
    includeTagsSummary?: boolean;
    outputFormat?: 'json' | 'pretty' | 'minimal';
    errorScreenshotDir?: string;
  } = {
    includeSummary: true,
    includeTagsSummary: true,
    outputFormat: 'json'
  };

  // Parse options that could appear anywhere in the arguments
  // These are options like --format, --screenshots, etc.
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--format' && i + 1 < args.length) {
      const format = args[i + 1].toLowerCase();
      if (['json', 'pretty', 'minimal'].includes(format)) {
        options.outputFormat = format as 'json' | 'pretty' | 'minimal';
        // Remove these args so they don't interfere with other parsing
        args.splice(i, 2);
        i--; // Adjust index after removal
      }
    } else if (args[i] === '--screenshots' && i + 1 < args.length) {
      options.errorScreenshotDir = args[i + 1];
      args.splice(i, 2);
      i--;
    } else if (args[i] === '--no-summary') {
      options.includeSummary = false;
      args.splice(i, 1);
      i--;
    } else if (args[i] === '--no-tags-summary') {
      options.includeTagsSummary = false;
      args.splice(i, 1);
      i--;
    }
  }

  // Check if a config file is specified
  if (args.length > 0 && args[0] === '--config') {
    if (args.length < 2) {
      console.error('Error: Config file path not provided');
      displayUsage();
      process.exit(1);
    }

    const configPath = args[1];
    const enhancer = CucumberReportEnhancer.fromConfigFile(configPath);
    enhancer.process();
    return;
  }

  // Check if we need to find the latest report in a directory
  if (args.length > 0 && args[0] === '--latest') {
    const reportsDir = args.length > 1 ? args[1] : './reports';
    const outputFile = args.length > 2 ? args[2] : 'enhanced-report.json';

    const inputFile = CucumberReportEnhancer.findLatestReport(reportsDir);
    const metadata = getDefaultMetadata();

    const enhancer = new CucumberReportEnhancer(inputFile, outputFile, metadata, options);
    enhancer.process();
    return;
  }

  // Handle direct arguments
  if (args.length < 1) {
    displayUsage();
    process.exit(1);
  }

  const inputFile = args[0];
  const defaultOutputName = `enhanced-${path.basename(inputFile)}`;
  const outputFile = args[1] || defaultOutputName;

  // Create and run the enhancer
  const enhancer = new CucumberReportEnhancer(inputFile, outputFile, getDefaultMetadata(), options);
  enhancer.process();
}

/**
 * Get default metadata from environment variables or hardcoded defaults
 */
function getDefaultMetadata(): EnhancedReport['metadata'] {
  return {
    project: process.env.PROJECT_NAME || 'retail-platform',
    branch: process.env.BRANCH_NAME || 'main',
    commit: process.env.COMMIT_HASH || 'a389f82',
    timestamp: new Date().toISOString(),
    runner: process.env.RUNNER || 'cucumber-junit',
    environment: process.env.TEST_ENV || 'integration'
  };
}

function displayUsage(): void {
  console.log(`
Cucumber Report Enhancer
========================

Usage: 
  node cucumber-enhancer.js <inputFile> [outputFile] [options]
  node cucumber-enhancer.js --config <configFilePath> [options]
  node cucumber-enhancer.js --latest [reportsDir] [outputFile] [options]

Options:
  --format <json|pretty|minimal>  Output format (default: json)
  --screenshots <directory>       Directory to extract failure screenshots
  --no-summary                    Don't include test summary statistics
  --no-tags-summary               Don't include tags in the summary

Examples:
  node cucumber-enhancer.js cucumber_report.json enhanced-report.json
  node cucumber-enhancer.js cucumber_report.json report.txt --format pretty
  node cucumber-enhancer.js --config cucumber-enhancer-config.json
  node cucumber-enhancer.js --latest ./reports enhanced-report.json --screenshots ./failures
  `);
}

// Run the script if it's called directly
if (require.main === module) {
  main();
}

export { CucumberReportEnhancer };
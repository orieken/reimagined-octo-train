import { TestMetric, TestStatus } from './testMetric';

/**
 * Test report parameters interface
 */
export interface TestReportParams {
  id: string;
  projectId: string;
  projectName: string;
  buildNumber: string;
  buildUrl?: string | null;
  timestamp: Date;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  duration: number;
  testMetrics?: TestMetric[];
  azureDevOpsBuildId?: string | null;
}

/**
 * Report comparison result interface
 */
export interface ReportComparisonResult {
  totalTestsDiff: number;
  passedTestsDiff: number;
  failedTestsDiff: number;
  skippedTestsDiff: number;
  durationDiff: number;
  passRateDiff: number;
}

/**
 * Represents a test report with aggregated metrics
 */
export class TestReport {
  public readonly id: string;
  public readonly projectId: string;
  public readonly projectName: string;
  public readonly buildNumber: string;
  public readonly buildUrl: string | null;
  public readonly timestamp: Date;
  public readonly totalTests: number;
  public readonly passedTests: number;
  public readonly failedTests: number;
  public readonly skippedTests: number;
  public readonly duration: number;
  public readonly testMetrics: TestMetric[];
  public readonly azureDevOpsBuildId: string | null;

  /**
   * Create a new test report
   * @param params - The test report parameters
   */
  constructor(params: TestReportParams) {
    this.id = params.id;
    this.projectId = params.projectId;
    this.projectName = params.projectName;
    this.buildNumber = params.buildNumber;
    this.buildUrl = params.buildUrl || null;
    this.timestamp = params.timestamp;
    this.totalTests = params.totalTests;
    this.passedTests = params.passedTests;
    this.failedTests = params.failedTests;
    this.skippedTests = params.skippedTests;
    this.duration = params.duration;
    this.testMetrics = params.testMetrics || [];
    this.azureDevOpsBuildId = params.azureDevOpsBuildId || null;

    this.validate();
  }

  /**
   * Validate the test report object
   * @throws Error if validation fails
   */
  private validate(): void {
    if (!this.id) throw new Error('Test report ID is required');
    if (!this.projectId) throw new Error('Project ID is required');
    if (!this.projectName) throw new Error('Project name is required');
    if (!this.buildNumber) throw new Error('Build number is required');
    if (!(this.timestamp instanceof Date)) {
      throw new Error('Timestamp must be a valid Date object');
    }

    // Validate numeric fields
    if (!Number.isInteger(this.totalTests) || this.totalTests < 0) {
      throw new Error('Total tests must be a non-negative integer');
    }
    if (!Number.isInteger(this.passedTests) || this.passedTests < 0) {
      throw new Error('Passed tests must be a non-negative integer');
    }
    if (!Number.isInteger(this.failedTests) || this.failedTests < 0) {
      throw new Error('Failed tests must be a non-negative integer');
    }
    if (!Number.isInteger(this.skippedTests) || this.skippedTests < 0) {
      throw new Error('Skipped tests must be a non-negative integer');
    }
    if (typeof this.duration !== 'number' || this.duration < 0) {
      throw new Error('Duration must be a non-negative number');
    }

    // Ensure the sum of passed, failed, and skipped tests equals the total
    if (this.passedTests + this.failedTests + this.skippedTests !== this.totalTests) {
      throw new Error('Sum of passed, failed, and skipped tests must equal total tests');
    }
  }

  /**
   * Calculate and return the pass rate as a percentage
   * @returns The pass rate as a percentage (0-100)
   */
  public getPassRate(): number {
    if (this.totalTests === 0) return 0;
    return (this.passedTests / this.totalTests) * 100;
  }

  /**
   * Get failed test metrics
   * @returns Array of failed test metrics
   */
  public getFailedTestMetrics(): TestMetric[] {
    return this.testMetrics.filter(metric => metric.status === TestStatus.Failed);
  }

  /**
   * Get passed test metrics
   * @returns Array of passed test metrics
   */
  public getPassedTestMetrics(): TestMetric[] {
    return this.testMetrics.filter(metric => metric.status === TestStatus.Passed);
  }

  /**
   * Get skipped test metrics
   * @returns Array of skipped test metrics
   */
  public getSkippedTestMetrics(): TestMetric[] {
    return this.testMetrics.filter(metric => metric.status === TestStatus.Skipped);
  }

  /**
   * Compare with another test report and generate a diff
   * @param otherReport - The report to compare with
   * @returns The differences between the reports
   */
  public compareTo(otherReport: TestReport): ReportComparisonResult {
    return {
      totalTestsDiff: this.totalTests - otherReport.totalTests,
      passedTestsDiff: this.passedTests - otherReport.passedTests,
      failedTestsDiff: this.failedTests - otherReport.failedTests,
      skippedTestsDiff: this.skippedTests - otherReport.skippedTests,
      durationDiff: this.duration - otherReport.duration,
      passRateDiff: this.getPassRate() - otherReport.getPassRate()
    };
  }

  /**
   * Check if this report has associated Azure DevOps build information
   * @returns True if the report has Azure DevOps build ID
   */
  public hasAzureDevOpsBuild(): boolean {
    return !!this.azureDevOpsBuildId;
  }
}
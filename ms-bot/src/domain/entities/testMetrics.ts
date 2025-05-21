/**
 * Test status enum
 */
export enum TestStatus {
  Passed = 'passed',
  Failed = 'failed',
  Skipped = 'skipped'
}

/**
 * Test metric parameters interface
 */
export interface TestMetricParams {
  id: string;
  name: string;
  status: TestStatus;
  duration: number;
  className: string;
  projectId: string;
  buildNumber: string;
  timestamp: Date;
  errorMessage?: string | null;
}

/**
 * Represents a single test metric
 */
export class TestMetric {
  public readonly id: string;
  public readonly name: string;
  public readonly status: TestStatus;
  public readonly duration: number;
  public readonly className: string;
  public readonly projectId: string;
  public readonly buildNumber: string;
  public readonly timestamp: Date;
  public readonly errorMessage: string | null;

  /**
   * Create a new test metric
   * @param params - The test metric parameters
   */
  constructor(params: TestMetricParams) {
    this.id = params.id;
    this.name = params.name;
    this.status = params.status;
    this.duration = params.duration;
    this.className = params.className;
    this.projectId = params.projectId;
    this.buildNumber = params.buildNumber;
    this.timestamp = params.timestamp;
    this.errorMessage = params.errorMessage || null;

    this.validate();
  }

  /**
   * Validate the test metric object
   * @throws Error if validation fails
   */
  private validate(): void {
    if (!this.id) throw new Error('Test metric ID is required');
    if (!this.name) throw new Error('Test name is required');
    if (!Object.values(TestStatus).includes(this.status)) {
      throw new Error(`Test status must be one of: ${Object.values(TestStatus).join(', ')}`);
    }
    if (typeof this.duration !== 'number' || this.duration < 0) {
      throw new Error('Test duration must be a non-negative number');
    }
    if (!this.className) throw new Error('Test class name is required');
    if (!this.projectId) throw new Error('Project ID is required');
    if (!this.buildNumber) throw new Error('Build number is required');
    if (!(this.timestamp instanceof Date)) {
      throw new Error('Timestamp must be a valid Date object');
    }
    if (this.status === TestStatus.Failed && !this.errorMessage) {
      throw new Error('Error message is required for failed tests');
    }
  }

  /**
   * Check if the test passed
   * @returns True if the test passed
   */
  public isPassed(): boolean {
    return this.status === TestStatus.Passed;
  }

  /**
   * Check if the test failed
   * @returns True if the test failed
   */
  public isFailed(): boolean {
    return this.status === TestStatus.Failed;
  }

  /**
   * Check if the test was skipped
   * @returns True if the test was skipped
   */
  public isSkipped(): boolean {
    return this.status === TestStatus.Skipped;
  }
}
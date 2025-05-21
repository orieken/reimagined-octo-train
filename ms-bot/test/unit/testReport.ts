import { TestReport } from '../../../../src/domain/entities/testReport';
import { TestMetric, TestStatus } from '../../../../src/domain/entities/testMetric';

describe('TestReport Entity', () => {
  const validParams = {
    id: 'report-1',
    projectId: 'project-1',
    projectName: 'Test Project',
    buildNumber: 'build-123',
    buildUrl: 'https://example.com/builds/123',
    timestamp: new Date(),
    totalTests: 100,
    passedTests: 90,
    failedTests: 5,
    skippedTests: 5,
    duration: 5000,
    testMetrics: [],
    azureDevOpsBuildId: 'azdo-build-123'
  };

  const createTestMetric = (id: string, name: string, status: TestStatus, errorMessage?: string): TestMetric => {
    return new TestMetric({
      id,
      name,
      status,
      duration: 100,
      className: 'com.example.TestClass',
      projectId: 'project-1',
      buildNumber: 'build-123',
      timestamp: new Date(),
      errorMessage: status === TestStatus.Failed ? errorMessage || 'Test failed' : null
    });
  };

  describe('constructor', () => {
    it('should create a valid TestReport when all required params are provided', () => {
      const testReport = new TestReport(validParams);

      expect(testReport.id).toBe(validParams.id);
      expect(testReport.projectId).toBe(validParams.projectId);
      expect(testReport.projectName).toBe(validParams.projectName);
      expect(testReport.buildNumber).toBe(validParams.buildNumber);
      expect(testReport.buildUrl).toBe(validParams.buildUrl);
      expect(testReport.timestamp).toBe(validParams.timestamp);
      expect(testReport.totalTests).toBe(validParams.totalTests);
      expect(testReport.passedTests).toBe(validParams.passedTests);
      expect(testReport.failedTests).toBe(validParams.failedTests);
      expect(testReport.skippedTests).toBe(validParams.skippedTests);
      expect(testReport.duration).toBe(validParams.duration);
      expect(testReport.testMetrics).toEqual(validParams.testMetrics);
      expect(testReport.azureDevOpsBuildId).toBe(validParams.azureDevOpsBuildId);
    });

    it('should throw error when id is missing', () => {
      const params = { ...validParams, id: '' };

      expect(() => {
        new TestReport(params);
      }).toThrow('Test report ID is required');
    });

    it('should throw error when projectId is missing', () => {
      const params = { ...validParams, projectId: '' };

      expect(() => {
        new TestReport(params);
      }).toThrow('Project ID is required');
    });

    it('should throw error when projectName is missing', () => {
      const params = { ...validParams, projectName: '' };

      expect(() => {
        new TestReport(params);
      }).toThrow('Project name is required');
    });

    it('should throw error when buildNumber is missing', () => {
      const params = { ...validParams, buildNumber: '' };

      expect(() => {
        new TestReport(params);
      }).toThrow('Build number is required');
    });

    it('should throw error when timestamp is not a Date', () => {
      const params = { ...validParams, timestamp: 'not a date' as unknown as Date };

      expect(() => {
        new TestReport(params);
      }).toThrow('Timestamp must be a valid Date object');
    });

    it('should throw error when totalTests is negative', () => {
      const params = { ...validParams, totalTests: -1 };

      expect(() => {
        new TestReport(params);
      }).toThrow('Total tests must be a non-negative integer');
    });

    it('should throw error when sum of tests does not equal totalTests', () => {
      const params = {
        ...validParams,
        totalTests: 100,
        passedTests: 90,
        failedTests: 5,
        skippedTests: 10  // Sum is 105, not 100
      };

      expect(() => {
        new TestReport(params);
      }).toThrow('Sum of passed, failed, and skipped tests must equal total tests');
    });

    it('should set buildUrl to null if not provided', () => {
      const params = { ...validParams, buildUrl: undefined };
      const testReport = new TestReport(params);
      expect(testReport.buildUrl).toBeNull();
    });

    it('should set azureDevOpsBuildId to null if not provided', () => {
      const params = { ...validParams, azureDevOpsBuildId: undefined };
      const testReport = new TestReport(params);
      expect(testReport.azureDevOpsBuildId).toBeNull();
    });
  });

  describe('methods', () => {
    it('getPassRate() should calculate correct pass rate percentage', () => {
      const testReport = new TestReport(validParams);
      expect(testReport.getPassRate()).toBe(90);
    });

    it('getPassRate() should return 0 when totalTests is 0', () => {
      const params = {
        ...validParams,
        totalTests: 0,
        passedTests: 0,
        failedTests: 0,
        skippedTests: 0
      };
      const testReport = new TestReport(params);
      expect(testReport.getPassRate()).toBe(0);
    });

    it('getFailedTestMetrics() should return only failed test metrics', () => {
      const failedTest1 = createTestMetric('test-1', 'Failed Test 1', TestStatus.Failed);
      const failedTest2 = createTestMetric('test-2', 'Failed Test 2', TestStatus.Failed);
      const passedTest = createTestMetric('test-3', 'Passed Test', TestStatus.Passed);

      const params = {
        ...validParams,
        testMetrics: [failedTest1, passedTest, failedTest2]
      };

      const testReport = new TestReport(params);
      const failedTests = testReport.getFailedTestMetrics();

      expect(failedTests.length).toBe(2);
      expect(failedTests).toContain(failedTest1);
      expect(failedTests).toContain(failedTest2);
      expect(failedTests).not.toContain(passedTest);
    });

    it('getPassedTestMetrics() should return only passed test metrics', () => {
      const failedTest = createTestMetric('test-1', 'Failed Test', TestStatus.Failed);
      const passedTest1 = createTestMetric('test-2', 'Passed Test 1', TestStatus.Passed);
      const passedTest2 = createTestMetric('test-3', 'Passed Test 2', TestStatus.Passed);

      const params = {
        ...validParams,
        testMetrics: [failedTest, passedTest1, passedTest2]
      };

      const testReport = new TestReport(params);
      const passedTests = testReport.getPassedTestMetrics();

      expect(passedTests.length).toBe(2);
      expect(passedTests).toContain(passedTest1);
      expect(passedTests).toContain(passedTest2);
      expect(passedTests).not.toContain(failedTest);
    });

    it('getSkippedTestMetrics() should return only skipped test metrics', () => {
      const skippedTest1 = createTestMetric('test-1', 'Skipped Test 1', TestStatus.Skipped);
      const passedTest = createTestMetric('test-2', 'Passed Test', TestStatus.Passed);
      const skippedTest2 = createTestMetric('test-3', 'Skipped Test 2', TestStatus.Skipped);

      const params = {
        ...validParams,
        testMetrics: [skippedTest1, passedTest, skippedTest2]
      };

      const testReport = new TestReport(params);
      const skippedTests = testReport.getSkippedTestMetrics();

      expect(skippedTests.length).toBe(2);
      expect(skippedTests).toContain(skippedTest1);
      expect(skippedTests).toContain(skippedTest2);
      expect(skippedTests).not.toContain(passedTest);
    });

    it('compareTo() should calculate correct differences between reports', () => {
      const report1 = new TestReport({
        ...validParams,
        totalTests: 100,
        passedTests: 90,
        failedTests: 5,
        skippedTests: 5,
        duration: 5000
      });

      const report2 = new TestReport({
        ...validParams,
        totalTests: 105,
        passedTests: 85,
        failedTests: 10,
        skippedTests: 10,
        duration: 6000
      });

      const comparison = report1.compareTo(report2);

      expect(comparison.totalTestsDiff).toBe(-5);
      expect(comparison.passedTestsDiff).toBe(5);
      expect(comparison.failedTestsDiff).toBe(-5);
      expect(comparison.skippedTestsDiff).toBe(-5);
      expect(comparison.durationDiff).toBe(-1000);
      expect(comparison.passRateDiff).toBeCloseTo(4.76, 1); // 90 - (85/105*100)
    });

    it('hasAzureDevOpsBuild() should return true when azureDevOpsBuildId exists', () => {
      const testReport = new TestReport(validParams);
      expect(testReport.hasAzureDevOpsBuild()).toBe(true);
    });

    it('hasAzureDevOpsBuild() should return false when azureDevOpsBuildId does not exist', () => {
      const params = { ...validParams, azureDevOpsBuildId: null };
      const testReport = new TestReport(params);
      expect(testReport.hasAzureDevOpsBuild()).toBe(false);
    });
  });
});
import { TestMetric, TestStatus } from '../../../../src/domain/entities/testMetric';

describe('TestMetric Entity', () => {
  const validParams = {
    id: 'test-1',
    name: 'should pass when condition is met',
    status: TestStatus.Passed,
    duration: 1500,
    className: 'com.example.TestClass',
    projectId: 'project-1',
    buildNumber: 'build-123',
    timestamp: new Date(),
    errorMessage: null
  };

  describe('constructor', () => {
    it('should create a valid TestMetric when all required params are provided', () => {
      const testMetric = new TestMetric(validParams);

      expect(testMetric.id).toBe(validParams.id);
      expect(testMetric.name).toBe(validParams.name);
      expect(testMetric.status).toBe(validParams.status);
      expect(testMetric.duration).toBe(validParams.duration);
      expect(testMetric.className).toBe(validParams.className);
      expect(testMetric.projectId).toBe(validParams.projectId);
      expect(testMetric.buildNumber).toBe(validParams.buildNumber);
      expect(testMetric.timestamp).toBe(validParams.timestamp);
      expect(testMetric.errorMessage).toBe(validParams.errorMessage);
    });

    it('should throw error when id is missing', () => {
      const params = { ...validParams, id: '' };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Test metric ID is required');
    });

    it('should throw error when name is missing', () => {
      const params = { ...validParams, name: '' };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Test name is required');
    });

    it('should throw error when status is invalid', () => {
      const params = { ...validParams, status: 'invalid' as TestStatus };

      expect(() => {
        new TestMetric(params);
      }).toThrow(`Test status must be one of: ${Object.values(TestStatus).join(', ')}`);
    });

    it('should throw error when duration is negative', () => {
      const params = { ...validParams, duration: -1 };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Test duration must be a non-negative number');
    });

    it('should throw error when className is missing', () => {
      const params = { ...validParams, className: '' };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Test class name is required');
    });

    it('should throw error when projectId is missing', () => {
      const params = { ...validParams, projectId: '' };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Project ID is required');
    });

    it('should throw error when buildNumber is missing', () => {
      const params = { ...validParams, buildNumber: '' };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Build number is required');
    });

    it('should throw error when timestamp is not a Date', () => {
      const params = { ...validParams, timestamp: 'not a date' as unknown as Date };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Timestamp must be a valid Date object');
    });

    it('should throw error when status is failed but errorMessage is missing', () => {
      const params = { ...validParams, status: TestStatus.Failed, errorMessage: null };

      expect(() => {
        new TestMetric(params);
      }).toThrow('Error message is required for failed tests');
    });

    it('should allow errorMessage when status is failed', () => {
      const params = {
        ...validParams,
        status: TestStatus.Failed,
        errorMessage: 'Test failed due to assertion error'
      };

      const testMetric = new TestMetric(params);
      expect(testMetric.errorMessage).toBe(params.errorMessage);
    });
  });

  describe('status methods', () => {
    it('isPassed() should return true when status is passed', () => {
      const testMetric = new TestMetric(validParams);
      expect(testMetric.isPassed()).toBe(true);
      expect(testMetric.isFailed()).toBe(false);
      expect(testMetric.isSkipped()).toBe(false);
    });

    it('isFailed() should return true when status is failed', () => {
      const params = {
        ...validParams,
        status: TestStatus.Failed,
        errorMessage: 'Test failed due to assertion error'
      };
      const testMetric = new TestMetric(params);
      expect(testMetric.isPassed()).toBe(false);
      expect(testMetric.isFailed()).toBe(true);
      expect(testMetric.isSkipped()).toBe(false);
    });

    it('isSkipped() should return true when status is skipped', () => {
      const params = { ...validParams, status: TestStatus.Skipped };
      const testMetric = new TestMetric(params);
      expect(testMetric.isPassed()).toBe(false);
      expect(testMetric.isFailed()).toBe(false);
      expect(testMetric.isSkipped()).toBe(true);
    });
  });
});
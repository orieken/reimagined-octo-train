import { ConfigService } from '../../../src/config/config';

// Save original environment
const originalEnv = { ...process.env };

describe('ConfigService', () => {
  let configService: ConfigService;

  beforeEach(() => {
    // Reset environment variables before each test
    process.env = { ...originalEnv };
    // Make sure we're in test environment so validation is skipped
    process.env.NODE_ENV = 'test';

    // Set some test values
    process.env.TEST_STRING = 'test-value';
    process.env.TEST_NUMBER = '42';
    process.env.TEST_BOOLEAN_TRUE = 'true';
    process.env.TEST_BOOLEAN_FALSE = 'false';

    configService = new ConfigService();
  });

  afterAll(() => {
    // Restore original environment
    process.env = originalEnv;
  });

  describe('get', () => {
    it('should return the value when the key exists', () => {
      expect(configService.get('TEST_STRING')).toBe('test-value');
    });

    it('should return the default value when the key does not exist', () => {
      expect(configService.get('NON_EXISTENT_KEY', 'default-value')).toBe('default-value');
    });

    it('should throw an error when the key does not exist and no default value is provided', () => {
      expect(() => {
        configService.get('NON_EXISTENT_KEY');
      }).toThrow('Configuration key \'NON_EXISTENT_KEY\' not found and no default value provided');
    });
  });

  describe('getBoolean', () => {
    it('should return true for string "true"', () => {
      expect(configService.getBoolean('TEST_BOOLEAN_TRUE')).toBe(true);
    });

    it('should return false for string "false"', () => {
      expect(configService.getBoolean('TEST_BOOLEAN_FALSE')).toBe(false);
    });

    it('should return the default value when the key does not exist', () => {
      expect(configService.getBoolean('NON_EXISTENT_KEY', true)).toBe(true);
      expect(configService.getBoolean('NON_EXISTENT_KEY', false)).toBe(false);
    });

    it('should handle other truthy values', () => {
      process.env.TEST_BOOLEAN_YES = 'yes';
      process.env.TEST_BOOLEAN_1 = '1';

      expect(configService.getBoolean('TEST_BOOLEAN_YES')).toBe(true);
      expect(configService.getBoolean('TEST_BOOLEAN_1')).toBe(true);
    });
  });

  describe('getNumber', () => {
    it('should return the number value when the key exists', () => {
      expect(configService.getNumber('TEST_NUMBER')).toBe(42);
    });

    it('should throw an error when the value is not a valid number', () => {
      process.env.TEST_INVALID_NUMBER = 'not-a-number';

      expect(() => {
        configService.getNumber('TEST_INVALID_NUMBER');
      }).toThrow('Configuration key \'TEST_INVALID_NUMBER\' value \'not-a-number\' is not a valid number');
    });

    it('should return the default value when the key does not exist', () => {
      expect(configService.getNumber('NON_EXISTENT_KEY', 99)).toBe(99);
    });
  });

  describe('environment checks', () => {
    it('isProduction() should return true when NODE_ENV is production', () => {
      process.env.NODE_ENV = 'production';
      const prodConfigService = new ConfigService();

      expect(prodConfigService.isProduction()).toBe(true);
      expect(prodConfigService.isDevelopment()).toBe(false);
      expect(prodConfigService.isTest()).toBe(false);
    });

    it('isDevelopment() should return true when NODE_ENV is development', () => {
      process.env.NODE_ENV = 'development';
      const devConfigService = new ConfigService();

      expect(devConfigService.isProduction()).toBe(false);
      expect(devConfigService.isDevelopment()).toBe(true);
      expect(devConfigService.isTest()).toBe(false);
    });

    it('isTest() should return true when NODE_ENV is test', () => {
      process.env.NODE_ENV = 'test';
      const testConfigService = new ConfigService();

      expect(testConfigService.isProduction()).toBe(false);
      expect(testConfigService.isDevelopment()).toBe(false);
      expect(testConfigService.isTest()).toBe(true);
    });
  });
});
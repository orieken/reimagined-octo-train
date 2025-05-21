import { CacheService } from '../../../../src/infrastructure/persistence/cacheService';
import { Logger } from '../../../../src/infrastructure/logging/logger';
import { ConfigService } from '../../../../src/config/config';

// Mock dependencies
jest.mock('../../../../src/infrastructure/logging/logger');
jest.mock('../../../../src/config/config');

describe('CacheService', () => {
  let cacheService: CacheService;
  let mockLogger: jest.Mocked<Logger>;
  let mockConfigService: jest.Mocked<ConfigService>;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Create mock instances
    mockLogger = {
      info: jest.fn(),
      debug: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
      verbose: jest.fn(),
      child: jest.fn().mockReturnThis()
    } as unknown as jest.Mocked<Logger>;

    mockConfigService = {
      get: jest.fn(),
      getNumber: jest.fn().mockReturnValue(60), // Default TTL
      getBoolean: jest.fn(),
      isProduction: jest.fn().mockReturnValue(false),
      isDevelopment: jest.fn().mockReturnValue(false),
      isTest: jest.fn().mockReturnValue(true)
    } as unknown as jest.Mocked<ConfigService>;

    // Create service instance
    cacheService = new CacheService(mockLogger, mockConfigService);
  });

  describe('get', () => {
    it('should return null when key does not exist', async () => {
      const result = await cacheService.get('non-existent-key');
      expect(result).toBeNull();
    });

    it('should return the cached value when key exists', async () => {
      const testKey = 'test-key';
      const testValue = { name: 'test-value' };

      await cacheService.set(testKey, testValue);
      const result = await cacheService.get(testKey);

      expect(result).toEqual(testValue);
      expect(mockLogger.debug).toHaveBeenCalledWith(expect.stringContaining(`Cache hit for key ${testKey}`));
    });
  });

  describe('set', () => {
    it('should cache the value with default TTL', async () => {
      const testKey = 'test-key';
      const testValue = { name: 'test-value' };

      await cacheService.set(testKey, testValue);

      expect(mockLogger.debug).toHaveBeenCalledWith(expect.stringContaining(`Cache set for key ${testKey}`));
      expect(await cacheService.get(testKey)).toEqual(testValue);
    });

    it('should cache the value with custom TTL', async () => {
      const testKey = 'test-key';
      const testValue = { name: 'test-value' };
      const ttl = 120;

      await cacheService.set(testKey, testValue, ttl);

      expect(mockLogger.debug).toHaveBeenCalledWith(expect.stringContaining(`Cache set for key ${testKey} with TTL ${ttl}s`));
      expect(await cacheService.get(testKey)).toEqual(testValue);
    });
  });

  describe('delete', () => {
    it('should return false when key does not exist', async () => {
      const result = await cacheService.delete('non-existent-key');
      expect(result).toBe(false);
    });

    it('should delete the key and return true when key exists', async () => {
      const testKey = 'test-key';
      const testValue = { name: 'test-value' };

      await cacheService.set(testKey, testValue);
      expect(await cacheService.get(testKey)).toEqual(testValue);

      const result = await cacheService.delete(testKey);
      expect(result).toBe(true);
      expect(await cacheService.get(testKey)).toBeNull();
    });
  });

  describe('clear', () => {
    it('should remove all cached items', async () => {
      // Set multiple items
      await cacheService.set('key1', 'value1');
      await cacheService.set('key2', 'value2');

      // Verify items are cached
      expect(await cacheService.get('key1')).toBe('value1');
      expect(await cacheService.get('key2')).toBe('value2');

      // Clear cache
      await cacheService.clear();

      // Verify items are removed
      expect(await cacheService.get('key1')).toBeNull();
      expect(await cacheService.get('key2')).toBeNull();
      expect(mockLogger.debug).toHaveBeenCalledWith('Cache cleared');
    });
  });

  describe('has', () => {
    it('should return false when key does not exist', () => {
      expect(cacheService.has('non-existent-key')).toBe(false);
    });

    it('should return true when key exists', async () => {
      const testKey = 'test-key';
      await cacheService.set(testKey, 'test-value');
      expect(cacheService.has(testKey)).toBe(true);
    });
  });

  describe('getMultiple', () => {
    it('should return mapped object with values for existing keys and null for non-existing keys', async () => {
      // Set some items
      await cacheService.set('key1', 'value1');
      await cacheService.set('key2', 'value2');

      // Get multiple keys including a non-existent one
      const result = await cacheService.getMultiple(['key1', 'key2', 'key3']);

      expect(result).toEqual({
        key1: 'value1',
        key2: 'value2',
        key3: null
      });
    });

    it('should return an empty object for empty keys array', async () => {
      const result = await cacheService.getMultiple([]);
      expect(result).toEqual({});
    });
  });

  describe('setMultiple', () => {
    it('should set multiple values with default TTL', async () => {
      const items = {
        key1: 'value1',
        key2: 'value2',
        key3: { complex: 'object' }
      };

      await cacheService.setMultiple(items);

      expect(await cacheService.get('key1')).toBe('value1');
      expect(await cacheService.get('key2')).toBe('value2');
      expect(await cacheService.get('key3')).toEqual({ complex: 'object' });
      expect(mockLogger.debug).toHaveBeenCalledWith(expect.stringContaining(`Cache set for ${Object.keys(items).length} keys`));
    });

    it('should set multiple values with custom TTL', async () => {
      const items = {
        key1: 'value1',
        key2: 'value2'
      };
      const ttl = 300;

      await cacheService.setMultiple(items, ttl);

      expect(await cacheService.get('key1')).toBe('value1');
      expect(await cacheService.get('key2')).toBe('value2');
      expect(mockLogger.debug).toHaveBeenCalledWith(expect.stringContaining(`Cache set for ${Object.keys(items).length} keys with TTL ${ttl}s`));
    });
  });

  describe('getStats', () => {
    it('should return cache statistics', async () => {
      // Set some items
      await cacheService.set('key1', 'value1');
      await cacheService.set('key2', 'value2');

      const stats = cacheService.getStats();

      // NodeCache stats should include these properties
      expect(stats).toHaveProperty('hits');
      expect(stats).toHaveProperty('misses');
      expect(stats).toHaveProperty('keys');
      expect(stats).toHaveProperty('ksize');
      expect(stats).toHaveProperty('vsize');
    });
  });

  describe('getKeys', () => {
    it('should return all cache keys', async () => {
      // Set some items
      await cacheService.set('key1', 'value1');
      await cacheService.set('key2', 'value2');

      const keys = cacheService.getKeys();

      expect(keys).toContain('key1');
      expect(keys).toContain('key2');
      expect(keys.length).toBe(2);
    });

    it('should return empty array when cache is empty', async () => {
      const keys = cacheService.getKeys();
      expect(keys).toEqual([]);
    });
  });
});
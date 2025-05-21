import * as dotenv from 'dotenv';
import { injectable } from 'inversify';

// Load environment variables from .env file
dotenv.config();

@injectable()
export class ConfigService {
  private readonly environment: string;
  private readonly requiredVars: string[];

  constructor() {
    this.environment = process.env.NODE_ENV || 'development';
    this.requiredVars = [
      'FRIDAY_API_URL',
      'FRIDAY_API_KEY',
      'MicrosoftAppId',
      'MicrosoftAppPassword'
    ];

    // Validate required variables
    this.validateConfig();
  }

  /**
   * Get a configuration value
   * @param key - The configuration key
   * @param defaultValue - Default value if the key is not found
   * @returns The configuration value or default value
   */
  public get<T = string>(key: string, defaultValue?: T): T {
    const value = process.env[key] as unknown as T;

    if (value === undefined) {
      if (defaultValue !== undefined) {
        return defaultValue;
      }

      throw new Error(`Configuration key '${key}' not found and no default value provided`);
    }

    return value;
  }

  /**
   * Get a boolean configuration value
   * @param key - The configuration key
   * @param defaultValue - Default value if the key is not found
   * @returns The configuration value as a boolean
   */
  public getBoolean(key: string, defaultValue?: boolean): boolean {
    const value = this.get<string>(key, defaultValue?.toString());

    if (typeof value === 'boolean') {
      return value;
    }

    if (typeof value === 'string') {
      const lowerValue = value.toLowerCase();
      return lowerValue === 'true' || lowerValue === '1' || lowerValue === 'yes';
    }

    return Boolean(value);
  }

  /**
   * Get a numeric configuration value
   * @param key - The configuration key
   * @param defaultValue - Default value if the key is not found
   * @returns The configuration value as a number
   */
  public getNumber(key: string, defaultValue?: number): number {
    const value = this.get<string>(key, defaultValue?.toString());

    if (typeof value === 'number') {
      return value;
    }

    const parsedValue = Number(value);

    if (isNaN(parsedValue)) {
      throw new Error(`Configuration key '${key}' value '${value}' is not a valid number`);
    }

    return parsedValue;
  }

  /**
   * Check if the current environment is production
   * @returns True if the current environment is production
   */
  public isProduction(): boolean {
    return this.environment === 'production';
  }

  /**
   * Check if the current environment is development
   * @returns True if the current environment is development
   */
  public isDevelopment(): boolean {
    return this.environment === 'development';
  }

  /**
   * Check if the current environment is test
   * @returns True if the current environment is test
   */
  public isTest(): boolean {
    return this.environment === 'test';
  }

  /**
   * Validate required configuration variables
   * @throws Error if any required variable is missing
   */
  private validateConfig(): void {
    // Skip validation in test environment
    if (this.isTest()) {
      return;
    }

    const missingVars = this.requiredVars.filter(key => !process.env[key]);

    if (missingVars.length > 0) {
      throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
    }
  }
}
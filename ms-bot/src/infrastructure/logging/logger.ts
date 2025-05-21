import { injectable, inject } from 'inversify';
import * as winston from 'winston';
import { ConfigService } from '../../config/config';

@injectable()
export class Logger {
  private readonly logger: winston.Logger;

  /**
   * @param configService - Configuration service
   */
  constructor(@inject(ConfigService) private readonly configService: ConfigService) {
    this.logger = this.createLogger();
  }

  /**
   * Create a Winston logger instance
   * @returns Winston logger instance
   */
  private createLogger(): winston.Logger {
    const logLevel = this.configService.get<string>('LOG_LEVEL', 'info');

    // Define the custom format
    const customFormat = winston.format.combine(
      winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
      winston.format.errors({ stack: true }),
      winston.format.printf(({ level, message, timestamp, stack, ...meta }) => {
        const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
        return `${timestamp} ${level.toUpperCase()}: ${message}${stack ? `\n${stack}` : ''}${metaStr}`;
      })
    );

    // Define transports
    const transports: winston.transport[] = [
      new winston.transports.Console({
        format: winston.format.combine(
          winston.format.colorize(),
          customFormat
        )
      })
    ];

    // Add file transports in production
    if (this.configService.isProduction()) {
      transports.push(
        new winston.transports.File({
          filename: 'logs/error.log',
          level: 'error',
          format: customFormat,
          maxsize: 10 * 1024 * 1024, // 10MB
          maxFiles: 5
        }),
        new winston.transports.File({
          filename: 'logs/combined.log',
          format: customFormat,
          maxsize: 10 * 1024 * 1024, // 10MB
          maxFiles: 5
        })
      );
    }

    // Create and return the logger
    return winston.createLogger({
      level: logLevel,
      levels: winston.config.npm.levels,
      transports,
      exitOnError: false
    });
  }

  /**
   * Log a message at the 'info' level
   * @param message - The message to log
   * @param meta - Additional metadata to log
   */
  public info(message: string, meta: Record<string, unknown> = {}): void {
    this.logger.info(message, meta);
  }

  /**
   * Log a message at the 'warn' level
   * @param message - The message to log
   * @param meta - Additional metadata to log
   */
  public warn(message: string, meta: Record<string, unknown> = {}): void {
    this.logger.warn(message, meta);
  }

  /**
   * Log a message at the 'error' level
   * @param message - The message to log
   * @param error - Error object or additional metadata
   */
  public error(message: string, error: Error | Record<string, unknown> = {}): void {
    if (error instanceof Error) {
      this.logger.error(message, { stack: error.stack });
    } else {
      this.logger.error(message, error);
    }
  }

  /**
   * Log a message at the 'debug' level
   * @param message - The message to log
   * @param meta - Additional metadata to log
   */
  public debug(message: string, meta: Record<string, unknown> = {}): void {
    this.logger.debug(message, meta);
  }

  /**
   * Log a message at the 'verbose' level
   * @param message - The message to log
   * @param meta - Additional metadata to log
   */
  public verbose(message: string, meta: Record<string, unknown> = {}): void {
    this.logger.verbose(message, meta);
  }

  /**
   * Create a child logger with additional default metadata
   * @param defaultMeta - Default metadata to include with every log
   * @returns A new logger instance with the default metadata
   */
  public child(defaultMeta: Record<string, unknown>): Logger {
    const childLogger = new Logger(this.configService);
    childLogger.logger = this.logger.child(defaultMeta);
    return childLogger;
  }
}
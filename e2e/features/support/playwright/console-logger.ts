import { Page } from 'playwright';
import { ConsoleMessage } from '@playwright/test';

export class ConsoleLogger {
  private logs: Array<{
    type: string;
    text: string;
    location: string | undefined;
    timestamp: string;
  }> = [];

  constructor(private readonly page: Page) {
    this.setupConsoleListener();
  }

  public getLogs() {
    return this.logs;
  }

  public getFormattedLogs(): string {
    return this.logs
      .map(
        (log) => `[${log.timestamp}] ${log.type.toUpperCase()}: ${log.text}${log.location ? ` (${log.location})` : ''}`,
      )
      .join('\n');
  }

  public clear() {
    this.logs = [];
  }

  private setupConsoleListener() {
    this.page.on('console', async (msg: ConsoleMessage) => {
      this.logs.push({
        type: msg.type(),
        text: msg.text(),
        location: msg.location().url,
        timestamp: new Date().toISOString(),
      });
    });
  }
}

import { Container } from 'inversify';

// Import services
import { ConfigService } from './config';
import { Logger } from '../infrastructure/logging/logger';
import { CacheService } from '../infrastructure/persistence/cacheService';
import { FridayServiceAdapter } from '../adapters/fridayServiceAdapter';
import { AzureDevOpsAdapter } from '../adapters/azureDevOpsAdapter';
import { TeamsAdapter } from '../adapters/teamsAdapter';
import { MetricsBot } from '../bot/botActivity';
import { CardBuilder } from '../bot/adaptiveCards/cardBuilder';
import { MainDialog } from '../bot/botDialogs';
import { GetTestMetricsUseCase } from '../domain/useCases/getTestMetrics';
import { BotFrameworkAdapter, ConversationState, UserState } from 'botbuilder';

// Define symbols for dependencies that don't have classes
export const DIALOG_ID = {
  MAIN_DIALOG: Symbol.for('MainDialog')
};

/**
 * Register all services with the DI container
 * @param container - The inversify container
 */
export function registerServices(container: Container): void {
  // Infrastructure
  container.bind<ConfigService>(ConfigService).toSelf().inSingletonScope();
  container.bind<Logger>(Logger).toSelf().inSingletonScope();
  container.bind<CacheService>(CacheService).toSelf().inSingletonScope();

  // Adapters
  container.bind<FridayServiceAdapter>(FridayServiceAdapter).toSelf().inSingletonScope();
  container.bind<AzureDevOpsAdapter>(AzureDevOpsAdapter).toSelf().inSingletonScope();
  container.bind<TeamsAdapter>(TeamsAdapter).toSelf().inSingletonScope();

  // Bot
  container.bind<CardBuilder>(CardBuilder).toSelf().inSingletonScope();
  container.bind<MainDialog>(DIALOG_ID.MAIN_DIALOG).to(MainDialog).inSingletonScope();
  container.bind<MetricsBot>(MetricsBot).toSelf().inSingletonScope();

  // Domain
  container.bind<GetTestMetricsUseCase>(GetTestMetricsUseCase).toSelf().inSingletonScope();
}
// Import required packages
import 'dotenv/config';
import 'reflect-metadata';
import * as path from 'path';
import * as express from 'express';
import { Container } from 'inversify';
import { BotFrameworkAdapter, MemoryStorage, ConversationState, UserState, TurnContext } from 'botbuilder';

// Import our modules
import { Logger } from './infrastructure/logging/logger';
import { ConfigService } from './config/config';
import { MetricsBot } from './bot/botActivity';
import { registerServices } from './config/serviceRegistry';

// Create server
const app = express();
const PORT = process.env.PORT || 3978;

// Setup dependency injection container
const container = new Container();
registerServices(container);

// Get services from container
const logger = container.get<Logger>(Logger);
const config = container.get<ConfigService>(ConfigService);

// Create adapter (with error handling)
const adapter = new BotFrameworkAdapter({
  appId: config.get('MicrosoftAppId'),
  appPassword: config.get('MicrosoftAppPassword')
});

// Define error handler
adapter.onTurnError = async (context: TurnContext, error: Error) => {
  logger.error(`[onTurnError] Error: ${error.message}`, error);

  // Send a message to the user
  await context.sendActivity('The bot encountered an error.');

  // Clear conversation state
  const conversationState = container.get<ConversationState>(ConversationState);
  await conversationState.delete(context);
};

// Create conversation and user state
const memoryStorage = new MemoryStorage();
const conversationState = new ConversationState(memoryStorage);
const userState = new UserState(memoryStorage);

// Register states in container
container.bind<ConversationState>(ConversationState).toConstantValue(conversationState);
container.bind<UserState>(UserState).toConstantValue(userState);

// Create the bot instance
const bot = container.get<MetricsBot>(MetricsBot);

// Listen for incoming requests
app.post('/api/messages', (req, res) => {
  adapter.processActivity(req, res, async (context) => {
    await bot.run(context);
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.send({ status: 'healthy' });
});

// Serve static files
app.use(express.static(path.join(__dirname, '../public')));

// Start the server
app.listen(PORT, () => {
  logger.info(`Server is running on port ${PORT}`);
  logger.info(`Get the Emulator: https://aka.ms/botframework-emulator`);
  logger.info(`To talk to your bot, send requests to: http://localhost:${PORT}/api/messages`);
});

// Handle shutdown gracefully
process.on('SIGINT', () => {
  logger.info('Server shutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  logger.info('Server shutting down...');
  process.exit(0);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error(`Unhandled Rejection at: ${promise}, reason: ${reason}`);
});

process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception:', error);
  process.exit(1);
});
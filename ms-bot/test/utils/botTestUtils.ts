import { Activity, TestAdapter, TurnContext } from 'botbuilder';
import { Container } from 'inversify';
import { MetricsBot } from '../../src/bot/botActivity';
import { registerServices } from '../../src/config/serviceRegistry';

/**
 * Create a TestAdapter instance for testing the bot
 * @returns TestAdapter instance
 */
export function createTestAdapter(): TestAdapter {
  return new TestAdapter((context) => Promise.resolve());
}

/**
 * Setup a test environment with dependency injection
 * @returns Object with test dependencies
 */
export function setupBotTestEnv() {
  // Create a container
  const container = new Container();

  // Register services
  registerServices(container);

  // Get the bot instance
  const bot = container.get<MetricsBot>(MetricsBot);

  // Create a test adapter
  const testAdapter = createTestAdapter();

  // Set the bot logic for the test adapter
  testAdapter.onTurn(async (context) => {
    await bot.run(context);
  });

  return {
    container,
    bot,
    testAdapter
  };
}

/**
 * Wait for a specified time
 * @param ms Milliseconds to wait
 * @returns Promise that resolves after the specified time
 */
export function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create a user message activity
 * @param text Message text
 * @returns User message activity
 */
export function createUserActivity(text: string): Partial<Activity> {
  return {
    type: 'message',
    text,
    from: {
      id: 'user1',
      name: 'User'
    },
    recipient: {
      id: 'bot1',
      name: 'Bot'
    },
    conversation: {
      id: 'convo1'
    },
    channelId: 'test',
    serviceUrl: 'https://test.com'
  };
}

/**
 * Create a card action activity
 * @param action Action name
 * @param data Additional data
 * @returns Card action activity
 */
export function createCardActionActivity(action: string, data: any = {}): Partial<Activity> {
  return {
    type: 'message',
    value: {
      action,
      ...data
    },
    from: {
      id: 'user1',
      name: 'User'
    },
    recipient: {
      id: 'bot1',
      name: 'Bot'
    },
    conversation: {
      id: 'convo1'
    },
    channelId: 'test',
    serviceUrl: 'https://test.com'
  };
}

/**
 * Create a conversation update activity (bot added to conversation)
 * @returns Conversation update activity
 */
export function createBotAddedActivity(): Partial<Activity> {
  return {
    type: 'conversationUpdate',
    membersAdded: [
      {
        id: 'bot1',
        name: 'Bot'
      },
      {
        id: 'user1',
        name: 'User'
      }
    ],
    from: {
      id: 'user1',
      name: 'User'
    },
    recipient: {
      id: 'bot1',
      name: 'Bot'
    },
    conversation: {
      id: 'convo1'
    },
    channelId: 'test',
    serviceUrl: 'https://test.com'
  };
}

/**
 * Assert that a response contains a card of a specific type
 * @param activity Response activity
 * @param cardContentType Expected card content type
 * @returns Boolean indicating if the card type matches
 */
export function hasCardType(activity: Partial<Activity>, cardContentType: string): boolean {
  return activity.attachments?.some(attachment =>
    attachment.contentType === cardContentType
  ) ?? false;
}

/**
 * Assert that a response contains an adaptive card
 * @param activity Response activity
 * @returns Boolean indicating if an adaptive card is present
 */
export function hasAdaptiveCard(activity: Partial<Activity>): boolean {
  return hasCardType(activity, 'application/vnd.microsoft.card.adaptive');
}

/**
 * Get card content from an activity
 * @param activity Response activity
 * @returns Card content or null if no card is present
 */
export function getCardContent(activity: Partial<Activity>): any {
  const attachment = activity.attachments?.find(a =>
    a.contentType === 'application/vnd.microsoft.card.adaptive'
  );

  return attachment?.content || null;
}
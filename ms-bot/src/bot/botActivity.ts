import { ActivityHandler, MessageFactory, TurnContext, TeamsActivityHandler } from 'botbuilder';
import { injectable, inject } from 'inversify';
import { DialogSet, DialogTurnStatus } from 'botbuilder-dialogs';

import { Logger } from '../infrastructure/logging/logger';
import { GetTestMetricsUseCase } from '../domain/useCases/getTestMetrics';
import { CardBuilder } from './adaptiveCards/cardBuilder';
import { MainDialog } from './botDialogs';
import { DIALOG_ID } from '../config/serviceRegistry';
import { TeamsAdapter } from '../adapters/teamsAdapter';
import { BotFrameworkAdapter, ConversationState, UserState } from 'botbuilder';

@injectable()
export class MetricsBot extends TeamsActivityHandler {
  private readonly dialogState: any;
  private readonly dialogSet: DialogSet;

  /**
   * @param logger - Logger instance
   * @param conversationState - Conversation state
   * @param userState - User state
   * @param getTestMetricsUseCase - Use case for fetching metrics
   * @param cardBuilder - Adaptive card builder
   * @param teamsAdapter - Teams adapter
   * @param mainDialog - Main dialog
   */
  constructor(
    @inject(Logger) private readonly logger: Logger,
    @inject(ConversationState) private readonly conversationState: ConversationState,
    @inject(UserState) private readonly userState: UserState,
    @inject(GetTestMetricsUseCase) private readonly getTestMetricsUseCase: GetTestMetricsUseCase,
    @inject(CardBuilder) private readonly cardBuilder: CardBuilder,
    @inject(TeamsAdapter) private readonly teamsAdapter: TeamsAdapter,
    @inject(DIALOG_ID.MAIN_DIALOG) private readonly mainDialog: MainDialog
  ) {
    super();

    this.dialogState = this.conversationState.createProperty('DialogState');
    this.dialogSet = new DialogSet(this.dialogState);
    this.dialogSet.add(this.mainDialog);

    // Handle message activity
    this.onMessage(async (context, next) => {
      this.logger.info('Processing message activity.');

      // Extract action from card submission
      if (context.activity.value?.action) {
        await this.handleCardAction(context, context.activity.value);
      } else {
        // Run the dialog system
        const dialogContext = await this.dialogSet.createContext(context);
        const results = await dialogContext.continueDialog();

        if (results.status === DialogTurnStatus.empty) {
          await dialogContext.beginDialog(this.mainDialog.id);
        }
      }

      await next();
    });

    // Handle conversation update activity
    this.onConversationUpdate(async (context, next) => {
      if (context.activity.membersAdded && context.activity.membersAdded.length > 0) {
        for (const member of context.activity.membersAdded) {
          if (member.id !== context.activity.recipient.id) {
            await this.sendWelcomeMessage(context);
          }
        }
      }

      await next();
    });

    // Add other event handlers
    this.onDialog(async (context, next) => {
      // Save state changes at the end of the turn
      await this.conversationState.saveChanges(context);
      await this.userState.saveChanges(context);

      await next();
    });
  }

  /**
   * Send welcome message when the bot is added to a conversation
   * @param context - The turn context
   */
  private async sendWelcomeMessage(context: TurnContext): Promise<void> {
    this.logger.info('Sending welcome message');

    const welcomeCard = this.cardBuilder.createWelcomeCard();
    await context.sendActivity({
      attachments: [welcomeCard]
    });
  }

  /**
   * Handle action from adaptive card
   * @param context - The turn context
   * @param value - The submitted card value
   */
  private async handleCardAction(context: TurnContext, value: any): Promise<void> {
    const action = value.action;
    const projectId = value.projectId || 'demo-project';
    const buildNumber = value.buildNumber;

    try {
      switch (action) {
        case 'showRecentMetrics':
        case 'showLatestMetrics':
          await this.handleShowMetrics(context, projectId);
          break;

        case 'showFailedTests':
          await this.handleFailedTests(context, projectId, buildNumber);
          break;

        case 'showTrendCharts':
          await this.handleTrendCharts(context, projectId);
          break;

        case 'comparePreviousBuild':
          await this.handleComparePreviousBuild(context, projectId, buildNumber);
          break;

        default:
          await context.sendActivity(`I don't know how to handle the action: ${action}`);
      }
    } catch (error) {
      this.logger.error(`Error handling card action: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error processing your request.');
    }
  }

  /**
   * Handle 'Show Metrics' action
   * @param context - The turn context
   * @param projectId - Project ID
   */
  private async handleShowMetrics(context: TurnContext, projectId: string): Promise<void> {
    try {
      // Get the latest metrics
      const report = await this.getTestMetricsUseCase.getLatestMetrics(projectId);

      // Create and send the metrics card
      const card = this.cardBuilder.createMetricsSummaryCard(report);
      await context.sendActivity({ attachments: [card] });
    } catch (error) {
      this.logger.error(`Error handling show metrics: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error getting the metrics.');
    }
  }

  /**
   * Handle 'Failed Tests' action
   * @param context - The turn context
   * @param projectId - Project ID
   * @param buildNumber - Build number
   */
  private async handleFailedTests(context: TurnContext, projectId: string, buildNumber: string): Promise<void> {
    try {
      // Get the report for the build
      const report = await this.getTestMetricsUseCase.getMetricsForBuild(projectId, buildNumber);

      // Get failed tests
      const failedTests = await this.getTestMetricsUseCase.getFailedTests(projectId, buildNumber);

      if (failedTests.length === 0) {
        await context.sendActivity(`Good news! There are no failed tests in build ${buildNumber}.`);
      } else {
        // Create and send the failed tests card
        const card = this.cardBuilder.createFailedTestsCard(report, failedTests);
        await context.sendActivity({ attachments: [card] });
      }
    } catch (error) {
      this.logger.error(`Error handling failed tests: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error getting the failed tests.');
    }
  }

  /**
   * Handle 'Trend Charts' action
   * @param context - The turn context
   * @param projectId - Project ID
   */
  private async handleTrendCharts(context: TurnContext, projectId: string): Promise<void> {
    try {
      // Get the latest metrics and historical data
      const [latestReport, historicalData] = await Promise.all([
        this.getTestMetricsUseCase.getLatestMetrics(projectId),
        this.getTestMetricsUseCase.getHistoricalMetrics(projectId, 10)
      ]);

      // Create and send the chart card
      const card = this.cardBuilder.createMetricsChartCard(latestReport, historicalData);
      await context.sendActivity({ attachments: [card] });
    } catch (error) {
      this.logger.error(`Error handling trend charts: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error generating the trend charts.');
    }
  }

  /**
   * Handle 'Compare Previous Build' action
   * @param context - The turn context
   * @param projectId - Project ID
   * @param buildNumber - Current build number
   */
  private async handleComparePreviousBuild(context: TurnContext, projectId: string, buildNumber: string): Promise<void> {
    try {
      // Get historical data
      const historicalData = await this.getTestMetricsUseCase.getHistoricalMetrics(projectId, 5);

      if (historicalData.length < 2) {
        await context.sendActivity('Sorry, I need at least two builds to compare.');
        return;
      }

      // Find the current build and the previous one
      const currentBuildIndex = historicalData.findIndex(report => report.buildNumber === buildNumber);
      let previousBuildIndex: number;

      if (currentBuildIndex === -1 || currentBuildIndex === historicalData.length - 1) {
        // Current build not found or is the oldest, use the two most recent builds
        previousBuildIndex = 1;
        buildNumber = historicalData[0].buildNumber;
      } else {
        previousBuildIndex = currentBuildIndex + 1;
      }

      // Get the comparison
      const result = await this.getTestMetricsUseCase.compareBuilds(
        projectId,
        buildNumber,
        historicalData[previousBuildIndex].buildNumber
      );

      // Create and send the comparison card
      const card = this.cardBuilder.createBuildComparisonCard(result);
      await context.sendActivity({ attachments: [card] });
    } catch (error) {
      this.logger.error(`Error handling compare previous build: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error comparing the builds.');
    }
  }

  /**
   * Parse command text from a message
   * @param text - Message text
   * @returns Parsed command and arguments
   */
  private parseCommand(text: string): { command: string; args: string[] } {
    const trimmedText = text.trim();
    const parts = trimmedText.split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1);

    return { command, args };
  }

  /**
   * Process a command from the user
   * @param context - The turn context
   * @param command - The command
   * @param args - Command arguments
   */
  private async processCommand(context: TurnContext, command: string, args: string[]): Promise<void> {
    try {
      switch (command) {
        case 'help':
          await this.sendWelcomeMessage(context);
          break;

        case 'metrics':
        case 'show':
          const projectId = args[0] || 'demo-project';
          await this.handleShowMetrics(context, projectId);
          break;

        case 'failed':
        case 'failures':
          if (args.length < 2) {
            await context.sendActivity('Please specify a project and build number. Example: failed demo-project build-123');
            return;
          }
          await this.handleFailedTests(context, args[0], args[1]);
          break;

        case 'trends':
        case 'charts':
          const trendProjectId = args[0] || 'demo-project';
          await this.handleTrendCharts(context, trendProjectId);
          break;

        case 'compare':
          if (args.length < 3) {
            await context.sendActivity('Please specify a project and two build numbers. Example: compare demo-project build-123 build-124');
            return;
          }
          await this.getTestMetricsUseCase.compareBuilds(args[0], args[1], args[2]);
          break;

        default:
          await context.sendActivity(`I don't understand the command: ${command}. Try 'help' to see what I can do.`);
      }
    } catch (error) {
      this.logger.error(`Error processing command: ${(error as Error).message}`, error as Error);
      await context.sendActivity('Sorry, I encountered an error processing your command.');
    }
  }

  /**
   * Helper method to run the bot with error handling
   * @param context - The turn context
   */
  public async run(context: TurnContext): Promise<void> {
    try {
      await super.run(context);
    } catch (error) {
      this.logger.error(`Error running bot: ${(error as Error).message}`, error as Error);
      await context.sendActivity('An error occurred while processing your request.');
    }
  }

  /**
   * Handle Teams-specific events
   */
  protected override async onTeamsTaskModuleFetch(context: TurnContext, taskModuleRequest: any): Promise<any> {
    this.logger.info('Teams task module fetch event received');
    // Handle task module fetch
    return {
      task: {
        type: 'continue',
        value: {
          title: 'Friday Metrics',
          url: 'https://friday-metrics-bot.azurewebsites.net/taskModule.html',
          width: 'large',
          height: 'large'
        }
      }
    };
  }

  protected override async onTeamsTaskModuleSubmit(context: TurnContext, taskModuleRequest: any): Promise<any> {
    this.logger.info('Teams task module submit event received', { data: taskModuleRequest.data });

    // Handle task module submit based on the data
    if (taskModuleRequest.data.action) {
      await this.handleCardAction(context, taskModuleRequest.data);
    }

    return {
      task: {
        type: 'message',
        value: 'Task completed successfully.'
      }
    };
  }
}
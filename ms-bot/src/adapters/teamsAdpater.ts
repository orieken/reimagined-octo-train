import { injectable, inject } from 'inversify';
import {
  TurnContext,
  TeamsInfo,
  BotAdapter,
  ConversationReference,
  CardFactory,
  Attachment
} from 'botbuilder';
import { Logger } from '../infrastructure/logging/logger';

/**
 * Interface for connector information
 */
export interface ConnectorInfo {
  id: string;
  conversationReference: Partial<ConversationReference>;
  projectId: string;
  installedBy: string;
  installedAt: string;
}

@injectable()
export class TeamsAdapter {
  /**
   * @param logger - Logger instance
   */
  constructor(@inject(Logger) private readonly logger: Logger) {}

  /**
   * Get the team info for a conversation
   * @param context - Turn context
   * @returns Promise resolving to team info object
   */
  public async getTeamInfo(context: TurnContext): Promise<any | null> {
    try {
      if (!this.isTeamConversation(context)) {
        this.logger.info('Not a team conversation, returning null for team info');
        return null;
      }

      const teamDetails = await TeamsInfo.getTeamDetails(context);
      return teamDetails;
    } catch (error) {
      this.logger.error(`Error getting team info: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Get members of a team conversation
   * @param context - Turn context
   * @returns Promise resolving to an array of team members
   */
  public async getTeamMembers(context: TurnContext): Promise<any[]> {
    try {
      if (!this.isTeamConversation(context)) {
        this.logger.info('Not a team conversation, returning empty array for team members');
        return [];
      }

      const teamMembers = await TeamsInfo.getMembers(context);
      return teamMembers;
    } catch (error) {
      this.logger.error(`Error getting team members: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Check if the conversation is in a team
   * @param context - Turn context
   * @returns True if the conversation is in a team
   */
  public isTeamConversation(context: TurnContext): boolean {
    return Boolean(
      context.activity.channelData &&
      context.activity.channelData.team &&
      context.activity.channelData.team.id
    );
  }

  /**
   * Send a proactive message to a conversation
   * @param serviceUrl - Service URL
   * @param conversationId - Conversation ID
   * @param message - Message to send (string or activity object)
   * @param adapter - Bot adapter instance
   * @returns Promise that resolves when the message is sent
   */
  public async sendProactiveMessage(
    serviceUrl: string,
    conversationId: string,
    message: string | Attachment | any,
    adapter: BotAdapter
  ): Promise<void> {
    try {
      // Create a reference to the conversation
      const conversationReference: Partial<ConversationReference> = {
        serviceUrl: serviceUrl,
        conversation: {
          id: conversationId
        }
      };

      // Create a turn context and send the message
      await adapter.continueConversation(conversationReference, async (context) => {
        if (typeof message === 'string') {
          await context.sendActivity(message);
        } else if (message.contentType) {
          // It's an attachment
          await context.sendActivity({ attachments: [message] });
        } else {
          // It's a complete activity
          await context.sendActivity(message);
        }
      });

      this.logger.info(`Sent proactive message to conversation ${conversationId}`);
    } catch (error) {
      this.logger.error(`Error sending proactive message: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Install a connector for proactive notifications
   * @param context - Turn context
   * @param projectId - Project ID to associate with the team
   * @returns Promise resolving to the installed connector info
   */
  public async installConnector(context: TurnContext, projectId: string): Promise<ConnectorInfo> {
    try {
      // Store the conversation reference for future proactive messages
      const reference = TurnContext.getConversationReference(context.activity);

      // Create connector info
      const connectorInfo: ConnectorInfo = {
        id: `${reference.conversation?.id}-${projectId}`,
        conversationReference: reference,
        projectId: projectId,
        installedBy: context.activity.from?.id || 'unknown',
        installedAt: new Date().toISOString()
      };

      this.logger.info(`Installed connector for project ${projectId} in conversation ${reference.conversation?.id}`);

      return connectorInfo;
    } catch (error) {
      this.logger.error(`Error installing connector: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Uninstall a connector
   * @param context - Turn context
   * @param projectId - Project ID to uninstall
   * @returns Promise resolving to true if successful
   */
  public async uninstallConnector(context: TurnContext, projectId: string): Promise<boolean> {
    try {
      const reference = TurnContext.getConversationReference(context.activity);

      // In a real implementation, you would remove the reference from a persistent store

      this.logger.info(`Uninstalled connector for project ${projectId} in conversation ${reference.conversation?.id}`);

      return true;
    } catch (error) {
      this.logger.error(`Error uninstalling connector: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Get user information from Teams context
   * @param context - Turn context
   * @returns Promise resolving to user information
   */
  public async getUserInfo(context: TurnContext): Promise<any> {
    try {
      const member = await TeamsInfo.getMember(context, context.activity.from?.id || '');
      return member;
    } catch (error) {
      this.logger.error(`Error getting user info: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Send an adaptive card to the conversation
   * @param context - Turn context
   * @param card - Adaptive card JSON
   * @returns Promise that resolves when the card is sent
   */
  public async sendAdaptiveCard(context: TurnContext, card: any): Promise<void> {
    try {
      const adaptiveCard = CardFactory.adaptiveCard(card);
      await context.sendActivity({ attachments: [adaptiveCard] });
    } catch (error) {
      this.logger.error(`Error sending adaptive card: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }

  /**
   * Update an adaptive card in the conversation
   * @param context - Turn context
   * @param activityId - ID of the activity containing the card
   * @param card - Updated adaptive card JSON
   * @returns Promise that resolves when the card is updated
   */
  public async updateAdaptiveCard(context: TurnContext, activityId: string, card: any): Promise<void> {
    try {
      const adaptiveCard = CardFactory.adaptiveCard(card);
      await context.updateActivity({
        id: activityId,
        attachments: [adaptiveCard]
      });
    } catch (error) {
      this.logger.error(`Error updating adaptive card: ${(error as Error).message}`, error as Error);
      throw error;
    }
  }
}
import { injectable, inject } from 'inversify';
import * as azdev from 'azure-devops-node-api';
import { IWorkItemTrackingApi } from 'azure-devops-node-api/WorkItemTrackingApi';
import { IBuildApi } from 'azure-devops-node-api/BuildApi';
import { ITestApi } from 'azure-devops-node-api/TestApi';
import { WorkItem, WorkItemExpand } from 'azure-devops-node-api/interfaces/WorkItemTrackingInterfaces';
import { BuildResult, Build } from 'azure-devops-node-api/interfaces/BuildInterfaces';
import { TestRun, TestCaseResult } from 'azure-devops-node-api/interfaces/TestInterfaces';
import { ConfigService } from '../config/config';
import { Logger } from '../infrastructure/logging/logger';

/**
 * Azure DevOps build information
 */
export interface AzureDevOpsBuildInfo {
  id: string;
  buildNumber: string;
  status: string;
  result: string;
  startTime: Date | null;
  finishTime: Date | null;
  url: string;
  sourceBranch: string;
  sourceVersion: string;
  requestedBy: string;
}

/**
 * Azure DevOps work item details
 */
export interface AzureDevOpsWorkItem {
  id: number;
  url: string;
  title: string;
  state: string;
  type: string;
  assignedTo?: string;
}

/**
 * Azure DevOps test run details
 */
export interface AzureDevOpsTestRun {
  id: number;
  name: string;
  url: string;
  state: string;
  passedTests: number;
  failedTests: number;
  totalTests: number;
  startDate: Date | null;
  completeDate: Date | null;
}

@injectable()
export class AzureDevOpsAdapter {
  private connection: azdev.WebApi | null = null;
  private workItemClient: IWorkItemTrackingApi | null = null;
  private buildClient: IBuildApi | null = null;
  private testClient: ITestApi | null = null;

  private readonly orgUrl: string;
  private readonly personalAccessToken: string;
  private readonly project: string;

  /**
   * @param configService - Configuration service
   * @param logger - Logger instance
   */
  constructor(
    @inject(ConfigService) private readonly configService: ConfigService,
    @inject(Logger) private readonly logger: Logger
  ) {
    this.orgUrl = this.configService.get<string>('AZURE_DEVOPS_ORG_URL');
    this.personalAccessToken = this.configService.get<string>('AZURE_DEVOPS_PAT');
    this.project = this.configService.get<string>('AZURE_DEVOPS_PROJECT');

    this.initializeConnection();
  }

  /**
   * Initialize the Azure DevOps connection
   */
  private async initializeConnection(): Promise<void> {
    try {
      const authHandler = azdev.getPersonalAccessTokenHandler(this.personalAccessToken);
      this.connection = new azdev.WebApi(this.orgUrl, authHandler);

      // Initialize clients
      this.workItemClient = await this.connection.getWorkItemTrackingApi();
      this.buildClient = await this.connection.getBuildApi();
      this.testClient = await this.connection.getTestApi();

      this.logger.info('Azure DevOps connection initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize Azure DevOps connection', error as Error);
      throw new Error(`Failed to initialize Azure DevOps connection: ${(error as Error).message}`);
    }
  }

  /**
   * Get build information by build ID
   * @param buildId - Azure DevOps build ID
   * @returns Build information
   */
  public async getBuildById(buildId: string): Promise<AzureDevOpsBuildInfo> {
    try {
      if (!this.buildClient) {
        await this.initializeConnection();
      }

      if (!this.buildClient) {
        throw new Error('Build client not initialized');
      }

      const build = await this.buildClient.getBuild(this.project, parseInt(buildId));

      return this.mapToBuildInfo(build);
    } catch (error) {
      this.logger.error(`Error fetching build by ID ${buildId}`, error as Error);
      throw new Error(`Failed to fetch build information: ${(error as Error).message}`);
    }
  }

  /**
   * Create a work item for a failed test
   * @param title - Work item title
   * @param description - Work item description
   * @param buildId - Related build ID
   * @param testName - Name of the failed test
   * @returns Created work item
   */
  public async createWorkItemForFailedTest(
    title: string,
    description: string,
    buildId: string,
    testName: string
  ): Promise<AzureDevOpsWorkItem> {
    try {
      if (!this.workItemClient) {
        await this.initializeConnection();
      }

      if (!this.workItemClient) {
        throw new Error('Work item client not initialized');
      }

      const patchDocument = [
        {
          op: 'add',
          path: '/fields/System.Title',
          value: title
        },
        {
          op: 'add',
          path: '/fields/System.Description',
          value: description
        },
        {
          op: 'add',
          path: '/fields/System.Tags',
          value: 'Failed Test,Automated Test'
        },
        {
          op: 'add',
          path: '/fields/System.History',
          value: `Created from failed test "${testName}" in build ${buildId}`
        }
      ];

      const workItem = await this.workItemClient.createWorkItem(
        undefined,
        patchDocument,
        this.project,
        'Bug'
      );

      return {
        id: workItem.id as number,
        url: workItem.url as string,
        title: workItem.fields?.['System.Title'] as string,
        state: workItem.fields?.['System.State'] as string,
        type: workItem.fields?.['System.WorkItemType'] as string,
        assignedTo: workItem.fields?.['System.AssignedTo'] as string
      };
    } catch (error) {
      this.logger.error('Error creating work item for failed test', error as Error);
      throw new Error(`Failed to create work item: ${(error as Error).message}`);
    }
  }

  /**
   * Get test runs associated with a build
   * @param buildId - Azure DevOps build ID
   * @returns Test runs for the build
   */
  public async getTestRunsForBuild(buildId: string): Promise<AzureDevOpsTestRun[]> {
    try {
      if (!this.testClient) {
        await this.initializeConnection();
      }

      if (!this.testClient) {
        throw new Error('Test client not initialized');
      }

      const testRuns = await this.testClient.getTestRuns(
        this.project,
        undefined, // owner
        undefined, // tester
        parseInt(buildId)
      );

      return testRuns.map(run => ({
        id: run.id as number,
        name: run.name as string,
        url: run.url as string,
        state: run.state as string,
        passedTests: run.passedTests as number,
        failedTests: run.failedTests as number,
        totalTests: run.totalTests as number,
        startDate: run.startDate ? new Date(run.startDate) : null,
        completeDate: run.completeDate ? new Date(run.completeDate) : null
      }));
    } catch (error) {
      this.logger.error(`Error fetching test runs for build ${buildId}`, error as Error);
      throw new Error(`Failed to fetch test runs: ${(error as Error).message}`);
    }
  }

  /**
   * Map Azure DevOps Build to BuildInfo
   * @param build - Azure DevOps Build object
   * @returns Simplified build info
   */
  private mapToBuildInfo(build: Build): AzureDevOpsBuildInfo {
    return {
      id: build.id?.toString() || '',
      buildNumber: build.buildNumber || '',
      status: build.status || '',
      result: build.result || '',
      startTime: build.startTime ? new Date(build.startTime) : null,
      finishTime: build.finishTime ? new Date(build.finishTime) : null,
      url: build.url || '',
      sourceBranch: build.sourceBranch || '',
      sourceVersion: build.sourceVersion || '',
      requestedBy: build.requestedBy?.displayName || ''
    };
  }
}
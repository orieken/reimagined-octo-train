import { CardBuilder } from '../../../../src/bot/adaptiveCards/cardBuilder';
import { CardFactory } from 'botbuilder';
import { TestReport } from '../../../../src/domain/entities/testReport';
import { TestMetric, TestStatus } from '../../../../src/domain/entities/testMetric';
import { AzureDevOpsBuildInfo } from '../../../../src/adapters/azureDevOpsAdapter';

// Mock CardFactory.adaptiveCard
jest.mock('botbuilder', () => ({
  CardFactory: {
    adaptiveCard: jest.fn().mockImplementation((cardJson) => ({
      contentType: 'application/vnd.microsoft.card.adaptive',
      content: cardJson
    }))
  }
}));

describe('CardBuilder', () => {
  let cardBuilder: CardBuilder;

  // Sample test report
  const testReport: TestReport = new TestReport({
    id: 'report-1',
    projectId: 'project-1',
    projectName: 'Test Project',
    buildNumber: 'build-123',
    buildUrl: 'https://example.com/builds/123',
    timestamp: new Date('2023-05-15T14:30:00Z'),
    totalTests: 100,
    passedTests: 90,
    failedTests: 5,
    skippedTests: 5,
    duration: 5000,
    azureDevOpsBuildId: 'azdo-build-123'
  });

  // Sample test metrics
  const testMetrics: TestMetric[] = [
    new TestMetric({
      id: 'test-1',
      name: 'Failed Test 1',
      status: TestStatus.Failed,
      duration: 500,
      className: 'com.example.TestClass1',
      projectId: 'project-1',
      buildNumber: 'build-123',
      timestamp: new Date('2023-05-15T14:29:00Z'),
      errorMessage: 'Assertion failed: expected true but was false'
    }),
    new TestMetric({
      id: 'test-2',
      name: 'Failed Test 2',
      status: TestStatus.Failed,
      duration: 300,
      className: 'com.example.TestClass2',
      projectId: 'project-1',
      buildNumber: 'build-123',
      timestamp: new Date('2023-05-15T14:29:30Z'),
      errorMessage: 'NullPointerException'
    })
  ];

  // Sample build info
  const buildInfo: AzureDevOpsBuildInfo = {
    id: 'azdo-build-123',
    buildNumber: 'build-123',
    status: 'completed',
    result: 'succeeded',
    startTime: new Date('2023-05-15T14:00:00Z'),
    finishTime: new Date('2023-05-15T14:30:00Z'),
    url: 'https://dev.azure.com/org/project/_build/results?buildId=123',
    sourceBranch: 'refs/heads/main',
    sourceVersion: '1234567890abcdef',
    requestedBy: 'John Doe'
  };

  // Sample historical data
  const historicalData: TestReport[] = [
    testReport,
    new TestReport({
      id: 'report-2',
      projectId: 'project-1',
      projectName: 'Test Project',
      buildNumber: 'build-122',
      buildUrl: 'https://example.com/builds/122',
      timestamp: new Date('2023-05-14T10:30:00Z'),
      totalTests: 98,
      passedTests: 85,
      failedTests: 8,
      skippedTests: 5,
      duration: 5200
    })
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    cardBuilder = new CardBuilder();
  });

  describe('createWelcomeCard', () => {
    it('should create a welcome card with correct data', () => {
      const card = cardBuilder.createWelcomeCard();

      expect(card.contentType).toBe('application/vnd.microsoft.card.adaptive');
      expect(CardFactory.adaptiveCard).toHaveBeenCalled();

      const content = card.content;
      expect(content).toHaveProperty('type', 'AdaptiveCard');
      expect(content).toHaveProperty('version');
      expect(content).toHaveProperty('body');
      expect(content).toHaveProperty('actions');

      // Check the title is present in the body
      const titleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Large' && item.weight === 'Bolder'
      );
      expect(titleBlock).toBeTruthy();
      expect(titleBlock.text).toContain('Friday Metrics Bot');
    });
  });

  describe('createMetricsSummaryCard', () => {
    it('should create a metrics summary card with correct data', () => {
      const card = cardBuilder.createMetricsSummaryCard(testReport);

      expect(card.contentType).toBe('application/vnd.microsoft.card.adaptive');
      expect(CardFactory.adaptiveCard).toHaveBeenCalled();

      const content = card.content;
      expect(content).toHaveProperty('type', 'AdaptiveCard');

      // Check title contains project name
      const titleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Large' && item.weight === 'Bolder'
      );
      expect(titleBlock).toBeTruthy();
      expect(titleBlock.text).toContain(testReport.projectName);

      // Check subtitle contains build number
      const subtitleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Medium'
      );
      expect(subtitleBlock).toBeTruthy();
      expect(subtitleBlock.text).toContain(testReport.buildNumber);

      // Check that the pass rate is calculated correctly (90%)
      const passRateContainer = content.body.find((item: any) =>
        item.type === 'ColumnSet'
      )?.columns.find((col: any) => col.width === 'auto')?.items.find((item: any) =>
        item.type === 'Container'
      );

      expect(passRateContainer).toBeTruthy();
      expect(passRateContainer.style).toBe('good'); // > 90% should be green

      // Check that actions are present
      expect(content.actions.length).toBeGreaterThan(0);
      expect(content.actions.some((action: any) => action.title === 'View Build Details')).toBeTruthy();
    });

    it('should include Azure DevOps information when buildInfo is provided', () => {
      const card = cardBuilder.createMetricsSummaryCard(testReport, buildInfo);

      expect(card.contentType).toBe('application/vnd.microsoft.card.adaptive');

      const content = card.content;

      // Find the Azure DevOps container which should be present
      const azureDevOpsContainer = content.body.find((item: any) =>
        item.type === 'Container' && item.items &&
        item.items.some((subItem: any) =>
          subItem.type === 'TextBlock' &&
          subItem.text &&
          subItem.text.includes('Azure DevOps')
        )
      );

      expect(azureDevOpsContainer).toBeTruthy();

      // Check that the Azure DevOps build action is present
      const azureDevOpsAction = content.actions.find((action: any) =>
        action.title === 'View in Azure DevOps'
      );
      expect(azureDevOpsAction).toBeTruthy();
      expect(azureDevOpsAction.url).toContain(testReport.azureDevOpsBuildId);
    });
  });

  describe('createMetricsChartCard', () => {
    it('should create a metrics chart card with correct data', () => {
      const card = cardBuilder.createMetricsChartCard(testReport, historicalData);

      expect(card.contentType).toBe('application/vnd.microsoft.card.adaptive');
      expect(CardFactory.adaptiveCard).toHaveBeenCalled();

      const content = card.content;
      expect(content).toHaveProperty('type', 'AdaptiveCard');

      // Check title contains project name
      const titleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Large' && item.weight === 'Bolder'
      );
      expect(titleBlock).toBeTruthy();
      expect(titleBlock.text).toContain(testReport.projectName);

      // Check subtitle contains builds count
      const subtitleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Medium'
      );
      expect(subtitleBlock).toBeTruthy();
      expect(subtitleBlock.text).toContain(`${historicalData.length}`);

      // Check that chart URLs are present
      const imageElements = content.body.filter((item: any) =>
        item.type === 'Container' && item.items &&
        item.items.some((subItem: any) => subItem.type === 'Image')
      );
      expect(imageElements.length).toBeGreaterThan(0);

      // Check that actions are present
      expect(content.actions.length).toBeGreaterThan(0);
    });
  });

  describe('createFailedTestsCard', () => {
    it('should create a failed tests card with correct data', () => {
      const card = cardBuilder.createFailedTestsCard(testReport, testMetrics);

      expect(card.contentType).toBe('application/vnd.microsoft.card.adaptive');
      expect(CardFactory.adaptiveCard).toHaveBeenCalled();

      const content = card.content;
      expect(content).toHaveProperty('type', 'AdaptiveCard');

      // Check title contains project name and "Failed Tests"
      const titleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Large' && item.weight === 'Bolder'
      );
      expect(titleBlock).toBeTruthy();
      expect(titleBlock.text).toContain(testReport.projectName);
      expect(titleBlock.text).toContain('Failed Tests');

      // Check that there's a subtitle with build number
      const subtitleBlock = content.body.find((item: any) =>
        item.type === 'TextBlock' && item.size === 'Medium'
      );
      expect(subtitleBlock).toBeTruthy();
      expect(subtitleBlock.text).toContain(testReport.buildNumber);

      // Check for failed test count
      const totalFailedTests = content.totalFailedTests;
      expect(totalFailedTests).toBe(testMetrics.length);

      // Check that the actions are present
      expect(content.actions.length).toBeGreaterThan(0);
    });
  });

  describe('utility methods', () => {
    it('formatDuration should format duration correctly', () => {
      // Access private method for testing
      const formatDuration = (cardBuilder as any).formatDuration.bind(cardBuilder);

      expect(formatDuration(5000)).toBe('5s');
      expect(formatDuration(65000)).toBe('1m 5s');
      expect(formatDuration(3665000)).toBe('1h 1m 5s');
    });

    it('getStatusColor should return correct color based on pass rate', () => {
      // Access private method for testing
      const getStatusColor = (cardBuilder as any).getStatusColor.bind(cardBuilder);

      expect(getStatusColor(95)).toBe('good');
      expect(getStatusColor(80)).toBe('warning');
      expect(getStatusColor(60)).toBe('attention');
    });
  });
});
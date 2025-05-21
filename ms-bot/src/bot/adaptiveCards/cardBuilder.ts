import { injectable } from 'inversify';
import { CardFactory, Attachment } from 'botbuilder';
import * as moment from 'moment';
import * as ACData from 'adaptivecards-templating';
import { TestReport } from '../../domain/entities/testReport';
import { TestMetric } from '../../domain/entities/testMetric';
import { AzureDevOpsBuildInfo } from '../../adapters/azureDevOpsAdapter';
import { MetricComparisonWithBuildInfo } from '../../domain/useCases/getTestMetrics';

// Import card templates
import * as welcomeCardTemplate from './templates/welcomeCard.json';
import * as metricCardTemplate from './templates/metricCard.json';
import * as metricChartCardTemplate from './templates/metricChartCard.json';
import * as buildComparisonCardTemplate from './templates/buildComparisonCard.json';
import * as failedTestsCardTemplate from './templates/failedTestsCard.json';

@injectable()
export class CardBuilder {
  /**
   * Creates a welcome card with instructions for using the bot
   * @returns The welcome card
   */
  public createWelcomeCard(): Attachment {
    const cardData = {
      title: 'Friday Metrics Bot',
      subtitle: 'Your test metrics assistant',
      text: 'I can help you view and analyze test metrics from the Friday service. Try asking me:',
      commands: [
        '• Show me today\'s test metrics',
        '• Get failed tests from last week',
        '• Compare metrics between builds',
        '• Show performance trends for project X'
      ]
    };

    const cardJson = this.populateTemplate(welcomeCardTemplate, cardData);
    return CardFactory.adaptiveCard(cardJson);
  }

  /**
   * Creates a card showing test metrics summary
   * @param report - The test metrics report
   * @param buildInfo - Optional Azure DevOps build information
   * @returns The metrics card
   */
  public createMetricsSummaryCard(report: TestReport, buildInfo?: AzureDevOpsBuildInfo): Attachment {
    const passRate = report.getPassRate().toFixed(1);

    const cardData = {
      title: `Test Metrics: ${report.projectName}`,
      subtitle: `Build: ${report.buildNumber} | ${moment(report.timestamp).format('MMM DD, YYYY')}`,
      totalTests: report.totalTests,
      passedTests: report.passedTests,
      failedTests: report.failedTests,
      skippedTests: report.skippedTests,
      passRate: passRate,
      duration: this.formatDuration(report.duration),
      statusColor: this.getStatusColor(Number(passRate)),
      buildUrl: report.buildUrl || '#',
      hasAzureDevOps: Boolean(buildInfo),
      buildStatus: buildInfo?.status || '',
      buildResult: buildInfo?.result || '',
      buildStartTime: buildInfo?.startTime ? moment(buildInfo.startTime).format('MMM DD, YYYY HH:mm') : '',
      buildFinishTime: buildInfo?.finishTime ? moment(buildInfo.finishTime).format('MMM DD, YYYY HH:mm') : '',
      buildRequestedBy: buildInfo?.requestedBy || '',
      azureDevOpsBuildId: report.azureDevOpsBuildId || ''
    };

    const cardJson = this.populateTemplate(metricCardTemplate, cardData);
    return CardFactory.adaptiveCard(cardJson);
  }

  /**
   * Creates a card with test metrics charts
   * @param report - The test metrics report
   * @param historicalData - Historical test data for trends
   * @returns The metrics chart card
   */
  public createMetricsChartCard(report: TestReport, historicalData: TestReport[]): Attachment {
    // Generate chart data URLs
    // In a real implementation, we would use chart generation services or base64 encoded images

    const cardData = {
      title: `${report.projectName} - Test Metrics Charts`,
      subtitle: `Last ${historicalData.length} builds`,
      passRateChartUrl: `https://example.com/charts/${report.projectId}/pass-rate.png`,
      durationChartUrl: `https://example.com/charts/${report.projectId}/duration.png`,
      testCountChartUrl: `https://example.com/charts/${report.projectId}/test-count.png`,
      timestamp: moment().format('MMMM DD, YYYY [at] HH:mm'),
      buildNumbers: historicalData.map(r => r.buildNumber).join(', ')
    };

    const cardJson = this.populateTemplate(metricChartCardTemplate, cardData);
    return CardFactory.adaptiveCard(cardJson);
  }

  /**
   * Creates a card showing failed tests
   * @param report - The test report
   * @param failedTests - List of failed tests
   * @returns The failed tests card
   */
  public createFailedTestsCard(report: TestReport, failedTests: TestMetric[]): Attachment {
    const cardData = {
      title: `Failed Tests: ${report.projectName}`,
      subtitle: `Build: ${report.buildNumber} | ${moment(report.timestamp).format('MMM DD, YYYY')}`,
      totalFailedTests: failedTests.length,
      failedTests: failedTests.map((test, index) => ({
        index: index + 1,
        name: test.name,
        className: test.className,
        duration: this.formatDuration(test.duration),
        errorMessage: test.errorMessage || 'Unknown error',
        id: test.id
      })),
      buildUrl: report.buildUrl || '#',
      hasAzureDevOps: report.hasAzureDevOpsBuild(),
      projectId: report.projectId,
      buildNumber: report.buildNumber
    };

    const cardJson = this.populateTemplate(failedTestsCardTemplate, cardData);
    return CardFactory.adaptiveCard(cardJson);
  }

  /**
   * Creates a card for build comparison
   * @param comparisonResult - Result of comparison with build info
   * @returns The build comparison card
   */
  public createBuildComparisonCard(comparisonResult: MetricComparisonWithBuildInfo): Attachment {
    const { report1, report2, comparison, buildInfo1, buildInfo2 } = comparisonResult;

    const cardData = {
      title: `Build Comparison: ${report1.projectName}`,
      subtitle: `Comparing builds ${report1.buildNumber} and ${report2.buildNumber}`,
      build1: {
        number: report1.buildNumber,
        totalTests: report1.totalTests,
        passedTests: report1.passedTests,
        failedTests: report1.failedTests,
        skippedTests: report1.skippedTests,
        passRate: report1.getPassRate().toFixed(1),
        duration: this.formatDuration(report1.duration),
        timestamp: moment(report1.timestamp).format('MMM DD, YYYY HH:mm'),
        url: report1.buildUrl || '#',
        hasAzureDevOps: Boolean(buildInfo1),
        status: buildInfo1?.status || '',
        result: buildInfo1?.result || '',
        requestedBy: buildInfo1?.requestedBy || ''
      },
      build2: {
        number: report2.buildNumber,
        totalTests: report2.totalTests,
        passedTests: report2.passedTests,
        failedTests: report2.failedTests,
        skippedTests: report2.skippedTests,
        passRate: report2.getPassRate().toFixed(1),
        duration: this.formatDuration(report2.duration),
        timestamp: moment(report2.timestamp).format('MMM DD, YYYY HH:mm'),
        url: report2.buildUrl || '#',
        hasAzureDevOps: Boolean(buildInfo2),
        status: buildInfo2?.status || '',
        result: buildInfo2?.result || '',
        requestedBy: buildInfo2?.requestedBy || ''
      },
      difference: {
        totalTests: this.formatDifference(comparison.totalTestsDiff),
        passedTests: this.formatDifference(comparison.passedTestsDiff),
        failedTests: this.formatDifference(comparison.failedTestsDiff),
        skippedTests: this.formatDifference(comparison.skippedTestsDiff),
        passRate: this.formatDifference(Number(comparison.passRateDiff.toFixed(1))),
        durationFormatted: this.formatDurationDifference(comparison.durationDiff),
        statusColor: comparison.passRateDiff >= 0 ? 'good' : 'attention'
      },
      projectId: report1.projectId
    };

    const cardJson = this.populateTemplate(buildComparisonCardTemplate, cardData);
    return CardFactory.adaptiveCard(cardJson);
  }

  /**
   * Formats test duration in a human-readable format
   * @param milliseconds - Duration in milliseconds
   * @returns Formatted duration
   */
  private formatDuration(milliseconds: number): string {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }

  /**
   * Formats a duration difference in a human-readable format
   * @param millisecondsDifference - Duration difference in milliseconds
   * @returns Formatted duration difference
   */
  private formatDurationDifference(millisecondsDifference: number): string {
    const secondsDiff = Math.floor(Math.abs(millisecondsDifference) / 1000);
    const minutesDiff = Math.floor(secondsDiff / 60);
    const hoursDiff = Math.floor(minutesDiff / 60);

    let formattedDiff = '';

    if (hoursDiff > 0) {
      formattedDiff = `${hoursDiff}h ${minutesDiff % 60}m ${secondsDiff % 60}s`;
    } else if (minutesDiff > 0) {
      formattedDiff = `${minutesDiff}m ${secondsDiff % 60}s`;
    } else {
      formattedDiff = `${secondsDiff}s`;
    }

    if (millisecondsDifference >= 0) {
      return `${formattedDiff} slower`;
    } else {
      return `${formattedDiff} faster`;
    }
  }

  /**
   * Formats a difference value with sign
   * @param difference - Difference value
   * @returns Formatted difference with sign
   */
  private formatDifference(difference: number): string {
    if (difference > 0) {
      return `+${difference}`;
    } else {
      return `${difference}`;
    }
  }

  /**
   * Gets the color for status indication based on pass rate
   * @param passRate - Pass rate percentage
   * @returns Color name for styling
   */
  private getStatusColor(passRate: number): string {
    if (passRate >= 90) {
      return 'good';
    } else if (passRate >= 75) {
      return 'warning';
    } else {
      return 'attention';
    }
  }

  /**
   * Populates a card template with data
   * @param template - The card template
   * @param data - The data to populate the template with
   * @returns The populated card
   */
  private populateTemplate(template: any, data: any): any {
    const templatePayload = template;
    const templateEngine = new ACData.Template(templatePayload);
    const context = new ACData.EvaluationContext();
    context.$root = data;

    return templateEngine.expand(context);
  }
}
import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { injectable, inject } from 'inversify';
import { ConfigService } from '../config/config';
import { Logger } from '../infrastructure/logging/logger';
import { TestMetric, TestStatus } from '../domain/entities/testMetric';
import { TestReport } from '../domain/entities/testReport';

/**
 * Interface for API metric data
 */
interface ApiFridayMetric {
  id: string;
  name: string;
  status: string;
  duration: number;
  className: string;
  timestamp: string;
  errorMessage?: string;
}

/**
 * Interface for API report data
 */
interface ApiFridayReport {
  id: string;
  projectId: string;
  projectName: string;
  buildNumber: string;
  buildUrl?: string;
  timestamp: string;
  totalTests: number;
  passedTests: number;
  failedTests: number;
  skippedTests: number;
  duration: number;
  metrics?: ApiFridayMetric[];
  azureDevOpsBuildId?: string;
}

@injectable()
export class FridayServiceAdapter {
  private readonly apiBaseUrl: string;
  private readonly apiKey: string;
  private readonly httpClient: AxiosInstance;

  /**
   * @param configService - Configuration service
   * @param logger - Logger instance
   */
  constructor(
    @inject(ConfigService) private readonly configService: ConfigService,
    @inject(Logger) private readonly logger: Logger
  ) {
    this.apiBaseUrl = this.configService.get<string>('FRIDAY_API_URL');
    this.apiKey = this.configService.get<string>('FRIDAY_API_KEY');

    this.httpClient = axios.create({
      baseURL: this.apiBaseUrl,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      timeout: 10000
    });
  }

  /**
   * Get the latest test report for a project
   * @param projectId - Project identifier
   * @returns Promise resolving to a test report
   */
  public async getLatestTestReport(projectId: string): Promise<TestReport> {
    try {
      const response = await this.httpClient.get<ApiFridayReport>(`/projects/${projectId}/reports/latest`);
      return this.mapToTestReport(response.data);
    } catch (error) {
      this.handleApiError(error as Error, `Error fetching latest test report for project ${projectId}`);
      // This line is never reached due to the throw in handleApiError, but needed for TypeScript
      throw error;
    }
  }

  /**
   * Get a test report for a specific build
   * @param projectId - Project identifier
   * @param buildNumber - Build number
   * @returns Promise resolving to a test report
   */
  public async getTestReportForBuild(projectId: string, buildNumber: string): Promise<TestReport> {
    try {
      const response = await this.httpClient.get<ApiFridayReport>(`/projects/${projectId}/builds/${buildNumber}/report`);
      return this.mapToTestReport(response.data);
    } catch (error) {
      this.handleApiError(error as Error, `Error fetching test report for project ${projectId}, build ${buildNumber}`);
      // This line is never reached due to the throw in handleApiError, but needed for TypeScript
      throw error;
    }
  }

  /**
   * Get historical test reports for a project
   * @param projectId - Project identifier
   * @param count - Number of reports to retrieve
   * @returns Promise resolving to an array of test reports
   */
  public async getHistoricalTestReports(projectId: string, count: number): Promise<TestReport[]> {
    try {
      const response = await this.httpClient.get<{ reports: ApiFridayReport[] }>(`/projects/${projectId}/reports`, {
        params: { limit: count }
      });

      return response.data.reports.map(this.mapToTestReport.bind(this));
    } catch (error) {
      this.handleApiError(error as Error, `Error fetching historical test reports for project ${projectId}`);
      // This line is never reached due to the throw in handleApiError, but needed for TypeScript
      throw error;
    }
  }

  /**
   * Get detailed test metrics for a build
   * @param projectId - Project identifier
   * @param buildNumber - Build number
   * @returns Promise resolving to an array of test metrics
   */
  public async getDetailedTestMetrics(projectId: string, buildNumber: string): Promise<TestMetric[]> {
    try {
      const response = await this.httpClient.get<{ metrics: ApiFridayMetric[] }>(`/projects/${projectId}/builds/${buildNumber}/metrics`);

      return response.data.metrics.map(metric => this.mapToTestMetric(metric, projectId, buildNumber));
    } catch (error) {
      this.handleApiError(error as Error, `Error fetching detailed test metrics for project ${projectId}, build ${buildNumber}`);
      // This line is never reached due to the throw in handleApiError, but needed for TypeScript
      throw error;
    }
  }

  /**
   * Map API response to TestReport domain entity
   * @param data - API response data
   * @returns Test report object
   */
  private mapToTestReport(data: ApiFridayReport): TestReport {
    try {
      return new TestReport({
        id: data.id,
        projectId: data.projectId,
        projectName: data.projectName,
        buildNumber: data.buildNumber,
        buildUrl: data.buildUrl,
        timestamp: new Date(data.timestamp),
        totalTests: data.totalTests,
        passedTests: data.passedTests,
        failedTests: data.failedTests,
        skippedTests: data.skippedTests,
        duration: data.duration,
        azureDevOpsBuildId: data.azureDevOpsBuildId,
        // Map test metrics if they exist in the response
        testMetrics: data.metrics
          ? data.metrics.map(metric => this.mapToTestMetric(metric, data.projectId, data.buildNumber))
          : []
      });
    } catch (error) {
      this.logger.error(`Error mapping test report data: ${(error as Error).message}`, error as Error);
      throw new Error(`Failed to map test report data: ${(error as Error).message}`);
    }
  }

  /**
   * Map API metric to TestMetric domain entity
   * @param metric - API metric data
   * @param projectId - Project ID
   * @param buildNumber - Build number
   * @returns TestMetric object
   */
  private mapToTestMetric(metric: ApiFridayMetric, projectId: string, buildNumber: string): TestMetric {
    let status: TestStatus;

    switch (metric.status.toLowerCase()) {
      case 'passed':
        status = TestStatus.Passed;
        break;
      case 'failed':
        status = TestStatus.Failed;
        break;
      case 'skipped':
        status = TestStatus.Skipped;
        break;
      default:
        throw new Error(`Unknown test status: ${metric.status}`);
    }

    return new TestMetric({
      id: metric.id,
      name: metric.name,
      status,
      duration: metric.duration,
      className: metric.className,
      projectId,
      buildNumber,
      timestamp: new Date(metric.timestamp),
      errorMessage: metric.errorMessage
    });
  }

  /**
   * Handle API errors
   * @param error - The error object
   * @param message - Custom error message
   * @throws Error - Rethrows a formatted error
   */
  private handleApiError(error: Error, message: string): never {
    let errorMessage = message;

    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError;

      if (axiosError.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        errorMessage += ` - Status: ${axiosError.response.status}`;

        const responseData = axiosError.response.data as { message?: string };
        if (responseData && responseData.message) {
          errorMessage += ` - ${responseData.message}`;
        }

        this.logger.error(errorMessage, {
          status: axiosError.response.status,
          data: axiosError.response.data
        });
      } else if (axiosError.request) {
        // The request was made but no response was received
        errorMessage += ' - No response received';
        this.logger.error(errorMessage, { request: axiosError.request });
      } else {
        // Something happened in setting up the request that triggered an Error
        errorMessage += ` - ${axiosError.message}`;
        this.logger.error(errorMessage, axiosError);
      }
    } else {
      // Non-Axios error
      errorMessage += ` - ${error.message}`;
      this.logger.error(errorMessage, error);
    }

    throw new Error(errorMessage);
  }
}
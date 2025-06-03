import { chromium, firefox, webkit } from 'playwright';
import { browserOptions } from './browser-options';
import { CustomWorld } from '../../world/custom-world';
import { ITestCaseHookParameter } from '@cucumber/cucumber/lib/support_code_library_builder/types';
import { Browser } from 'playwright';

import fs from 'node:fs';
import { ConsoleLogger } from '../../playwright/console-logger';

declare global {
  // eslint-disable-next-line no-var
  var browser: Browser;
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace NodeJS {
    interface Global {
      browser: Browser;
    }
  }
}

const browsers: { [k: string]: () => Promise<Browser> } = {
  firefox: async (): Promise<Browser> => firefox.launch(browserOptions),
  webkit: async (): Promise<Browser> => webkit.launch(browserOptions),
  chrome: async (): Promise<Browser> => chromium.launch({ ...browserOptions, channel: 'chrome' }),
  chromium: async (): Promise<Browser> => chromium.launch(browserOptions),
};

export function createBrowser(): () => Promise<void> {
  return async function () {
    global.browser = await browsers[process.env.BROWSER ?? 'chrome']();
  };
}

export function closeBrowser(): () => Promise<void> {
  return async function () {
    await global.browser.close();
  };
}

export function createContext(): (this: CustomWorld, { pickle }: ITestCaseHookParameter) => Promise<void> {
  return async function (this: CustomWorld, { pickle }: ITestCaseHookParameter) {
    this.context = await global.browser.newContext({
      acceptDownloads: true,
      recordVideo: {
        dir: 'reports/videos/',
        size: { width: 1280, height: 720 },
      },
    });

    this.page = await this.context?.newPage();
    this.request = this.context?.request;
    this.feature = pickle;
    this.scenarioName = pickle.name.replace(/\s+/g, '_');
    this.consoleLogger = new ConsoleLogger(this.page);
  };
}

async function attachScreenshot(this: CustomWorld) {
  const image = await this.page?.screenshot();
  if (image) {
    this.attach(image, 'image/png');
  }
}

async function attachVideo(this: CustomWorld) {
  const videoPath = (await this.page.video()?.path()) ?? '';

  try {
    await fs.promises.access(videoPath!);
    const videoData = await fs.promises.readFile(videoPath!);
    this.attach(videoData, 'video/mp4');
  } catch (error) {
    console.error('Error accessing or reading video file:', error);
  }
}

async function createReport(this: CustomWorld, { result }: ITestCaseHookParameter) {
  if (result) {
    this.attach(`Status: ${result?.status}. Duration: ${result.duration?.seconds}s`);
    await attachScreenshot.call(this);
  }
}

export function closeContext(): (this: CustomWorld, hookParameter: ITestCaseHookParameter) => Promise<void> {
  return async function (this: CustomWorld, { result }: ITestCaseHookParameter) {
    await createReport.call(this, { result } as ITestCaseHookParameter);

    const logs = this.consoleLogger.getFormattedLogs();
    if (logs) {
      this.attach(logs, 'text/plain');
    }

    await this.page?.close();
    await this.context?.close();
    await attachVideo.call(this);
  };
}

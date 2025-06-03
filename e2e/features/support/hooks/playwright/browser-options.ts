import { LaunchOptions } from 'playwright';

/* eslint-disable @typescript-eslint/naming-convention */
export const browserOptions: LaunchOptions = {
  slowMo: 0,
  args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
  firefoxUserPrefs: {
    'media.navigator.streams.fake': true,
    'media.navigator.permission.disabled': true,
  },
  headless: false,
  executablePath: '/usr/bin/google-chrome',

};
/* eslint-enable @typescript-eslint/naming-convention */

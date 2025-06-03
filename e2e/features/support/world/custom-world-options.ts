import { IWorldOptions } from '@cucumber/cucumber';

export interface CustomWorldOptions extends IWorldOptions {
  parameters: { [key: string]: string };
}

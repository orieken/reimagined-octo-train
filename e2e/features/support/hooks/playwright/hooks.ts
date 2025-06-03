import { After, AfterAll, Before, BeforeAll } from '@cucumber/cucumber';
import { closeBrowser, closeContext, createBrowser, createContext } from './setup-playwright';

BeforeAll(createBrowser());
AfterAll(closeBrowser());

Before(createContext());
After(closeContext());

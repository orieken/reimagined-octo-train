# Unit Tests for Page Object Framework

This directory contains unit tests for the page object framework using Vitest.

## Structure

The test directory structure mirrors the source code structure:

- `tests/lib/pages/` - Tests for the page object framework

## Running Tests

To run the tests, use the following npm scripts:

```bash
# Run tests once
npm run test:unit

# Run tests in watch mode
npm run test:unit:watch
```

## Writing Tests

### Testing BasePage

Since BasePage is an abstract class, we need to create a concrete implementation for testing purposes. Here's an example of how to test BasePage:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BasePage } from '../../../lib/pages/base-page';
import { Locator, Page } from 'playwright';

// Create a concrete implementation of BasePage for testing
class TestPage extends BasePage {
  protected get containerLocator(): Locator {
    return this.page.locator('#test-container');
  }
}

// Mock Playwright's Page and Locator
const createMockPage = () => {
  const mockLocator = {
    // Mock methods here
  };

  const mockPage = {
    locator: vi.fn().mockReturnValue(mockLocator),
  };

  return { mockPage, mockLocator };
};

describe('BasePage', () => {
  let testPage: TestPage;
  let mockPage: any;
  let mockLocator: any;

  beforeEach(() => {
    const mocks = createMockPage();
    mockPage = mocks.mockPage;
    mockLocator = mocks.mockLocator;
    testPage = new TestPage(mockPage as unknown as Page);
  });

  // Write tests here
});
```

### Testing Concrete Page Objects

When testing concrete page objects, you can use the same approach as above, but you don't need to create a concrete implementation since you're already testing one.

## Best Practices

1. **Mock Playwright objects**: Use Vitest's mocking capabilities to mock Playwright's Page and Locator objects.
2. **Test one method at a time**: Each test should focus on testing a single method.
3. **Use descriptive test names**: Test names should describe what the test is checking.
4. **Check method calls**: Verify that the correct methods are called with the correct arguments.
5. **Check return values**: Verify that methods return the expected values.
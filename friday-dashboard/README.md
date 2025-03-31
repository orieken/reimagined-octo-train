# Friday Dashboard

A modern web application for analyzing Cucumber test results from the Friday service.

## Overview

Friday Dashboard provides an intuitive interface for viewing and analyzing test results, with features for data visualization and natural language querying of test data. It allows teams to quickly understand test outcomes, track trends, and identify patterns in test failures.

## Features

- **Test Results Dashboard**: Overview of test pass/fail rates, visualizations by feature/scenario, tag distribution analysis, and failure analysis
- **Natural Language Query Interface**: Ask questions about your test data and get answers with source attribution
- **Test Trends Analysis**: Historical pass rate trends, build-to-build comparison, and failure pattern detection

## Technology Stack

- **React**: UI framework
- **React Router**: Navigation
- **Recharts**: Data visualization
- **Tailwind CSS**: Styling
- **Vite**: Build tool
- **Axios**: API communication

## Getting Started

### Prerequisites

- Node.js (v14 or later)
- npm or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/friday-dashboard.git
   cd friday-dashboard
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn
   ```

3. Create a `.env` file in the root directory with the following content:
   ```
   VITE_API_URL=http://localhost:5000/api
   ```

4. Start the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Building for Production

```bash
npm run build
# or
yarn build
```

The build artifacts will be stored in the `dist/` directory.

## Project Structure

```
friday-dashboard/
│
├── public/                      # Static files
│
├── src/                         # Source code
│   ├── assets/                  # Images, fonts, etc.
│   │
│   ├── components/              # Reusable UI components
│   │   ├── common/              # Common UI elements
│   │   ├── charts/              # Chart components
│   │   ├── dashboards/          # Dashboard views
│   │   └── query/               # Query interface components
│   │
│   ├── contexts/                # React contexts
│   │
│   ├── hooks/                   # Custom React hooks
│   │
│   ├── pages/                   # Page components
│   │
│   ├── services/                # API services
│   │
│   └── utils/                   # Utility functions
│
├── .env                         # Environment variables
├── package.json                 # npm dependencies
└── vite.config.js               # Vite configuration
```

## Development Guidelines

### Component Design

- Create reusable, focused components
- Keep component complexity low
- Use functional components with hooks
- Implement proper prop validation

### State Management

- Use React Context for global state
- Keep component state local when possible
- Implement custom hooks for reusable logic

### API Integration

- Create service modules for API communication
- Handle loading and error states
- Implement proper caching and data refresh strategies

### Testing

- Write unit tests for all components
- Test hooks and service functions
- Include integration tests for key features

### Styling

- Use Tailwind CSS for consistent styling
- Implement responsive design
- Create a cohesive visual language

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
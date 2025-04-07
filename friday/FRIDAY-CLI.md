# Check the health of the service
./friday-cli.py health

# Push a sample test report with 10 test cases
./friday-cli.py report --count 10

# Push sample build information
./friday-cli.py build

# Search for test artifacts
./friday-cli.py search "failed login tests"

# Analyze test failure patterns
./friday-cli.py analyze

# Get test execution trends
./friday-cli.py trends

# Populate all endpoints with sample data
./friday-cli.py populate --reports 5 --tests 8

# Show help information
./friday-cli.py --help
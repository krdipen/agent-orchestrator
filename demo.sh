#!/bin/bash

# Function to run a command with a 5-second delay and show its output
run_with_delay() {
    echo "Running: $1"
    echo "----------------------------------------"
    # Execute the command and capture both stdout and stderr
    if ! output=$(eval "$1" 2>&1); then
        echo "Error: Command failed with status $?"
        echo "Output:"
        echo "$output"
        exit 1
    fi
    echo "Output:"
    echo "$output"
    echo "----------------------------------------"
    echo "Waiting 5 seconds before next command..."
    sleep 5
    echo
}

# List all agents
run_with_delay "curl -s --location --request GET 'http://localhost:8000/agents/list' --header 'Content-Type: application/json' | jq '.'"

# Register the agent
run_with_delay "curl -s --location 'http://localhost:8000/agents/register?name=my_agent' --form 'python_file=@\"./my_agent.txt\"' | jq '.'"

# List all agents
run_with_delay "curl -s --location --request GET 'http://localhost:8000/agents/list' --header 'Content-Type: application/json' | jq '.'"

# Start a new success run
run_with_delay "curl -s --location 'http://localhost:8000/runs' --header 'Content-Type: application/json' --data '{
    \"nodes\": [
        {
            \"id\": \"node1\",
            \"agent\": \"data_fetcher\"
        },
        {
            \"id\": \"node2\",
            \"agent\": \"calculator\",
            \"params\": {
                \"parent\": \"node1\",
                \"values\": [5, 6]
            }
        },
        {
            \"id\": \"node3\",
            \"agent\": \"my_agent\"
        }
    ],
    \"edges\": [{\"from_\": \"node1\", \"to\": \"node2\"}],
    \"initial_inputs\": {\"url\": \"https://krdipen.com\"}
}' | jq '.'"

# Start a new failed run
run_with_delay "curl -s --location 'http://localhost:8000/runs' --header 'Content-Type: application/json' --data '{
    \"nodes\": [
        {
            \"id\": \"node1\",
            \"agent\": \"data_fetcher\"
        },
        {
            \"id\": \"node2\",
            \"agent\": \"calculator\",
            \"params\": {
                \"parent\": \"node1\",
                \"values\": [\"5s\", \"6s\"]
            }
        },
        {
            \"id\": \"node3\",
            \"agent\": \"my_agent\"
        }
    ],
    \"edges\": [{\"from_\": \"node1\", \"to\": \"node2\"}],
    \"initial_inputs\": {\"url\": \"https://krdipen.com\"}
}' | jq '.'"

# Get run status
run_with_delay "curl -s --location 'http://localhost:8000/runs' | jq '.'"

echo "All commands executed successfully!"

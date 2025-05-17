# #!/bin/bash

cd ./client && npm run dev &
cd ./server && python main.py

# Clean up on control-c

trap 'kill $(jobs -p)' EXIT
# Wait for all background jobs to finish
wait
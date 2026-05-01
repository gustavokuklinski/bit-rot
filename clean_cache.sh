#!/bin/bash
echo "===================================" 
echo "BIT ROT __pycache__ CLEANER - Linux" 
echo "===================================" 

# Find and delete all __pycache__ directories recursively
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "All __pycache__ folders have been successfully deleted."
echo "===================================" 
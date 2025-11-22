@echo off

set "-x"
coverage "run" "-m" "pytest" "tests/"
coverage "report"
coverage "html" "--title" "%@-coverage%"
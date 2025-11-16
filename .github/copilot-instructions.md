### Required Before Each Commit
- Run `pre-commit` before committing any changes to ensure proper code formatting
- This will run gofmt on all Go files to maintain consistent style
- If pre-commit fails due to linting errors, run it again as it often auto-fixes issues
- Always run `pre-commit run --all-files` to fix any linting errors across the entire codebase

use tailwind only
for anything with color, make it the red color we use which is #e74c3c

always use poetry and not pip
if you don't fix somethign on the first try, add debugging to the code and try again

if you are unsure of something, ask the user for clarification

if you are not sure about the user's intent, ask the user for clarification

dont include exceptions in error messages but be very detailed in text what the error is - don't do this: messages.error(request, f"Error: {str(e)}")
keep javascript in separate files and don't add it to html files
avoid installing packages that are not needed
remove any <style tags and use tailwind css instead
when fixing an issue, always fix the root cause

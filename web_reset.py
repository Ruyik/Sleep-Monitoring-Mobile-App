# web_reset.py

from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime
import os
import sys

# 1. Add the parent directory to the path to import AuthService
# This assumes web_reset.py is run from a subfolder or needs to find AuthService
# If AuthService is in the same directory, you can remove these lines.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))
from backend.auth_service import AuthService # Import directly from backend folder

app = Flask(__name__)
# Initialize the AuthService class
auth_service = AuthService()

# --- Minimal HTML Template for Password Input ---
# This form submits a POST request to the same URL, carrying the token and new password.
RESET_FORM_HTML = """
<!doctype html>
<title>Password Reset</title>
<style>body {font-family: Arial, sans-serif; background-color: #f0f8ff; text-align: center; padding: 50px;} .container {max-width: 400px; margin: auto; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);} input[type=password] {width: 100%; padding: 10px; margin: 8px 0; display: inline-block; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;} input[type=submit] {background-color: #4CAF50; color: white; padding: 14px 20px; margin: 8px 0; border: none; border-radius: 4px; cursor: pointer; width: 100%;} .error {color: red;} .success {color: green;}</style>

<div class="container">
    <h2>Set New Password</h2>
    {% if message %}
        <p class="{{ status }}">{{ message }}</p>
    {% endif %}

    <form method="POST">
        <input type="hidden" name="token" value="{{ token }}">
        <input type="password" name="new_password" placeholder="New Password" required>
        <input type="password" name="confirm_password" placeholder="Confirm Password" required>
        <input type="submit" value="Reset Password">
    </form>
    <p>Token: <code>{{ token }}</code></p>
</div>
"""


# --- End HTML Template ---

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password_handler():
    # Get the token from the URL query parameters
    token = request.args.get('token')

    if request.method == 'GET':
        if not token:
            return render_template_string(RESET_FORM_HTML, message="Error: Reset token missing.", status="error",
                                          token="N/A")

        # Display the form (The user clicked the link)
        return render_template_string(RESET_FORM_HTML, token=token, message="Enter your new password.")

    elif request.method == 'POST':
        # Process the form submission
        token = request.form['token']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return render_template_string(RESET_FORM_HTML, token=token, message="Error: Passwords do not match.",
                                          status="error")

        if len(new_password) < 6:  # Basic validation
            return render_template_string(RESET_FORM_HTML, token=token,
                                          message="Error: Password must be at least 6 characters.", status="error")

        try:
            # Call the AuthService function to validate token and update DB
            result_message = auth_service.reset_password_via_token(token, new_password)

            if "successfully reset" in result_message:
                return render_template_string(RESET_FORM_HTML, message=result_message, status="success",
                                              token="RESET COMPLETE")
            else:
                return render_template_string(RESET_FORM_HTML, message=result_message, status="error", token=token)

        except Exception as e:
            return render_template_string(RESET_FORM_HTML, message=f"Server Error: {e}", status="error", token=token)


if __name__ == '__main__':
    # Run the server accessible on your local network (e.g., from your phone)
    print("🚀 Running Flask Server accessible via your network IP...")
    app.run(host='0.0.0.0', port=5000, debug=False)
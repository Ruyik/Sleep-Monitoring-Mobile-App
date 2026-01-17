import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import random
import string
import uuid # Kept for compatibility, but we use random/string for new tokens

# --- CONFIGURATION ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# Sender email credentials for reset email
SENDER_EMAIL = "positivechillalways@gmail.com"
SENDER_PASSWORD = "qmgi rnji ysxm icai"
SPREADSHEET_NAME = "SmartHealthApp_UserData"

# CRITICAL FIX: Base URL for the password reset web endpoint (must be public)
# This is your current Ngrok URL. MUST be updated if Ngrok restarts.
PASSWORD_RESET_URL_BASE = "https://tracklessly-panicky-kaelyn.ngrok-free.dev/reset_password"
# ---------------------


class AuthService:

    def _get_sheet(self):
        """Helper to establish Google Sheets connection."""
        try:
            # Note: Ensure backend/service_account.json is the NEW key file
            creds = Credentials.from_service_account_file("backend/service_account.json", scopes=SCOPES)
            client = gspread.authorize(creds)
            return client.open(SPREADSHEET_NAME).sheet1
        except Exception as e:
            raise ConnectionError(f"Google Sheets connection failed: {e}")

    # Helper to generate a unique, temporary token (using random/string for robustness)
    def _generate_token(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    def register_user(self, username, email, password):
        """Register a new user by adding their data to Google Sheets."""
        if not (username and email and password):
            return "Error: All fields are required."

        try:
            sheet = self._get_sheet()
        except ConnectionError as e:
            return f"Error: {e}"

        # Check if username or email already exists
        records = sheet.get_all_records()
        for row in records:
            if str(row.get('username', '')).lower() == username.lower():
                return "Error: Username already exists."
            if str(row.get('email', '')).lower() == email.lower():
                return "Error: Email already registered."

        # Append new user data, leaving columns D and E blank for reset token/expiry
        sheet.append_row([username, email, password, "", ""])
        return f"✅ Registration successful for {username}! Proceed to Login."

    def login_user(self, username, password):
        """Login by verifying credentials from Google Sheets."""
        if not (username and password):
            return "Error: Username and Password required."

        try:
            sheet = self._get_sheet()
        except ConnectionError as e:
            return f"Error: {e}"

        records = sheet.get_all_records()

        if len(records) == 0:
            return "❌ No user data found. Please register first."

        for row in records:
            # Normalize key names and strip whitespace
            sheet_username = str(row.get('username', '')).strip()
            sheet_password = str(row.get('password', '')).strip()

            if sheet_username.lower() == username.lower() and sheet_password == password:
                return f"✅ Welcome back, {username}!"

        return "❌ Invalid username or password."

    def send_reset_email(self, recipient_email):
        """Generates a token, stores it in the DB, and sends the public reset link."""
        if not recipient_email:
            return "Error: Email required for password reset."

        try:
            sheet = self._get_sheet()
        except ConnectionError as e:
            return f"Error: Failed to verify email registration ({e})"

        # 1. Find the row based on email (gspread utility)
        try:
            cell = sheet.find(recipient_email, in_column=2) # Assuming email is in column B (index 2)
        except Exception:
            return "Error: Email not found in database."

        if not cell:
             return "Error: Email not found in database."

        # 2. Generate Token and Expiration Time
        token = self._generate_token()
        expiry_time = datetime.now() + timedelta(hours=1) # Token expires in 1 hour
        row_index = cell.row

        # 3. Store Token and Expiration Time in the Spreadsheet
        # We assume: Column D (Token) is index 4, Column E (Expiry) is index 5
        sheet.update_cell(row_index, 4, token) # Update column D (Token)
        sheet.update_cell(row_index, 5, expiry_time.isoformat()) # Update column E (Expiry)

        # 4. Build the public reset link using the Ngrok URL
        reset_link = f"{PASSWORD_RESET_URL_BASE}?token={token}"

        # 5. Send email
        message = MIMEText(f"Click this link to reset your password (valid for 1 hour):\n{reset_link}")
        message['Subject'] = "Smart Sleep App: Password Reset Request"
        message['From'] = SENDER_EMAIL
        message['To'] = recipient_email

        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
            server.quit()
            return "Password reset email sent successfully. Check your inbox."
        except Exception as e:
            return f"Error sending email: Check app password or network. Detail: {str(e)}"

    def reset_password_via_token(self, token, new_password):
        """
        Verifies token, updates password, and clears token field in Google Sheets.
        Handles both standard ISO and Google Sheets date formats for expiry.
        """
        try:
            sheet = self._get_sheet()
        except ConnectionError:
            return "Error: Database connection failed."

        # 1. Find the row based on the token (assuming token is in column D)
        try:
            token_cell = sheet.find(token, in_column=4)
        except Exception:
            # This handles cases where the token simply doesn't exist
            return "Error: Invalid or expired token (not found)."

        if not token_cell:
            return "Error: Invalid or expired token."

        row_index = token_cell.row

        # 2. Validate Expiry (Directly from Column E / Index 5)
        try:
            # Fetch specifically from Column E to avoid index shifting
            expiry_str = sheet.cell(row_index, 5).value

            if not expiry_str:
                return "Error: Token validation failed (no expiry found)."

            # Clean any whitespace or formatting characters
            expiry_str = expiry_str.strip()

            # --- SMART PARSING LOGIC ---
            # Handles '2026-01-10T03:23:21' and '2026-01-10 03:23:21'
            try:
                # Try standard ISO first
                expiry_time = datetime.fromisoformat(expiry_str)
            except ValueError:
                # Fallback for Google Sheets auto-formatting
                expiry_time = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
            # ---------------------------

            # Check if time has passed
            if datetime.now() > expiry_time:
                return "Error: Token has expired."

        except Exception as e:
            # Returns the exact string value to help you debug if it fails
            return f"Error: Token expiry format invalid. Value in sheet: '{expiry_str}'"

        # 3. Update the Password (Column C / Index 3)
        try:
            sheet.update_cell(row_index, 3, new_password)

            # 4. Clear Token and Expiry (Columns D and E) to prevent re-use
            sheet.update_cell(row_index, 4, "")
            sheet.update_cell(row_index, 5, "")

            return "Password successfully reset! You can now log in with your new password."
        except Exception as e:
            return f"Error updating password in database: {str(e)}"
import js
import json
import hashlib
from pyscript import document

async def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

async def login_user(event):
    if event:
        event.preventDefault()

    # 1. Retrieve user inputs
    email = document.querySelector("#email-id").value.strip()
    password = document.querySelector("#password").value

    if not email or not password:
        js.console.warn("Login attempt failed: Email or password field is empty.")
        js.alert("Please fill in both fields.")
        return

    # 2. Hash input password to match stored SHA-256 format from signup
    hashed_password = await hash_password(password)

    # 3. Supabase API query setup
    url = f"https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data?Email_ID=eq.{email}&select=*"
    api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8"

    js_headers = js.Headers.new()
    js_headers.append("apikey", api_key)
    js_headers.append("Authorization", f"Bearer {api_key}")
    js_headers.append("Content-Type", "application/json")

    # 4. Fetch matching account from Supabase
    try:
        options = js.Object.new()
        options.method = "GET"
        options.headers = js_headers

        response = await js.fetch(url, options)

        if response.ok:
            data_text = await response.text()
            users = json.loads(data_text)

            if len(users) > 0:
                user = users[0]
                # Compare hashed input password with stored database password
                if user.get("Password") == hashed_password:
                    js.console.log("Login successful! Redirecting to home page...")
                    
                    # Store logged-in user info in localStorage
                    js.localStorage.setItem("user_email", email)
                    js.localStorage.setItem("user_name", user.get("First_Name", "User"))
                    
                    # Redirect to home page
                    js.window.location.href = "home.html"
                else:
                    # Output error to browser console
                    js.console.error("Login failed: Password provided is incorrect.")
                    js.alert("Incorrect password. Please try again.")
            else:
                js.console.error(f"Login failed: No account found for email '{email}'.")
                js.alert("No account found with this email ID.")
        else:
            error_text = await response.text()
            js.console.error(f"Database error response: {error_text}")
            js.alert(f"Database error: {error_text}")

    except Exception as e:
        js.console.error(f"Unexpected Python Exception: {str(e)}")
        js.alert(f"An unexpected error occurred: {str(e)}")
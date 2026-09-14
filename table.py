import js
import uuid
import json
import hashlib
from pyscript import document

async def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

async def register_user(event):
    # Prevent default form submission and page refresh
    if event:
        event.preventDefault()

    # 1. Fetch and clean values from input elements
    first_name = document.querySelector("#first_name").value.strip()
    last_name = document.querySelector("#last_name").value.strip()
    email = document.querySelector("#email").value.strip()
    phone = document.querySelector("#phone").value.strip()
    new_password = document.querySelector("#new_password").value
    confirm_password = document.querySelector("#confirm_password").value

    # Validate that required fields are not empty
    if not all([first_name, last_name, email, phone, new_password, confirm_password]):
        js.alert("Please fill in all required fields.")
        return

    # Validate that passwords match
    if new_password != confirm_password:
        js.alert("Passwords do not match!")
        return

    # 2. Hash password before saving
    hashed_password = await hash_password(new_password)

    # 3. Generate unique UUID
    uid = str(uuid.uuid4())

    # 4. Supabase API Configuration
    url = "https://fvgwubrhxlpwyoqkbakm.supabase.co/rest/v1/Signup_Data"
    api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ2Z3d1YnJoeGxwd3lvcWtiYWttIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkzNjUyMzAsImV4cCI6MjEwNDk0MTIzMH0.pFQl2ZDwJSj-Vjsp-jvUFCEDmDAmWEWg0Sar_-jTdn8"

    payload = {
        "UID": uid,
        "First_Name": first_name,
        "Last_Name": last_name,
        "Email_ID": email,
        "Phone_No": phone,
        "Password": hashed_password
    }

    # 5. Construct JavaScript Headers using native JS Headers object
    js_headers = js.Headers.new()
    js_headers.append("apikey", api_key)
    js_headers.append("Authorization", f"Bearer {api_key}")
    js_headers.append("Content-Type", "application/json")
    js_headers.append("Prefer", "return=minimal")

    # 6. Submit POST request to Supabase REST API
    try:
        options = js.Object.new()
        options.method = "POST"
        options.headers = js_headers
        options.body = json.dumps(payload)

        response = await js.fetch(url, options)

        if response.ok:
            # Print to browser console
            print("Account created successfully!")
            js.console.log("Account created successfully!")
            
            # Display alert message
            js.alert("Account successfully created!")
            
            # Redirect user to sign-in page
            js.window.location.href = "signin.html"
        else:
            error_text = await response.text()
            print("Supabase Error Response:", error_text)
            js.alert(f"Failed to insert into database: {error_text}")

    except Exception as e:
        print("Python Exception:", str(e))
        js.alert(f"An unexpected error occurred: {str(e)}")
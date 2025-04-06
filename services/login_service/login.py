from flask import Flask, request, render_template, redirect, url_for, jsonify, make_response
import requests 
import os

app = Flask(__name__)

CHAT_SERVICE_PORT=5003

# Directly set the port number

@app.route("/", methods=['GET'])
def home():
    # redirect to login
    return redirect(url_for('login'))


@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")

    form_data = request.form

    profile_response = requests.post("http://profile_service/new_profile", json={
        "user_name": form_data["username"],
        "password": form_data["password"],
        "bio": form_data["bio"]
    })

    if profile_response.status_code != 200:
        return profile_response.text

    profile_data = profile_response.json()
    profile_id = profile_data.get("profile_id")
    
    if not profile_id:
        return make_response(jsonify({"error": "Invalid profile response"}), 400)

    return redirect(url_for('login'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html")

    # Get form data
    form_data = request.form
    username = form_data.get("username")
    password = form_data.get("password")
    # make this endpoint return profile id
    profile_response = requests.post("http://profile_service/validate_user", json={
        "user_name": username,
        "password": password
    })
    profile_response = profile_response.json()
    profile_id = profile_response["profile_id"]

    if profile_id:

        token_response = requests.post("http://auth_service/create_access_token", json={"profile_id": profile_id})
        if token_response.status_code != 200:
            return token_response.text
        access_token = token_response.json().get("access_token")

        if access_token:
            # Redirect directly with the profile_id and access_token as query parameters
            chatroom_url = f"http://54.242.224.204:5003/chatrooms?profile_id={profile_id}&access_token={access_token}"
            return redirect(chatroom_url)
            # return render_template(url_for('chatrooms', profile_id=profile_id, access_token=access_token)) # EDIT HTML TEMPLATE


    # If profile ID or access token is not found, redirect back to login page
    return render_template('login.html', app_message="Login failed")


@app.route("/logout", methods=["GET"])
def logout():
    # Extract the authentication token from the query parameters
    token = request.args.get("access_token")
    if not token:
        return jsonify({"error": "Missing token"}), 400

    # Forward the token to the auth_service's logout endpoint
    try:
        auth_response = requests.get("http://auth_service/logout", params={"access_token": token})
        if auth_response.status_code == 200:
            # Logout was successful at the auth_service
            return redirect(url_for("login"))
        else:
            return jsonify({"error": "Logout failed at auth_service"}), auth_response.status_code
    except Exception as e:
        return jsonify({"error": "Error communicating with auth_service: " + str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)

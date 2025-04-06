{\rtf1\ansi\ansicpg1252\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 4.1 Profile Service - This starting point was not bad at all, I had to figure out the codebase and containers and that took me a while but it was alright after I figured things out. I wrote out the functions, it took me a while to figure out how to use the cryptography library but storing in the database wasn't bad after reading documentation before. I wrote the SQL table initialization, and made some adjustments to the SQL table.\
\
Endpoints:\
	\'95	POST /new_profile\
Accepts user_name, password, and bio. The password is hashed using cryptography and stored in the database. This function was pretty simple to develop since we already kind of did it in the last project. I mainly referred to that and connected the DB as well.\
\
@app.route("/new_profile", methods=["POST"])\
def new_profile():\
    # Create a new profile based on the parameters passed in the POST body as JSON.\
    # Expected JSON: \{ "user_name": <str>, "password": <str>, "bio": <str> \}\
    data = request.get_json()\
    user_name = data.get("user_name")\
    password = data.get("password")\
    bio = data.get("bio", "")\
\
    if not user_name or not password:\
        return jsonify(\{"error": "Missing user_name or password"\}), 400\
\
    # Hash the password using the cryptography package\
    hashed_pw_str = hash_password(password)\
\
    try:\
        conn = get_db()\
        cursor = conn.cursor()\
        insert_query = """\
            INSERT INTO user_profiles (username, password_hash, biography)\
            VALUES (%s, %s, %s)\
        """\
        cursor.execute(insert_query, (user_name, hashed_pw_str, bio))\
        conn.commit()\
        profile_id = cursor.lastrowid\
        return jsonify(\{"profile_id": profile_id\}), 201\
    except pymysql.MySQLError as err:\
        print("MySQL Error:", err, file=sys.stderr)\
        return jsonify(\{"error": "Database error"\}), 500\
    except Exception as e:\
        print("Exception:", str(e), file=sys.stderr)\
        return jsonify(\{"error": "Internal error"\}), 500\
    finally:\
        cursor.close()\
        conn.close()\
\
\
\
	\'95	POST /validate_user\
Accepts user_name and password, validates credentials, and returns the corresponding profile_id if correct. This one was a little different since I used python's bcrypt last time and now using cryptography based on the requirements.txt. It was a little tricky but I found an example usage online and that was helpful.\
\
@app.route("/validate_user", methods=["POST"])\
def validate_user():\
    # Validate user credentials.\
    # Expected JSON: \{ "user_name": <str>, "password": <str> \}\
    data = request.get_json()\
    user_name = data.get("user_name")\
    password = data.get("password")\
\
    if not user_name or not password:\
        return jsonify(\{"profile_id": None\}), 400\
\
    try:\
        conn = get_db()\
        cursor = conn.cursor(pymysql.cursors.DictCursor)\
        select_query = "SELECT profile_id, password_hash FROM user_profiles WHERE username = %s"\
        cursor.execute(select_query, (user_name,))\
        user = cursor.fetchone()\
\
        if user and verify_password(password, user["password_hash"]):\
            return jsonify(\{"profile_id": user["profile_id"]\}), 200\
        else:\
            return jsonify(\{"profile_id": None\}), 401\
    except pymysql.MySQLError as err:\
        print("MySQL Error:", err, file=sys.stderr)\
        return jsonify(\{"profile_id": None\}), 500\
    except Exception as e:\
        print("Exception:", str(e), file=sys.stderr)\
        return jsonify(\{"profile_id": None\}), 500\
    finally:\
        cursor.close()\
        conn.close()\
\
\
\
\
\
	\'95	GET /get_username/<profile_id>\
Returns the username associated with a given profile ID. Also a simple function, just had to air out the kinks with the SQL query but after testing it was fine.\
\
@app.route('/get_username/<int:profile_id>', methods=['GET'])\
def get_username(profile_id):\
    # Return the username associated with the given profile_id.\
    try:\
        conn = get_db()\
        cursor = conn.cursor()\
        select_query = "SELECT username FROM user_profiles WHERE profile_id = %s"\
        cursor.execute(select_query, (profile_id,))\
        result = cursor.fetchone()\
        if result:\
            return jsonify(\{"username": result[0]\}), 200\
        else:\
            return jsonify(\{"message": "Profile not found"\}), 404\
    except pymysql.MySQLError as err:\
        print("MySQL Error:", err, file=sys.stderr)\
        return jsonify(\{"message": "Database error"\}), 500\
    except Exception as e:\
        print("Exception:", str(e), file=sys.stderr)\
        return jsonify(\{"message": "Internal error"\}), 500\
    finally:\
        cursor.close()\
        conn.close()\
\
\
\
\
\
4.2 Database Management Interface (phpMyAdmin)\
\
To enable convenient access to the MySQL database, I added a phpmyadmin service to the Docker Compose setup. I've had experienced with docker compose in a professional setting so this was pretty simple. Setting up the container and the pathing was a slight struggle but it became to be fine. I was confused how to log in at first but a friend helped me and it was right in front of my face haha. \
\
  phpmyadmin:\
    image: phpmyadmin/phpmyadmin\
    container_name: phpadmin\
    ports:\
      - "5005:80"\
    environment:\
      PMA_HOST: mysql\
    links:\
      - mysql\
\
\
\
\
\
4.3 Logout Button\
\
To implement logout functionality, I added a /logout route to both login_service and auth_service. I had to create a new Auth table for this and there was a bunch of ruckus with the auth_tokens and their naming convention. I didn't know where to use token and where to use auth_token so that took me a while to debug. I used the print and os systdr to show logs and where the access tokens were failing to be called and referred to, I had to play with the links and sending the user to certain places but I eventually figured it out.\
\
@app.route("/logout", methods=["GET"])\
def logout():\
    # Extract the authentication token from the query parameters\
    token = request.args.get("access_token")\
    if not token:\
        return jsonify(\{"error": "Missing token"\}), 400\
\
    # Forward the token to the auth_service's logout endpoint\
    try:\
        auth_response = requests.get("http://auth_service/logout", params=\{"access_token": token\})\
        if auth_response.status_code == 200:\
            # Logout was successful at the auth_service\
            return redirect(url_for("login"))\
        else:\
            return jsonify(\{"error": "Logout failed at auth_service"\}), auth_response.status_code\
    except Exception as e:\
        return jsonify(\{"error": "Error communicating with auth_service: " + str(e)\}), 500\
\
@app.route("/logout", methods=["GET"])\
def auth_logout():\
    access_token = request.args.get("access_token")\
    if not access_token:\
        return jsonify(\{"error": "Missing token"\}), 400\
\
    try:\
        conn = db_connect()\
        cursor = conn.cursor()\
        delete_query = "DELETE FROM Auth WHERE access_token = %s"\
        cursor.execute(delete_query, (access_token,))\
        conn.commit()\
        print(f"DEBUG: Attempted deletion of token \{access_token\}, rowcount: \{cursor.rowcount\}", file=sys.stderr)\
        if cursor.rowcount > 0:\
            return jsonify(\{"message": "Logged out successfully"\}), 200\
        else:\
            return jsonify(\{"error": "Token not found"\}), 404\
    except Exception as e:\
        print("Exception occurred in auth_logout:", str(e), file=sys.stderr)\
        return jsonify(\{"error": "Internal error: " + str(e)\}), 500\
    finally:\
        cursor.close()\
        conn.close()\
\
\
\
\
\
4.4 Message Attachments and Media\
\
I created a new file_service Flask app with the following endpoints: these two proved most difficult in all the project. I had to use my whole brain to figure out why the CORS errors were occuring and eventually found out that I read the requirements wrong, I was trying to authenticate before showing the image but I got rid of the auth for viewing images because it was unnecessary. It was a fluid process before then. I modified the messages SQL and added the file service to hold the files. It was tricky to figure out how to upload into the docker mounted volume but I watched a youtube video and it helped a lot in using docker + sql and a volume to retain the images even on volume clears.\
	\'95	POST /upload: Saves uploaded .png/.jpg files.\
	\'95	GET /files/<filename>: Serves files via HTTP for image rendering in chat.\
\
HTML\
for (let msg of messages) \{\
              // added check for message contains an image field\
              if (msg.image) \{  \
                text += `<li class="message-item" style="background-color: $\{ msg.color \};">\
                            <small class="message-timestamp">($\{ msg.timestamp \})</small>\
                            <strong class="message-username">$\{ msg.username \}:</strong> \
                            <img src="http://3.87.173.80:5000/files/$\{ msg.image \}" alt="Image" style="max-width:200px; max-height:200px;">\
                          </li>`;  \
              \} else \{  \
                text += \
                `<li class="message-item" style="background-color: $\{ msg.color \};">\
                    <small class="message-timestamp">($\{ msg.timestamp \})</small>\
                    <strong class="message-username">$\{ msg.username \}:</strong> \
                    <span class="message-text">$\{ msg.message \}</span>\
                </li>`;\
              \}  \
          \}\
\
@app.route("/upload", methods=["POST"])\
@cross_origin()\
def upload_file():\
    if not authenticate_request():\
        return jsonify(\{"error": "Unauthorized"\}), 401\
    if 'file' not in request.files:\
        return jsonify(\{"error": "No file part in request"\}), 400\
    file = request.files['file']\
    if file.filename == '':\
        return jsonify(\{"error": "No selected file"\}), 400\
    if file and allowed_file(file.filename):\
        filename = secure_filename(file.filename)\
        \
        # Append a unique ID to prevent collisions\
        unique_filename = f"\{uuid.uuid4().hex\}_\{filename\}"\
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)\
        file.save(file_path)\
        \
        # log file upload\
        print(f"File uploaded: \{file_path\}", file=sys.stderr)\
        return jsonify(\{"filename": unique_filename\}), 201\
    else:\
        return jsonify(\{"error": "File type not allowed"\}), 400\
\
function uploadFile(input) \{\
    // Implement file upload functionality\
    for (let file of input.files) \{\
        const formData = new FormData();\
        formData.append("file", file);\
\
        // Upload file to file service (replace <EC2_PUBLIC_IP> with your actual IP)\
        fetch("http://3.87.173.80:5000/upload?access_token=" + encodeURIComponent(access_token), \{ // might be wrong lol\
            method: "POST",\
            body: formData\
        \})\
        .then(response => response.json())\
        .then(data => \{\
            if (data.filename) \{ \
                console.log("File uploaded, filename:", data.filename);\
\
                // Send a message with image reference to the chat\
                fetch("/send_message?" + new URLSearchParams(\{ \
                    profile_id: \{\{ profile_id \}\},\
                    access_token: "\{\{ request.args.get('access_token') \}\}"\
                \}), \{\
                    method: 'POST',  \
                    headers: \{  \
                      'Content-Type': 'application/json'  \
                    \},  \
                    body: JSON.stringify(\{ \
                      room_id: room_id,  \
                      username: username,  \
                      message: "image",   // placehold text message  \
                      image: data.filename  // Include the uploaded filename\
                    \})\
                \})\
                .then(res => \{\
                    if (!res.ok) \{\
                        console.error("Failed to send image message");\
                    \}\
                \})\
                .catch(error => console.error("Error sending image message:", error));\
            \} else \{\
                console.error("File upload failed", data);\
            \}\
        \})\
        .catch(error => console.error("Upload error:", error));  \
    \}\
  \}\
\
@app.route("/files/<filename>", methods=["GET"])\
@cross_origin()\
def get_file(filename):\
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)\
    print(f"DEBUG: Finding file: \{file_path\}", file=sys.stderr)\
\
    if not os.path.isfile(file_path):\
        return jsonify(\{"error": "File not found"\}), 404\
\
    mime_type, _ = mimetypes.guess_type(file_path)\
    return send_file(file_path, mimetype=mime_type or 'application/octet-stream')\
\
\
\
\
\
\
    My biggest Issues:\
    As part of Requirement 4.1, I needed to implement a profile service that allowed users to register and log in securely. The instructions made it clear that storing plain-text passwords was not acceptable and I initially considered bcrypt because I used it before, but the given requirements didn\'92t allow it. Instead, I used the cryptography library to hash passwords during registration and verify them during login. This approach aligned with secure best practices and ensured that even if someone accessed the database, they would not be able to recover actual passwords. I stored only the hashed version, and during login, compared the hashed input with what was stored. It satisfied the requirement to manage credentials securely within the profile service, without modifying the provided requirements.txt.\
\
    For Requirement 4.4, I was tasked with building a new microservice for handling file uploads, separate from the main chat application. Because the file service runs on a different port (5000) than the chatroom service (5003), the browser blocked image fetches due to Cross-Origin Resource Sharing (CORS) restrictions. To solve this, I used the @cross_origin() decorator from the flask_cors module. This allowed my file service to explicitly declare that it was safe for other origins (like the chatroom frontend) to request images. Without this, the browser would continue to block the file service\'92s responses. This step was essential to meeting the requirement that uploaded files appear as media in the chatroom, fully visible to other users in chronological order.}
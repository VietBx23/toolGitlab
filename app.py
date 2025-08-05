from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

LOG_FILE = "upload.log"

@app.route("/")
def home():
    return "✅ GitLab Uploader Backend is running."

@app.route("/upload", methods=["POST"])
def upload_files():
    token = request.form.get("token")
    group_id_str = request.form.get("group_id")
    files = request.files.getlist("files")

    if not token or not group_id_str or not files:
        return jsonify({"error": "Thiếu token, group_id hoặc file upload"}), 400

    try:
        group_id = int(group_id_str)
    except ValueError:
        return jsonify({"error": "group_id phải là số nguyên"}), 400

    # Reset log mỗi lần upload mới
    open(LOG_FILE, "w", encoding="utf-8").close()

    files_sorted = sorted(files, key=lambda f: f.filename)
    created_urls = []
    created_projects = set()

    for index, file in enumerate(files_sorted, start=1):
        original_filename = os.path.basename(file.filename)
        project_name = original_filename.rsplit(".", 1)[0]

        # Nếu đã tạo rồi thì bỏ qua
        if project_name in created_projects:
            continue
        created_projects.add(project_name)

        project_slug = str(index)

        try:
            content = file.read().decode("utf-8")
        except Exception:
            continue

        create_url = "https://gitlab.com/api/v4/projects"
        headers = {"PRIVATE-TOKEN": token}
        payload = {
            "name": project_name,
            "path": project_slug,
            "namespace_id": group_id,
            "initialize_with_readme": True,
            "visibility": "public"
        }

        try:
            r = requests.post(create_url, headers=headers, json=payload, timeout=15)
            r_json = r.json()
        except Exception:
            continue

        if r.status_code != 201:
            continue

        project_id = r_json["id"]
        web_url = r_json["web_url"]
        created_urls.append(web_url)

        with open(LOG_FILE, "a", encoding="utf-8") as logf:
            logf.write(f"{web_url}\n")

        update_url = f"https://gitlab.com/api/v4/projects/{project_id}/repository/files/README.md"
        update_payload = {
            "branch": "main",
            "content": content,
            "commit_message": "Update README.md from uploaded file"
        }

        try:
            requests.put(update_url, headers=headers, json=update_payload, timeout=15)
        except Exception:
            continue

    return jsonify(created_urls)

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    app.run(debug=True, host="0.0.0.0", port=5000)

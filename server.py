from flask import Flask, request, jsonify
from flask_cors import CORS
import time

# Create the app
app = Flask(__name__)
# This line is CRITICAL to let the webpage talk to the server
CORS(app) 

# This is our "database" in memory.
# It will store the latest status for each student.
student_statuses = {}

# This is the API endpoint for STUDENTS to send their status
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    student_id = data.get('student_id')
    status = data.get('status')
    
    if student_id and status:
        print(f"Received status from {student_id}: {status}")
        # Store the latest status
        student_statuses[student_id] = {
            "status": status,
            "timestamp": time.time() 
        }
        return jsonify({"message": "Status updated successfully"}), 200
    return jsonify({"error": "Invalid data"}), 400

# This is the API endpoint for the TEACHER'S DASHBOARD to get all statuses
@app.route('/get_statuses', methods=['GET'])
def get_statuses():
    return jsonify(student_statuses)

# Run the server
if __name__ == '__main__':
    # '0.0.0.0' means it's accessible on your network
    app.run(host='0.0.0.0', port=5000)
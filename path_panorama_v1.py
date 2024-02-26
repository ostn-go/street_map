from flask import Flask, request, send_file,make_response
from werkzeug.utils import secure_filename
import os
import io
from PIL import Image
import pymongo
import sys
import matplotlib.pyplot as plt

from pymongo import GEOSPHERE

app = Flask(__name__)

# Set the upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to check if a file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to handle image uploads (POST)
@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        client = pymongo.MongoClient('mongodb+srv://mithunputhusseri:mithun123@cluster0.nypksyl.mongodb.net/')
    
    # return a friendly error if a URI error is thrown 
    except pymongo.errors.ConfigurationError:
        print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
        sys.exit(1)

    # use a database named "myDatabase"
    db = client.test

    # use a collection named "places"
    my_collection = db["places"]

    # Check if the 'file' key is present in the request files
    if 'file' not in request.files:
        return 'No file part', 400

    # Extract 'file', 'buildingId', 'xCoordinate', 'yCoordinate', and 'floorId' from the request
    file = request.files['file']
    im = Image.open(file)
    image_bytes = io.BytesIO()
    im.save(image_bytes, format='PNG')
    building_id = request.form.get('building_id')
    x_coordinate = request.form.get('x_coordinate')
    y_coordinate = request.form.get('y_coordinate')
    floor_id = request.form.get('floor_id')
    cross_axis_count = request.form.get('cross_axis_count')

    # Validate 'buildingId' (you might want to add more validation logic)
    if not building_id:
        return 'BuildingId is required', 400
    if not x_coordinate:
            return 'x_coordinate is required', 400
    if not y_coordinate:
                return 'y_coordinate is required', 400
    if not floor_id:
                return 'floor_id is required', 400
    if not cross_axis_count:
                    return 'cross_axis_count is required', 400

    # Convert coordinates to float
    # x_coordinate corresponds to lat (-180 to 180)
    # y_coordinate corresponds to lon (-90 to 90)
    # confing any points to space of (-10 t 10 lat and, -10 to 10 lon)
    x_lat = (float(x_coordinate)/int(cross_axis_count))*20 -10
    y_lon = (float(y_coordinate)/int(cross_axis_count))*20 -10

    # Construct GeoJSON Point for the 'location' field
    location = {
        'type': 'Point',
        'coordinates': [x_lat, y_lon]
    }

    # Query to check if the document with the given buildingId, xCoordinate, and yCoordinate exists
    query = {
        'buildingId': int(building_id),
        'location': {
            '$nearSphere': {
                '$geometry': location,
                '$maxDistance':  0.01 # Adjust the max distance as needed
            }
        },
        'floorId': int(floor_id)
    }

    existing_document = my_collection.find_one(query)

    # If the document exists, update it; otherwise, insert a new document
    if existing_document:
        # Update the existing document
        my_collection.update_one(query, {'$set': {
            'data': image_bytes.getvalue(),
            'file_name': file.filename
        }})
        return 'File updated successfully', 200
    else:
        # Construct the image document with additional data
        image = {
            'data': image_bytes.getvalue(),
            'file_name': file.filename,
            'location': location,
            'floorId': int(floor_id),
            'buildingId': int(building_id)  # Convert to the desired data type
        }

        # Insert the image document into the MongoDB collection
        image_id = my_collection.insert_one(image).inserted_id
        return 'File uploaded successfully', 200

@app.route('/image/<building_id>/<floor_id>/<cross_axis_count>/<x_coordinate>/<y_coordinate>', methods=['GET'])
def get_image(building_id,floor_id,x_coordinate,y_coordinate,cross_axis_count):
    try:
        client = pymongo.MongoClient('mongodb+srv://mithunputhusseri:mithun123@cluster0.nypksyl.mongodb.net/?retryWrites=true&w=majority')
    
    # return a friendly error if a URI error is thrown 
    except pymongo.errors.ConfigurationError:
        print("An Invalid URI host error was received. Is your Atlas host name correct in your connection string?")
        sys.exit(1)

    db = client.test
    my_collection = db["places"]

    # Convert coordinates to float
    # x_coordinate corresponds to lat (-180 to 180)
    # y_coordinate corresponds to lon (-90 to 90)
    # confing any points to space of (-10 t 10 lat and, -10 to 10 lon)
    x_lat = (float(x_coordinate)/int(cross_axis_count))*20 -10
    y_lon = (float(y_coordinate)/int(cross_axis_count))*20 -10

    # Query to check if the document with the given buildingId, xCoordinate, and yCoordinate exists
    query = {
        'buildingId': int(building_id),
        'location': {
            '$near': {
                '$geometry': {
                    'type': 'Point',
                    'coordinates': [x_lat, y_lon]  # Specify the coordinates as [longitude, latitude]
                },
            }
        },
        'floorId': int(floor_id)
    }
    find_near = my_collection.find_one(query)
    print(find_near['location'])  
    file_bytes = io.BytesIO(find_near['data'])
    response = make_response(file_bytes)
    response.headers['Content-Type'] = 'jpeg'
    response.headers['Content-Disposition'] = f'attachment; filename={secure_filename("1.jpeg")}'
    
    return response
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(debug=True, port=8083)

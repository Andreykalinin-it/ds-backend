import logging
from flask import Flask, request, jsonify
from models.plate_reader import PlateReader, InvalidImage
from image_provider_client import ImageProviderClient
import io
import requests


app = Flask(__name__)
plate_reader = PlateReader.load_from_file('./model_weights/plate_reader_model.pth')
image_provider = ImageProviderClient(host='http://89.169.157.72:8080', timeout=5)


@app.route('/')
def hello():
    user = request.args.get('user', 'World')
    return f'<h1 style="color:red;"><center>Hello {user}!</center></h1>'


@app.route('/greeting', methods=['POST'])
def greeting():
    if 'user' not in request.json:
        return {'error': 'field "user" not found'}, 400

    user = request.json['user']
    return {
        'result': f'Hello {user}',
    }


@app.route('/readPlateNumber', methods=['POST'])
def read_plate_number():
    im = request.get_data()
    im = io.BytesIO(im)

    try:
        res = plate_reader.read_text(im)
    except InvalidImage:
        logging.error('invalid image')
        return {'error': 'invalid image'}, 400

    return {
        'plate_number': res,
    }


@app.route('/readPlateById', methods=['POST'])
def read_plate_by_id():
    if 'image_id' not in request.json:
        return {'error': 'field "image_id" not found'}, 400
    image_id = request.json['image_id']
    image_data, error, status_code = image_provider.get_image(image_id)
    if error:
        # Если есть ошибка, возвращаем её
        return error, status_code
    try:
        image_stream = io.BytesIO(image_data)
        plate_number = plate_reader.read_text(image_stream)
        return {
            'image_id': image_id,
            'plate_number': plate_number
        }
    except Exception as e:
        logging.error(f'Unexpected error processing image ID {image_id}: {e}')
        return {'error': 'internal server error'}, 500


@app.route('/readPlatesByIds', methods=['POST'])
def read_plates_by_ids():
    if 'image_ids' not in request.json:
        return {'error': 'field "image_ids" not found'}, 400
    image_ids = request.json['image_ids']
    if not isinstance(image_ids, list):
        return {'error': 'image_ids must be a list'}, 400
    if not image_ids:
        return {'error': 'image_ids list is empty'}, 400
    results = []
    errors = []
    for image_id in image_ids:
        image_data, error, _ = image_provider.get_image(image_id)
        if error:
            errors.append({
                'image_id': image_id,
                'error': error['error'],
                'status': 'error'
            })
            continue
        try:
            image_stream = io.BytesIO(image_data)
            plate_number = plate_reader.read_text(image_stream)
            results.append({
                'image_id': image_id,
                'plate_number': plate_number,
                'status': 'success'
            })
        except Exception as e:
            logging.error(f'Unexpected error processing image ID {image_id}: {e}')
            errors.append({
                'image_id': image_id,
                'error': 'internal server error',
                'status': 'error'
            })
    response = {
        'results': results,
        'errors': errors,
        'total': len(image_ids),
        'successful': len(results),
        'failed': len(errors)
    }
    if not results and errors:
        return jsonify(response), 207
    return jsonify(response)


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(levelname)s] [%(asctime)s] %(message)s',
        level=logging.INFO,
    )

    app.config['JSON_AS_ASCII'] = False
    app.run(host='0.0.0.0', port=8080, debug=True)
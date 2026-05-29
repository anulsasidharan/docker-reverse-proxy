from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    return jsonify({"message": "Hello from backend"})

@app.route('/api/health')
def health():
    return jsonify({"status": "ok", "service": "backend", "version": "1.0.0"})

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    body = request.get_json(silent=True) or {}
    return jsonify({
        "message": f"Item {item_id} updated",
        "id": item_id,
        "data": body
    })

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    return jsonify({
        "message": f"Item {item_id} deleted",
        "id": item_id
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


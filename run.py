from app import app
import logging

if __name__ == '__main__':
    logging.basicConfig(filename='site.log',level=logging.DEBUG)
    app.run(host="0.0.0.0", port=80, threaded=False, debug=False)
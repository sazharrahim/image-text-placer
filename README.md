**Run a flask application and celery worker in the same Docker container**

## How to run this example
1. Clone the repository.
2. Ensure you have docker and docker-compose installed. If unsure, install 'Docker Toolbox'.
3. Make sure your docker-machine is running (if you are on Win or Mac)
4. Run the command docker-compose up --build

## How to use this example
This is purely an illustrative example, but you can fork it and use it as a template. The example shows how to properly configure supervisord, celery, flask and docker. Take inspiration from it.

The strategy used is to run the flask application, the celery worker and celerybeat worker as programs using supervisord. Pipe all their stdout to the docker container's stdout, et voila. Using docker-compose, we connect to an external redis container, but as long as you change the backend URLs in the celery configuration to whatever persistent backend you have, then the example should work as a standalone docker container.

## How to install on Production
## This installation is for Ubuntu 20.*
1. iptables -A INPUT -p tcp --destination-port 8080 -j DROP
2. mkdir /var/www-folder/
3. cd /var/www-folder/
4. git clone https://github.com/U34rAli/image-text-placer
5. cd image-text-placer
6. sudo apt-get update
7. apt install python3-pip
8. pip3 install -r requirements.txt
9. apt-get install nginx
10. sudo apt install redis-server
11. cp default /etc/nginx/sites-enabled/
12. apt-get install supervisor
13. cp celery.conf /etc/supervisor/conf.d/
14. service nginx reload
15. sudo reboot
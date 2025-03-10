# docker run -d -p 5672:5672 --name some-rabbit rabbitmq:3


#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='hello')


channel.basic_publish(exchange='',
                      routing_key='hello',
                      body='Hello Clod!')

print(" [x] Sent 'Hello World!'")

connection.close()
# docker run -d -p 5672:5672 --name some-rabbit rabbitmq:3


#!/usr/bin/env python
import pika
import json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='arca')


# Example message with required fields
message = {
    "cuit": "23146234399",
    "pto_vta": "0001",
    "cbte_tipo": "001"  # 001 for Factura A
}

channel.basic_publish(
    exchange='',
    routing_key='arca',
    body=json.dumps(message),
    properties=pika.BasicProperties(
        reply_to='response',  # Queue to receive the response
        correlation_id='1'    # Unique ID to track the request
    )
)

print(" [x] Sent request for last invoice")

connection.close()

import os
import sys

# Add the 'ssl' directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'ssl'))

import pika
import json
from zeep.helpers import serialize_object
from solicitud_ultimo_comprobante import solicitar_ultimo_comprobante
from login_arca import login_ARCA

#RabbitMQ connection parameters.  Adjust as needed.
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.environ.get("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.environ.get("RABBITMQ_PASSWORD", "guest")


def process_message(ch, method, properties, body):
    try:
        if not body:
            raise ValueError("Empty message body received")
            
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in message body: {body}")
        cuit = data.get("cuit")
        pto_vta = data.get("pto_vta")
        cbte_tipo = data.get("cbte_tipo")

        if not cuit or not pto_vta or not cbte_tipo:
            raise ValueError("Missing required parameters in message: cuit, pto_vta, cbte_tipo")

        #Check for existing token and sign.  If not found, log in to ARCA.
        token_file = "ssl/ssl_files/token.txt"
        sign_file = "ssl/ssl_files/sign.txt"
        
        if not os.path.exists(token_file) or not os.path.exists(sign_file):
          print("Login to ARCA required...")
          token, sign = login_ARCA()
        else:
          with open(token_file, 'r') as f:
              token = f.read()
          with open(sign_file, 'r') as f:
              sign = f.read()

        response = solicitar_ultimo_comprobante(token, sign, cuit, pto_vta, cbte_tipo)
        # Convert Zeep response object to dictionary
        response_dict = serialize_object(response)

        #Send response back to the original sender using reply_to
        if properties and properties.reply_to:
            try:
                ch.basic_publish(
                    exchange='',
                    routing_key=str(properties.reply_to),  # Ensure routing key is string
                    properties=pika.BasicProperties(
                        correlation_id=properties.correlation_id if properties.correlation_id else None
                    ),
                    body=json.dumps({"response": response_dict})
                )
                print("Message processed and response sent.")
            except Exception as pub_error:
                print(f"Error sending response: {pub_error}")
        else:
            print("No reply_to property in request, response not sent")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        #Handle exceptions, send error message back if needed
        print(f"Error processing message: {e}")
        
        # Only try to send error response if reply_to is available
        if properties and properties.reply_to:
            try:
                ch.basic_publish(
                    exchange='',
                    routing_key=str(properties.reply_to),  # Ensure routing key is string
                    properties=pika.BasicProperties(
                        correlation_id=properties.correlation_id if properties.correlation_id else None
                    ),
                    body=json.dumps({"error": str(e)})
                )
            except Exception as pub_error:
                print(f"Error sending error response: {pub_error}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue='arca')
    channel.queue_declare(queue='response') # For responses, if needed.

    channel.basic_consume(queue='arca', on_message_callback=process_message)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()

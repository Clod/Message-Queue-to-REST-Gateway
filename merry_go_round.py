"""
RabbitMQ consumer service for ARCA (Argentinian Revenue Service) integration.
This service listens for requests on the 'arca' queue to fetch the last invoice number
for a given CUIT (tax ID), point of sale, and invoice type. It handles authentication
with ARCA and returns responses through a reply queue.

Dependencies:
    - pika: RabbitMQ client library
    - zeep: SOAP client for ARCA web services
    - Custom modules: solicitud_ultimo_comprobante, login_arca

Environment Variables:
    - RABBITMQ_HOST: RabbitMQ server host (default: localhost)
    - RABBITMQ_PORT: RabbitMQ server port (default: 5672)
    - RABBITMQ_USER: RabbitMQ username (default: guest)
    - RABBITMQ_PASSWORD: RabbitMQ password (default: guest)
"""

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
    """
    Process incoming RabbitMQ messages containing ARCA invoice query requests.
    
    Args:
        ch (pika.Channel): The channel object for RabbitMQ communication
        method (pika.spec.Basic.Deliver): Contains message delivery information
        properties (pika.spec.BasicProperties): Message properties including reply_to and correlation_id
        body (bytes): Message body containing JSON with request parameters
    
    The message body should contain:
        - cuit: Tax ID number
        - pto_vta: Point of sale number
        - cbte_tipo: Invoice type code
    
    Raises:
        ValueError: If message body is empty or missing required parameters
        json.JSONDecodeError: If message body contains invalid JSON
    """
    try:
        if not body:
            raise ValueError("Empty message body received")
            
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in message body: {body}")
        # Extract required parameters from the JSON message
        cuit = data.get("cuit")  # Tax ID number
        pto_vta = data.get("pto_vta")  # Point of sale identifier
        cbte_tipo = data.get("cbte_tipo")  # Invoice type code

        if not cuit or not pto_vta or not cbte_tipo:
            raise ValueError("Missing required parameters in message: cuit, pto_vta, cbte_tipo")

        # #Check for existing token and sign.  If not found, log in to ARCA.
        # token_file = "ssl/ssl_files/token.txt"
        # sign_file = "ssl/ssl_files/sign.txt"
        
        # if not os.path.exists(token_file) or not os.path.exists(sign_file):
        #   print("Login to ARCA required...")
        #   token, sign = login_ARCA()
        # else:
        #   with open(token_file, 'r') as f:
        #       token = f.read()
        #   with open(sign_file, 'r') as f:
        #       sign = f.read()

        # Authenticate with ARCA service and get security tokens
        token, sign = login_ARCA()

        # Query ARCA web service for the last invoice number
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
    """
    Main function to establish RabbitMQ connection and start consuming messages.
    
    Sets up a connection to RabbitMQ using environment variables for configuration,
    declares necessary queues ('arca' for requests and 'response' for replies),
    and starts consuming messages from the 'arca' queue.
    
    The service runs indefinitely until interrupted with CTRL+C.
    """
    # Set up RabbitMQ connection with credentials from environment variables
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials))
    
    # Create channel and ensure queues exist
    channel = connection.channel()
    channel.queue_declare(queue='arca')
    channel.queue_declare(queue='response') # For responses, if needed.

    channel.basic_consume(queue='arca', on_message_callback=process_message)

    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    main()

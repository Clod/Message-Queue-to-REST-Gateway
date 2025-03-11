#!/usr/bin/env python
"""
RabbitMQ client that requests the last invoice number from a remote service.
This script establishes a connection with RabbitMQ, sends a request with invoice parameters,
and waits for a response using a temporary callback queue. It implements a request-reply
pattern with correlation IDs to ensure responses match their requests.

The script handles connection retries, timeouts, and proper cleanup of resources.
"""
import pika
import json
import uuid
import time
import sys

def request_last_invoice(cuit, pto_vta, cbte_tipo, timeout=30):  # timeout in seconds
    """
    Request the last invoice number for given parameters using RabbitMQ.

    Args:
        cuit (str): The tax ID number of the company
        pto_vta (str): The point of sale number
        cbte_tipo (str): The type of invoice document
        timeout (int, optional): Maximum time to wait for response in seconds. Defaults to 30.

    Returns:
        dict: The response from the server containing the last invoice information

    Raises:
        TimeoutError: If no response is received within the timeout period
        pika.exceptions.AMQPConnectionError: If connection to RabbitMQ fails
        Exception: For other unexpected errors
    """
    connection = None
    try:
        # Establish connection with retry mechanism for better reliability
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost',
            connection_attempts=3,
            retry_delay=1
        ))
        channel = connection.channel()

        # Declare a temporary exclusive queue for responses - will be auto-deleted when connection closes
        result = channel.queue_declare(queue='', exclusive=True)
        callback_queue = result.method.queue

        # Generate a unique correlation ID for this request to match response with request
        correlation_id = str(uuid.uuid4())
        
        # Store the response when it arrives - used by callback function
        response_received = None
        
        def on_response(ch, method, props, body):
            if props.correlation_id == correlation_id:
                nonlocal response_received
                try:
                    response_received = json.loads(body)
                except json.JSONDecodeError:
                    response_received = {"error": "Failed to parse response as JSON", "raw": body.decode()}

        # Set up consumer for the response queue with auto acknowledgment
        channel.basic_consume(
            queue=callback_queue,
            on_message_callback=on_response,
            auto_ack=True
        )

        # Prepare the request message with required invoice parameters
        message = {
            "cuit": cuit,
            "pto_vta": pto_vta,
            "cbte_tipo": cbte_tipo
        }

        # Send the request to the 'arca' queue with correlation ID and reply-to queue
        channel.basic_publish(
            exchange='',
            routing_key='arca',
            properties=pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=correlation_id,
            ),
            body=json.dumps(message)
        )

        print(" [x] Sent request for last invoice, waiting for response...")

        # Wait for the response with timeout - check every second for new messages
        start_time = time.time()
        while response_received is None:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"No response received after {timeout} seconds")
            connection.process_data_events()
            connection.sleep(1.0)  # Sleep for 1 second between checks

        return response_received

    except pika.exceptions.AMQPConnectionError as e:
        print(f"Failed to connect to RabbitMQ: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        # Ensure connection is closed even if an error occurs
        if connection and not connection.is_closed:
            connection.close()

def main():
    """
    Main function that demonstrates the usage of request_last_invoice.
    Sets up example parameters and handles potential errors in the request process.
    """
    # Example values
    cuit = "23146234399"
    pto_vta = "0001"
    cbte_tipo = "001"  # 001 for Factura A

    try:
        response = request_last_invoice(cuit, pto_vta, cbte_tipo)
        print("\nResponse received:")
        print(json.dumps(response, indent=2))
    except TimeoutError as e:
        print(f"\nTimeout error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
